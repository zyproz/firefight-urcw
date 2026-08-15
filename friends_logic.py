"""
Logique du systeme d'amis WarEast.io — v3.7
=============================================
S'appuie sur account_logic.verify_token pour s'assurer que chaque action
est bien faite par le compte connecte, pas par n'importe qui qui devine
un pseudo#tag.
"""

import requests
from account_logic import SUPABASE_URL, HEADERS, verify_token


def search_players(query: str, exclude_pseudo: str = "", limit: int = 10):
    query = query.strip()
    if len(query) < 2:
        return {"ok": False, "error": "Tape au moins 2 caracteres"}
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/players",
        headers=HEADERS,
        params={"pseudo": f"ilike.*{query}*", "select": "pseudo,tag", "limit": str(limit)},
        timeout=8,
    )
    r.raise_for_status()
    results = [row for row in r.json() if row["pseudo"] != exclude_pseudo]
    return {"ok": True, "results": results}


def send_friend_request(my_pseudo, my_tag, my_token, target_pseudo, target_tag):
    if not verify_token(my_pseudo, my_tag, my_token):
        return {"ok": False, "error": "Session invalide, reconnecte-toi"}
    if my_pseudo == target_pseudo and my_tag == target_tag:
        return {"ok": False, "error": "Impossible de s'ajouter soi-meme"}

    # Verifier qu'il n'existe pas deja une relation (dans un sens ou l'autre)
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/friendships",
        headers=HEADERS,
        params={
            "or": f"(and(requester_pseudo.eq.{my_pseudo},requester_tag.eq.{my_tag},addressee_pseudo.eq.{target_pseudo},addressee_tag.eq.{target_tag}),"
                  f"and(requester_pseudo.eq.{target_pseudo},requester_tag.eq.{target_tag},addressee_pseudo.eq.{my_pseudo},addressee_tag.eq.{my_tag}))",
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
            "requester_pseudo": my_pseudo, "requester_tag": my_tag,
            "addressee_pseudo": target_pseudo, "addressee_tag": target_tag,
            "status": "pending",
        },
        timeout=8,
    )
    if r2.status_code not in (200, 201):
        return {"ok": False, "error": "Erreur serveur, reessaie"}
    return {"ok": True}


def respond_friend_request(my_pseudo, my_tag, my_token, request_id, accept: bool):
    if not verify_token(my_pseudo, my_tag, my_token):
        return {"ok": False, "error": "Session invalide, reconnecte-toi"}

    if accept:
        r = requests.patch(
            f"{SUPABASE_URL}/rest/v1/friendships",
            headers=HEADERS,
            params={"id": f"eq.{request_id}", "addressee_pseudo": f"eq.{my_pseudo}", "addressee_tag": f"eq.{my_tag}"},
            json={"status": "accepted"},
            timeout=8,
        )
    else:
        r = requests.delete(
            f"{SUPABASE_URL}/rest/v1/friendships",
            headers=HEADERS,
            params={"id": f"eq.{request_id}", "addressee_pseudo": f"eq.{my_pseudo}", "addressee_tag": f"eq.{my_tag}"},
            timeout=8,
        )
    if r.status_code not in (200, 204):
        return {"ok": False, "error": "Erreur serveur, reessaie"}
    return {"ok": True}


def list_friends(my_pseudo, my_tag, my_token):
    if not verify_token(my_pseudo, my_tag, my_token):
        return {"ok": False, "error": "Session invalide, reconnecte-toi"}

    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/friendships",
        headers=HEADERS,
        params={
            "or": f"(and(requester_pseudo.eq.{my_pseudo},requester_tag.eq.{my_tag}),"
                  f"and(addressee_pseudo.eq.{my_pseudo},addressee_tag.eq.{my_tag}))",
            "select": "*",
        },
        timeout=8,
    )
    r.raise_for_status()
    rows = r.json()

    friends, incoming, outgoing = [], [], []
    for row in rows:
        is_requester = row["requester_pseudo"] == my_pseudo and row["requester_tag"] == my_tag
        other = (
            {"pseudo": row["addressee_pseudo"], "tag": row["addressee_tag"]}
            if is_requester else
            {"pseudo": row["requester_pseudo"], "tag": row["requester_tag"]}
        )
        if row["status"] == "accepted":
            friends.append(other)
        elif is_requester:
            outgoing.append(other)
        else:
            other["request_id"] = row["id"]
            incoming.append(other)

    return {"ok": True, "friends": friends, "incoming": incoming, "outgoing": outgoing}
