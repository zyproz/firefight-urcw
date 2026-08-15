from flask import Flask, send_from_directory, jsonify, request
import os
from account_logic import register_player, login_player
from friends_logic import search_players, send_friend_request, respond_friend_request, list_friends
from clan_logic import create_clan, search_clans, join_clan, leave_clan, invite_to_clan, respond_clan_invite, get_my_clan

app = Flask(__name__, static_folder='.')

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/ping')
def ping():
    return jsonify({'status': 'ok'})

# ---------- Comptes joueurs (v3.5) ----------

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json(force=True, silent=True) or {}
    result = register_player(data.get('pseudo', ''), data.get('password', ''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    result = login_player(data.get('pseudo', ''), data.get('tag', ''), data.get('password', ''))
    return jsonify(result), (200 if result.get('ok') else 401)

# ---------- Amis (v3.7) ----------

@app.route('/api/friends/search', methods=['GET'])
def api_friends_search():
    result = search_players(request.args.get('q', ''), request.args.get('exclude', ''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/friends/request', methods=['POST'])
def api_friends_request():
    d = request.get_json(force=True, silent=True) or {}
    result = send_friend_request(
        d.get('my_pseudo', ''), d.get('my_tag', ''), d.get('my_token', ''),
        d.get('target_pseudo', ''), d.get('target_tag', ''),
    )
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/friends/respond', methods=['POST'])
def api_friends_respond():
    d = request.get_json(force=True, silent=True) or {}
    result = respond_friend_request(
        d.get('my_pseudo', ''), d.get('my_tag', ''), d.get('my_token', ''),
        d.get('request_id', ''), bool(d.get('accept', False)),
    )
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/friends/list', methods=['GET'])
def api_friends_list():
    result = list_friends(
        request.args.get('pseudo', ''), request.args.get('tag', ''), request.args.get('token', ''),
    )
    return jsonify(result), (200 if result.get('ok') else 400)

# ---------- Clans (v4.0) ----------

@app.route('/api/clan/create', methods=['POST'])
def api_clan_create():
    d = request.get_json(force=True, silent=True) or {}
    result = create_clan(d.get('my_pseudo',''), d.get('my_tag',''), d.get('my_token',''), d.get('name',''), d.get('tag',''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/clan/search', methods=['GET'])
def api_clan_search():
    result = search_clans(request.args.get('q', ''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/clan/join', methods=['POST'])
def api_clan_join():
    d = request.get_json(force=True, silent=True) or {}
    result = join_clan(d.get('my_pseudo',''), d.get('my_tag',''), d.get('my_token',''), d.get('clan_id'))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/clan/leave', methods=['POST'])
def api_clan_leave():
    d = request.get_json(force=True, silent=True) or {}
    result = leave_clan(d.get('my_pseudo',''), d.get('my_tag',''), d.get('my_token',''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/clan/invite', methods=['POST'])
def api_clan_invite():
    d = request.get_json(force=True, silent=True) or {}
    result = invite_to_clan(d.get('my_pseudo',''), d.get('my_tag',''), d.get('my_token',''), d.get('target_pseudo',''), d.get('target_tag',''))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/clan/respond', methods=['POST'])
def api_clan_respond():
    d = request.get_json(force=True, silent=True) or {}
    result = respond_clan_invite(d.get('my_pseudo',''), d.get('my_tag',''), d.get('my_token',''), d.get('invite_id'), bool(d.get('accept', False)))
    return jsonify(result), (200 if result.get('ok') else 400)

@app.route('/api/clan/mine', methods=['GET'])
def api_clan_mine():
    result = get_my_clan(request.args.get('pseudo',''), request.args.get('tag',''), request.args.get('token',''))
    return jsonify(result), (200 if result.get('ok') else 400)

# ---------- Fichiers statiques (inchangé, toujours en dernier) ----------

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
