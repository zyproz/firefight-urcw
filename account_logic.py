"""
Logique du système de comptes WarEast.io — Phase 1 (v3.5)
============================================================
Ce fichier n'est PAS encore branché sur le serveur — c'est la logique
prête à être fusionnée dans server.py une fois que Ciro l'envoie.

Utilise uniquement des librairies déjà incluses dans Python (hashlib, secrets,
urllib) + `requests` pour parler à Supabase en HTTP direct — pas besoin
d'installer de nouvelle dépendance exotique, donc pas de risque de casser
le déploiement Render pour un package manquant.

La clé secrète Supabase doit être fournie via une variable d'environnement
Render (jamais écrite en dur ici), nommée SUPABASE_SECRET_KEY.
"""

import os
import hmac
import hashlib
import secrets
import requests

SUPABASE_URL = "https://lilivxqezzgaoisbbour.supabase.co"
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")

HEADERS = {
    "apikey": SUPABASE_SECRET_KEY,
    "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
    "Content-Type": "application/json",
}


# ---------- Mots de passe : hachage sécurisé (PBKDF2, aucune dépendance externe) ----------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 100_000)
    return f"{salt}${digest.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, digest_hex = stored_hash.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 100_000)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


# ---------- Requetes Supabase (REST direct, via la table 'players') ----------

def _get_existing_tags(pseudo: str):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/players",
        headers=HEADERS,
        params={"pseudo": f"eq.{pseudo}", "select": "tag"},
        timeout=8,
    )
    r.raise_for_status()
    return [row["tag"] for row in r.json()]

def _generate_unique_tag(pseudo: str) -> str:
    existing = set(_get_existing_tags(pseudo))
    for _ in range(50):
        tag = f"{secrets.randbelow(9000) + 1000}"
        if tag not in existing:
            return tag
    raise RuntimeError("Impossible de generer un tag unique, pseudo trop demande")

def register_player(pseudo: str, password: str):
    pseudo = pseudo.strip()
    if not (2 <= len(pseudo) <= 16):
        return {"ok": False, "error": "Pseudo invalide (2 a 16 caracteres)"}
    if len(password) < 6:
        return {"ok": False, "error": "Mot de passe trop court (6 caracteres min)"}

    tag = _generate_unique_tag(pseudo)
    pw_hash = hash_password(password)
    token = secrets.token_urlsafe(24)

    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/players",
        headers={**HEADERS, "Prefer": "return=representation"},
        json={"pseudo": pseudo, "tag": tag, "password_hash": pw_hash, "session_token": token},
        timeout=8,
    )
    if r.status_code not in (200, 201):
        return {"ok": False, "error": "Erreur serveur, reessaie"}

    return {"ok": True, "pseudo": pseudo, "tag": tag, "token": token}

def login_player(pseudo: str, tag: str, password: str):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/players",
        headers=HEADERS,
        params={"pseudo": f"eq.{pseudo}", "tag": f"eq.{tag}", "select": "password_hash"},
        timeout=8,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows or not verify_password(password, rows[0]["password_hash"]):
        return {"ok": False, "error": "Pseudo, tag ou mot de passe incorrect"}

    token = secrets.token_urlsafe(24)
    requests.patch(
        f"{SUPABASE_URL}/rest/v1/players",
        headers=HEADERS,
        params={"pseudo": f"eq.{pseudo}", "tag": f"eq.{tag}"},
        json={"session_token": token},
        timeout=8,
    )
    return {"ok": True, "pseudo": pseudo, "tag": tag, "token": token}

def verify_token(pseudo: str, tag: str, token: str) -> bool:
    if not (pseudo and tag and token):
        return False
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/players",
        headers=HEADERS,
        params={"pseudo": f"eq.{pseudo}", "tag": f"eq.{tag}", "select": "session_token"},
        timeout=8,
    )
    r.raise_for_status()
    rows = r.json()
    return bool(rows) and hmac.compare_digest(rows[0].get("session_token") or "", token)


# ---------- Exemple des routes Flask a ajouter (adapte selon la structure reelle de server.py) ----------
#
# from account_logic import register_player, login_player
#
# @app.route('/api/register', methods=['POST'])
# def api_register():
#     data = request.get_json(force=True)
#     result = register_player(data.get('pseudo', ''), data.get('password', ''))
#     return jsonify(result), (200 if result['ok'] else 400)
#
# @app.route('/api/login', methods=['POST'])
# def api_login():
#     data = request.get_json(force=True)
#     result = login_player(data.get('pseudo', ''), data.get('tag', ''), data.get('password', ''))
#     return jsonify(result), (200 if result['ok'] else 401)
