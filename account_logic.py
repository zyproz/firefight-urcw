"""
Logique du systeme de comptes WarEast.io — v4.1
==================================================
Systeme simplifie : pseudo + mot de passe uniquement (plus de tag).
Le pseudo est desormais l'identifiant unique complet.
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


def register_player(pseudo: str, password: str):
    pseudo = pseudo.strip()
    if not (2 <= len(pseudo) <= 16):
        return {"ok": False, "error": "Pseudo invalide (2 a 16 caracteres)"}
    if len(password) < 6:
        return {"ok": False, "error": "Mot de passe trop court (6 caracteres min)"}

    r0 = requests.get(
        f"{SUPABASE_URL}/rest/v1/players",
        headers=HEADERS,
        params={"pseudo": f"ilike.{pseudo}", "select": "id"},
        timeout=8,
    )
    r0.raise_for_status()
    if r0.json():
        return {"ok": False, "error": "Ce pseudo est deja pris, choisis-en un autre"}

    pw_hash = hash_password(password)
    token = secrets.token_urlsafe(24)

    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/players",
        headers={**HEADERS, "Prefer": "return=representation"},
        json={"pseudo": pseudo, "tag": "0000", "password_hash": pw_hash, "session_token": token},
        timeout=8,
    )
    if r.status_code not in (200, 201):
        return {"ok": False, "error": "Ce pseudo est deja pris, choisis-en un autre"}

    return {"ok": True, "pseudo": pseudo, "token": token}

def login_player(pseudo: str, password: str):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/players",
        headers=HEADERS,
        params={"pseudo": f"ilike.{pseudo}", "select": "pseudo,password_hash"},
        timeout=8,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows or not verify_password(password, rows[0]["password_hash"]):
        return {"ok": False, "error": "Pseudo ou mot de passe incorrect"}

    real_pseudo = rows[0]["pseudo"]
    token = secrets.token_urlsafe(24)
    requests.patch(
        f"{SUPABASE_URL}/rest/v1/players",
        headers=HEADERS,
        params={"pseudo": f"eq.{real_pseudo}"},
        json={"session_token": token},
        timeout=8,
    )
    return {"ok": True, "pseudo": real_pseudo, "token": token}

def verify_token(pseudo: str, token: str) -> bool:
    if not (pseudo and token):
        return False
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/players",
        headers=HEADERS,
        params={"pseudo": f"eq.{pseudo}", "select": "session_token"},
        timeout=8,
    )
    r.raise_for_status()
    rows = r.json()
    return bool(rows) and hmac.compare_digest(rows[0].get("session_token") or "", token)

def heartbeat(pseudo: str, token: str):
    if not verify_token(pseudo, token):
        return {"ok": False, "error": "Session invalide, reconnecte-toi"}
    requests.patch(
        f"{SUPABASE_URL}/rest/v1/players",
        headers=HEADERS,
        params={"pseudo": f"eq.{pseudo}"},
        json={"last_active": "now()"},
        timeout=8,
    )
    return {"ok": True}

def get_online_status(pseudos):
    if not pseudos:
        return {}
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/players",
        headers=HEADERS,
        params={"pseudo": f"in.({','.join(pseudos)})", "select": "pseudo,last_active"},
        timeout=8,
    )
    r.raise_for_status()
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    result = {}
    for row in r.json():
        try:
            la = datetime.datetime.fromisoformat(row["last_active"].replace("Z", "+00:00"))
            result[row["pseudo"]] = (now - la).total_seconds() < 25
        except Exception:
            result[row["pseudo"]] = False
    return result
