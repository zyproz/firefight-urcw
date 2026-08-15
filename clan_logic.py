"""
Logique du systeme de clan WarEast.io — v4.0
================================================
"""

import requests
from account_logic import SUPABASE_URL, HEADERS, verify_token


def _get_my_clan_id(pseudo, tag):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/clan_members",
        headers=HEADERS,
        params={"pseudo": f"eq.{pseudo}", "tag": f"eq.{tag}", "select": "clan_id"},
        timeout=8,
    )
    r.raise_for_status()
    rows = r.json()
    return rows[0]["clan_id"] if rows else None


def create_clan(my_pseudo, my_tag, my_token, name, tag):
    if not verify_token(my_pseudo, my_tag, my_token):
        return {"ok": False, "error": "Session invalide, reconnecte-toi"}
    name = name.strip()
    tag = tag.strip().upper()
    if not (2 <= len(name) <= 24):
        return {"ok": False, "error": "Nom de clan invalide (2 a 24 caracteres)"}
    if not (2 <= len(tag) <= 4):
        return {"ok": False, "error": "Tag invalide (2 a 4 caracteres)"}
    if _get_my_clan_id(my_pseudo, my_tag):
        return {"ok": False, "error": "Tu es deja dans un clan"}

    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/clans",
        headers={**HEADERS, "Prefer": "return=representation"},
        json={"name": name, "tag": tag, "owner_pseudo": my_pseudo, "owner_tag": my_tag},
        timeout=8,
    )
    if r.status_code not in (200, 201):
        return {"ok": False, "error": "Ce nom ou tag est deja pris"}
    clan_id = r.json()[0]["id"]

    requests.post(
        f"{SUPABASE_URL}/rest/v1/clan_members",
        headers=HEADERS,
        json={"clan_id": clan_id, "pseudo": my_pseudo, "tag": my_tag},
        timeout=8,
    )
    return {"ok": True, "clan_id": clan_id}


def search_clans(query):
    query = query.strip()
    if len(query) < 2:
        return {"ok": False, "error": "Tape au moins 2 caracteres"}
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/clans",
        headers=HEADERS,
        params={"name": f"ilike.*{query}*", "select": "id,name,tag", "limit": "10"},
        timeout=8,
    )
    r.raise_for_status()
    return {"ok": True, "results": r.json()}


def join_clan(my_pseudo, my_tag, my_token, clan_id):
    if not verify_token(my_pseudo, my_tag, my_token):
        return {"ok": False, "error": "Session invalide, reconnecte-toi"}
    if _get_my_clan_id(my_pseudo, my_tag):
        return {"ok": False, "error": "Tu es deja dans un clan"}
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/clan_members",
        headers=HEADERS,
        json={"clan_id": clan_id, "pseudo": my_pseudo, "tag": my_tag},
        timeout=8,
    )
    if r.status_code not in (200, 201):
        return {"ok": False, "error": "Erreur serveur, reessaie"}
    return {"ok": True}


def leave_clan(my_pseudo, my_tag, my_token):
    if not verify_token(my_pseudo, my_tag, my_token):
        return {"ok": False, "error": "Session invalide, reconnecte-toi"}
    requests.delete(
        f"{SUPABASE_URL}/rest/v1/clan_members",
        headers=HEADERS,
        params={"pseudo": f"eq.{my_pseudo}", "tag": f"eq.{my_tag}"},
        timeout=8,
    )
    return {"ok": True}


def invite_to_clan(my_pseudo, my_tag, my_token, target_pseudo, target_tag):
    if not verify_token(my_pseudo, my_tag, my_token):
        return {"ok": False, "error": "Session invalide, reconnecte-toi"}
    clan_id = _get_my_clan_id(my_pseudo, my_tag)
    if not clan_id:
        return {"ok": False, "error": "Tu n'es dans aucun clan"}
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/clan_invites",
        headers={**HEADERS, "Prefer": "return=representation"},
        json={"clan_id": clan_id, "invited_pseudo": target_pseudo, "invited_tag": target_tag, "invited_by_pseudo": my_pseudo},
        timeout=8,
    )
    if r.status_code not in (200, 201):
        return {"ok": False, "error": "Erreur serveur, reessaie"}
    return {"ok": True}


def respond_clan_invite(my_pseudo, my_tag, my_token, invite_id, accept: bool):
    if not verify_token(my_pseudo, my_tag, my_token):
        return {"ok": False, "error": "Session invalide, reconnecte-toi"}
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/clan_invites",
        headers=HEADERS,
        params={"id": f"eq.{invite_id}", "invited_pseudo": f"eq.{my_pseudo}", "invited_tag": f"eq.{my_tag}", "select": "clan_id"},
        timeout=8,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return {"ok": False, "error": "Invitation introuvable"}
    clan_id = rows[0]["clan_id"]

    requests.delete(
        f"{SUPABASE_URL}/rest/v1/clan_invites",
        headers=HEADERS, params={"id": f"eq.{invite_id}"}, timeout=8,
    )
    if accept:
        if _get_my_clan_id(my_pseudo, my_tag):
            return {"ok": False, "error": "Tu es deja dans un clan"}
        requests.post(
            f"{SUPABASE_URL}/rest/v1/clan_members",
            headers=HEADERS,
            json={"clan_id": clan_id, "pseudo": my_pseudo, "tag": my_tag},
            timeout=8,
        )
    return {"ok": True}


def get_my_clan(my_pseudo, my_tag, my_token):
    if not verify_token(my_pseudo, my_tag, my_token):
        return {"ok": False, "error": "Session invalide, reconnecte-toi"}
    clan_id = _get_my_clan_id(my_pseudo, my_tag)
    if not clan_id:
        # inclure aussi les invitations en attente
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/clan_invites",
            headers=HEADERS,
            params={"invited_pseudo": f"eq.{my_pseudo}", "invited_tag": f"eq.{my_tag}", "select": "id,clan_id,invited_by_pseudo"},
            timeout=8,
        )
        r.raise_for_status()
        return {"ok": True, "clan": None, "invites": r.json()}

    rc = requests.get(
        f"{SUPABASE_URL}/rest/v1/clans",
        headers=HEADERS, params={"id": f"eq.{clan_id}", "select": "*"}, timeout=8,
    )
    rc.raise_for_status()
    clan = rc.json()[0] if rc.json() else None

    rm = requests.get(
        f"{SUPABASE_URL}/rest/v1/clan_members",
        headers=HEADERS, params={"clan_id": f"eq.{clan_id}", "select": "pseudo,tag"}, timeout=8,
    )
    rm.raise_for_status()
    return {"ok": True, "clan": clan, "members": rm.json(), "invites": []}
