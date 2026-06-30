"""MDBList API wrapper - per-user API key, list sync, optional auto-request."""
from __future__ import annotations

import logging
import time

import requests as req_lib

import db
import settings

log = logging.getLogger(__name__)

_BASE = "https://api.mdblist.com"


# ── per-user API key storage ──────────────────────────────────────────────────

def get_key(user_id: int) -> dict | None:
    with db._connect() as c:
        row = c.execute("SELECT * FROM mdblist_keys WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def set_key(user_id: int, api_key: str) -> None:
    with db._connect() as c:
        c.execute(
            "INSERT INTO mdblist_keys (user_id, api_key) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET api_key=excluded.api_key",
            (user_id, api_key),
        )


def clear_key(user_id: int) -> None:
    with db._connect() as c:
        c.execute("DELETE FROM mdblist_keys WHERE user_id=?", (user_id,))


def _mark_synced(user_id: int) -> None:
    with db._connect() as c:
        c.execute("UPDATE mdblist_keys SET synced_at=? WHERE user_id=?",
                  (time.strftime("%Y-%m-%d %H:%M:%S"), user_id))


def status(user_id: int) -> dict:
    rec = get_key(user_id)
    return {
        "connected": bool(rec and rec.get("api_key")),
        "synced_at": rec.get("synced_at") if rec else None,
    }


# ── MDBList HTTP ──────────────────────────────────────────────────────────────

def _get(path: str, api_key: str, params: dict | None = None):
    p = dict(params or {})
    p["apikey"] = api_key
    r = req_lib.get(f"{_BASE}{path}", params=p, timeout=15)
    r.raise_for_status()
    return r.json()


def _fetch_lists(api_key: str) -> list[dict]:
    try:
        data = _get("/lists/user", api_key)
    except Exception as exc:
        log.warning("MDBList lists fetch failed: %s", exc)
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("lists") or data.get("results") or []
    return []


def _iter_items(payload):
    """Yield raw item dicts whether the API returns {movies, shows}, {results},
    or a flat list."""
    if isinstance(payload, dict):
        emitted = False
        for key in ("movies", "shows"):
            for it in payload.get(key) or []:
                emitted = True
                yield it
        if not emitted:
            for it in payload.get("results") or []:
                yield it
    elif isinstance(payload, list):
        for it in payload:
            yield it


def _fetch_list_items(api_key: str, list_id) -> list[dict]:
    try:
        return list(_iter_items(_get(f"/lists/{list_id}/items", api_key)))
    except Exception as exc:
        log.warning("MDBList items fetch failed for list %s: %s", list_id, exc)
        return []


def _norm(it: dict) -> dict | None:
    imdb_id = it.get("imdb_id") or it.get("imdbid")
    if not imdb_id:
        return None
    tmdb_raw = it.get("tmdb_id") or it.get("tmdbid") or it.get("id")
    try:
        tmdb_id = int(tmdb_raw) if tmdb_raw else None
    except (TypeError, ValueError):
        tmdb_id = None
    mt = str(it.get("mediatype") or it.get("media_type") or "movie").lower()
    media_type = "tv" if mt in ("show", "tv", "series") else "movie"
    return {
        "imdb_id": imdb_id,
        "tmdb_id": tmdb_id,
        "title": it.get("title") or "",
        "media_type": media_type,
    }


# ── sync + auto-request ───────────────────────────────────────────────────────

def sync_user(user_id: int) -> int:
    """Pull all items from this user's MDBList lists into the Mycelium watchlist."""
    rec = get_key(user_id)
    if not rec or not rec.get("api_key"):
        return 0
    api_key = rec["api_key"]
    added = 0
    for lst in _fetch_lists(api_key):
        list_id = lst.get("id") or lst.get("slug")
        if not list_id:
            continue
        for raw in _fetch_list_items(api_key, list_id):
            item = _norm(raw)
            if not item:
                continue
            try:
                db.add_to_watchlist(user_id, item["imdb_id"], item["tmdb_id"],
                                    item["media_type"], item["title"], None)
                added += 1
            except Exception:
                pass
    _mark_synced(user_id)
    return added


def auto_request_user(user_id: int, limit: int) -> int:
    """Request up to `limit` not-yet-requested watchlist items for this user.
    Existing requests and monitored series are skipped so repeated runs drain the
    backlog instead of re-processing. Returns the number of new items requested."""
    if limit <= 0:
        return 0
    import processor
    import tmdb
    from webhook_parser import MediaRequest

    monitored = {s["imdb_id"] for s in db.get_all_monitored_series() if s.get("imdb_id")}
    requested = 0
    for w in db.get_watchlist(user_id):
        if requested >= limit:
            break
        imdb_id = w.get("imdb_id")
        tmdb_id = w.get("tmdb_id")
        title = w.get("title") or ""
        media_type = "movie" if w.get("media_type") == "movie" else "series"
        if not imdb_id:
            continue
        try:
            if media_type == "movie":
                if db.get_request_by_imdb(imdb_id):
                    continue
                if processor.process(MediaRequest(title=title, media_type="movie",
                                                  imdb_id=imdb_id, seasons=[], tmdb_id=tmdb_id)):
                    requested += 1
            else:
                if imdb_id in monitored:
                    continue
                show = tmdb.get_show_info(tmdb_id) if tmdb_id else {}
                seasons = list(range(1, ((show or {}).get("number_of_seasons") or 1) + 1))
                db.upsert_monitored_series(imdb_id, tmdb_id, title, seasons)
                monitored.add(imdb_id)
                requested += 1
        except Exception as exc:
            log.warning("MDBList auto-request failed for %s: %s", title or imdb_id, exc)
    return requested


def sync_all_users() -> None:
    """Background job: sync MDBList lists (and optionally auto-request) for every
    user who has stored an API key."""
    auto_request = bool(settings.get("MDBLIST_AUTO_REQUEST", False))
    try:
        limit = int(settings.get("MDBLIST_AUTO_REQUEST_LIMIT", 10))
    except (TypeError, ValueError):
        limit = 10
    with db._connect() as c:
        rows = c.execute("SELECT user_id FROM mdblist_keys").fetchall()
    for row in rows:
        uid = row["user_id"]
        try:
            n = sync_user(uid)
            requested = auto_request_user(uid, limit) if auto_request else 0
            log.info("MDBList sync: user %d  -  %d items, %d auto-requested", uid, n, requested)
        except Exception as exc:
            log.warning("MDBList sync failed for user %d: %s", uid, exc)
