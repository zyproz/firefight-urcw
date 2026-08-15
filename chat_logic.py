"""
Logique du chat WarEast.io — v5.0
====================================
Chat global + chat de clan, avec commandes admin masquees (prefixe '/').
Une commande n'est jamais enregistree dans le chat visible par les autres.
"""

import requests
from account_logic import SUPABASE_URL, HEADERS, verify_token, is_admin_account, admin_add_braves


def send_message(pseudo, token, channel, message):
    if not verify_token(pseudo, token):
        return {"ok": False, "error": "Session invalide, reconnecte-toi"}
    message = (message or "").strip()
    if not message:
        return {"ok": False, "error": "Message vide"}
    if len(message) > 300:
        return {"ok": False, "error": "Message trop long"}

    if message.startswith("/"):
        return _handle_command(pseudo, token, message)

    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/chat_messages",
        headers={**HEADERS, "Prefer": "return=representation"},
        json={"channel": channel, "pseudo": pseudo, "message": message},
        timeout=8,
    )
    if r.status_code not in (200, 201):
        return {"ok": False, "error": "Erreur serveur, reessaie"}
    return {"ok": True, "isCommand": False}


def _handle_command(pseudo, token, message):
    if not is_admin_account(pseudo, token):
        return {"ok": False, "error": "Commande reservee a l'administrateur", "isCommand": True}

    parts = message[1:].split()
    if not parts:
        return {"ok": False, "error": "Commande vide", "isCommand": True}
    cmd = parts[0].lower()

    if cmd in ("addbrave", "addbraves"):
        if len(parts) == 2:
            target, amount = pseudo, parts[1]
        elif len(parts) == 3:
            target, amount = parts[1], parts[2]
        else:
            return {"ok": False, "error": "Usage: /addbrave [pseudo] montant", "isCommand": True}
        try:
            amount = int(amount)
        except ValueError:
            return {"ok": False, "error": "Montant invalide", "isCommand": True}
        result = admin_add_braves(pseudo, token, target, amount)
        result["isCommand"] = True
        return result

    return {"ok": False, "error": f"Commande inconnue: /{cmd}", "isCommand": True}


def get_messages(channel, since_id=0):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/chat_messages",
        headers=HEADERS,
        params={
            "channel": f"eq.{channel}",
            "id": f"gt.{since_id}",
            "select": "id,pseudo,message,created_at",
            "order": "id.asc",
            "limit": "100",
        },
        timeout=8,
    )
    r.raise_for_status()
    return {"ok": True, "messages": r.json()}
