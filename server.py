from flask import Flask, send_from_directory, jsonify, request
import os
from account_logic import register_player, login_player

app = Flask(__name__, static_folder='.')

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

# ---------- Fichiers statiques (inchangé, toujours en dernier) ----------

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
