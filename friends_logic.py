"""
Logique du systeme d'amis WarEast.io — v4.1 (pseudo seul, plus de tag)
"""

import requests
from account_logic import SUPABASE_URL, HEADERS, verify_token, get_online_status


def search_players(query: str, exclude_pseudo: str = "", limit: int = 10):
    query = query.strip()
    if len(query) < 2:
        return {"ok": False, "error": "Tape au moins 2 caracteres"}
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/players",
        headers=HEADERS,
        params={"pseudo": f"ilike.*{query}*", "select": "pseudo", "limit": str(limit)},
        timeout=8,
    )
    r.raise_for_status()
    results = [row for row in r.json() if row["pseudo"].lower() != exclude_pseudo.lower()]
    return {"ok": True, "results": results}


def send_friend_request(my_pseudo, my_token, target_pseudo):
    if not verify_token(my_pseudo, my_token):
        return {"ok": False, "error": "Session invalide, reconnecte-toi"}
    if my_pseudo.lower() == target_pseudo.lower():
        return {"ok": False, "error": "Impossible de s'ajouter soi-meme"}

    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/friendships",
        headers=HEADERS,
        params={
            "or": f"(and(requester_pseudo.eq.{my_pseudo},addressee_pseudo.eq.{target_pseudo}),"
                  f"and(requester_pseudo.eq.{target_pseudo},addressee_pseudo.eq.{my_pseudo}))",
            "select": "id,status",
        },
        timeout=8,
    )
    r.raise_for_status()
    if r.json():
        return {"ok": False, "error": "Demande deja envoyee ou deja amis"}

    r2 = requests.post(
        f"{SUPABASE_URL}/rest/v1/friendships",
        headers={**HEADERS, "Prefer": "return=representation"},
        json={
            "requester_pseudo": my_pseudo, "requester_tag": "0000",
            "addressee_pseudo": target_pseudo, "addressee_tag": "0000",
            "status": "pending",
        },
        timeout=8,
    )
    if r2.status_code not in (200, 201):
        return {"ok": False, "error": "Erreur serveur, reessaie"}
    return {"ok": True}


def respond_friend_request(my_pseudo, my_token, request_id, accept: bool):
    if not verify_token(my_pseudo, my_token):
        return {"ok": False, "error": "Session invalide, reconnecte-toi"}

    if accept:
        r = requests.patch(
            f"{SUPABASE_URL}/rest/v1/friendships",
            headers=HEADERS,
            params={"id": f"eq.{request_id}", "addressee_pseudo": f"eq.{my_pseudo}"},
            json={"status": "accepted"},
            timeout=8,
        )
    else:
        r = requests.delete(
            f"{SUPABASE_URL}/rest/v1/friendships",
            headers=HEADERS,
            params={"id": f"eq.{request_id}", "addressee_pseudo": f"eq.{my_pseudo}"},
            timeout=8,
        )
    if r.status_code not in (200, 204):
        return {"ok": False, "error": "Erreur serveur, reessaie"}
    return {"ok": True}


def list_friends(my_pseudo, my_token):
    if not verify_token(my_pseudo, my_token):
        return {"ok": False, "error": "Session invalide, reconnecte-toi"}

    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/friendships",
        headers=HEADERS,
        params={
            "or": f"(requester_pseudo.eq.{my_pseudo},addressee_pseudo.eq.{my_pseudo})",
            "select": "*",
        },
        timeout=8,
    )
    r.raise_for_status()
    rows = r.json()

    friends, incoming, outgoing = [], [], []
    for row in rows:
        is_requester = row["requester_pseudo"] == my_pseudo
        other_pseudo = row["addressee_pseudo"] if is_requester else row["requester_pseudo"]
        other = {"pseudo": other_pseudo}
        if row["status"] == "accepted":
            friends.append(other)
        elif is_requester:
            outgoing.append(other)
        else:
            other["request_id"] = row["id"]
            incoming.append(other)

    online = get_online_status([f["pseudo"] for f in friends])
    for f in friends:
        f["online"] = online.get(f["pseudo"], False)

    return {"ok": True, "friends": friends, "incoming": incoming, "outgoing": outgoing}
