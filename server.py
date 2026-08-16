import eventlet
eventlet.monkey_patch()

from flask import Flask, send_from_directory, jsonify, request
import os
from account_logic import register_player, login_player, heartbeat, sync_braves
from friends_logic import search_players, send_friend_request, respond_friend_request, list_friends
from clan_logic import create_clan, search_clans, join_clan, leave_clan, invite_to_clan, respond_clan_invite, get_my_clan
from chat_logic import send_message, get_messages
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__, static_folder='.')
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

MAP_FILE = os.environ.get('MAP_FILE', 'index.html')

# ---------- Multijoueur temps réel (remplace Ably) ----------
# Relais générique : chaque event envoyé par un client est renvoyé tel quel
# à tous les autres clients connectés à CE serveur (= cette map, puisque
# chaque map a déjà son propre serveur Render). Aucune logique de jeu ici,
# exactement comme Ably ne faisait que relayer sans comprendre le contenu.

connected_players = set()

RELAY_EVENTS = ['pos', 'sfx', 'veh_spawn', 'shot', 'gren', 'expl', 'hit', 'heal',
                 'cap', 'died', 'corpse', 'corpse2', 'tix', 'reset', 'state',
                 'spawn', 'bye', 'blood', 'drone_hit', 'drone']

def _make_relay(event_name):
    def _handler(data):
        emit(event_name, data, broadcast=True, include_self=True)
    return _handler

for _ev in RELAY_EVENTS:
    socketio.on_event(_ev, _make_relay(_ev))

# Chat vocal (WebRTC signaling) : un salon par équipe, comme les channels
# Ably 'ff_vc_TEAM_...' avant. Le client doit d'abord émettre
# 'voice_join_team' avec {team:'UA'|'RU'} avant d'utiliser les events voix.
VOICE_EVENTS = ['join', 'offer', 'answer', 'ice', 'spk']
voice_team_by_sid = {}  # sid -> 'UA'/'RU', pour router sans dépendre du payload

@socketio.on('voice_join_team')
def _voice_join_team(data):
    team = (data or {}).get('team', '')
    if team:
        join_room('voice_' + team)
        voice_team_by_sid[request.sid] = team

def _make_voice_relay(event_name):
    def _handler(data):
        team = voice_team_by_sid.get(request.sid)
        if team:
            emit(event_name, data, room='voice_' + team, include_self=True)
    return _handler

for _ev in VOICE_EVENTS:
    socketio.on_event(_ev, _make_voice_relay(_ev))

@socketio.on('connect')
def _on_connect():
    connected_players.add(request.sid)

@socketio.on('disconnect')
def _on_disconnect():
    connected_players.discard(request.sid)
    voice_team_by_sid.pop(request.sid, None)

@app.route('/api/playercount')
def api_playercount():
    return jsonify({'count': len(connected_players)})

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/')
def index():
    return send_from_directory('.', MAP_FILE)

@app.route('/ping')
def ping():
    return jsonify({'status': 'ok'})

# ---------- Comptes joueurs (v4.1 : pseudo + mot de passe uniquement) ----------

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json(force=True, silent=True) or {}
    result = register_player(data.get('pseudo', ''), data.get('password', ''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    result = login_player(data.get('pseudo', ''), data.get('password', ''))
    return jsonify(result), (200 if result.get('ok') else 401)

@app.route('/api/heartbeat', methods=['POST'])
def api_heartbeat():
    data = request.get_json(force=True, silent=True) or {}
    result = heartbeat(data.get('pseudo', ''), data.get('token', ''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/braves/sync', methods=['POST'])
def api_braves_sync():
    data = request.get_json(force=True, silent=True) or {}
    result = sync_braves(data.get('pseudo', ''), data.get('token', ''), data.get('amount', 0))
    return jsonify(result), (200 if result.get('ok') else 400)

# ---------- Chat (v5.0) ----------

@app.route('/api/chat/send', methods=['POST'])
def api_chat_send():
    d = request.get_json(force=True, silent=True) or {}
    result = send_message(d.get('pseudo', ''), d.get('token', ''), d.get('channel', 'global'), d.get('message', ''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/chat/messages', methods=['GET'])
def api_chat_messages():
    result = get_messages(request.args.get('channel', 'global'), request.args.get('since', 0))
    return jsonify(result), (200 if result.get('ok') else 400)

# ---------- Amis ----------

@app.route('/api/friends/search', methods=['GET'])
def api_friends_search():
    result = search_players(request.args.get('q', ''), request.args.get('exclude', ''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/friends/request', methods=['POST'])
def api_friends_request():
    d = request.get_json(force=True, silent=True) or {}
    result = send_friend_request(d.get('my_pseudo', ''), d.get('my_token', ''), d.get('target_pseudo', ''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/friends/respond', methods=['POST'])
def api_friends_respond():
    d = request.get_json(force=True, silent=True) or {}
    result = respond_friend_request(d.get('my_pseudo', ''), d.get('my_token', ''), d.get('request_id', ''), bool(d.get('accept', False)))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/friends/list', methods=['GET'])
def api_friends_list():
    result = list_friends(request.args.get('pseudo', ''), request.args.get('token', ''))
    return jsonify(result), (200 if result.get('ok') else 400)

# ---------- Clans ----------

@app.route('/api/clan/create', methods=['POST'])
def api_clan_create():
    d = request.get_json(force=True, silent=True) or {}
    result = create_clan(d.get('my_pseudo',''), d.get('my_token',''), d.get('name',''), d.get('tag',''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/clan/search', methods=['GET'])
def api_clan_search():
    result = search_clans(request.args.get('q', ''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/clan/join', methods=['POST'])
def api_clan_join():
    d = request.get_json(force=True, silent=True) or {}
    result = join_clan(d.get('my_pseudo',''), d.get('my_token',''), d.get('clan_id'))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/clan/leave', methods=['POST'])
def api_clan_leave():
    d = request.get_json(force=True, silent=True) or {}
    result = leave_clan(d.get('my_pseudo',''), d.get('my_token',''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/clan/invite', methods=['POST'])
def api_clan_invite():
    d = request.get_json(force=True, silent=True) or {}
    result = invite_to_clan(d.get('my_pseudo',''), d.get('my_token',''), d.get('target_pseudo',''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/clan/respond', methods=['POST'])
def api_clan_respond():
    d = request.get_json(force=True, silent=True) or {}
    result = respond_clan_invite(d.get('my_pseudo',''), d.get('my_token',''), d.get('invite_id'), bool(d.get('accept', False)))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/clan/mine', methods=['GET'])
def api_clan_mine():
    result = get_my_clan(request.args.get('pseudo',''), request.args.get('token',''))
    return jsonify(result), (200 if result.get('ok') else 400)

# ---------- Fichiers statiques (inchangé, toujours en dernier) ----------

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
