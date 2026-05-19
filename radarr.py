"""Radarr API client — pull all movies from an existing Radarr instance."""
import logging

import requests

log = logging.getLogger(__name__)


def _headers(api_key: str) -> dict:
    return {"X-Api-Key": api_key, "Accept": "application/json"}


def list_movies(url: str, api_key: str, timeout: int = 30) -> list[dict]:
    """Return all movies from Radarr. Each item has tmdbId, imdbId, title, year, monitored."""
    base = url.rstrip("/")
    log.info("Radarr: fetching movies from %s", base)
    resp = requests.get(f"{base}/api/v3/movie", headers=_headers(api_key), timeout=timeout)
    resp.raise_for_status()
    items = resp.json() or []
    out = []
    for m in items:
        out.append({
            "tmdb_id": m.get("tmdbId"),
            "imdb_id": m.get("imdbId") or "",
            "title": m.get("title") or "",
            "year": m.get("year"),
            "monitored": bool(m.get("monitored")),
            "has_file": bool(m.get("hasFile")),
        })
    log.info("Radarr: %d movie(s) returned", len(out))
    return out


def ping(url: str, api_key: str, timeout: int = 8) -> bool:
    try:
        resp = requests.get(f"{url.rstrip('/')}/api/v3/system/status",
                            headers=_headers(api_key), timeout=timeout)
        return resp.status_code == 200
    except Exception as exc:
        log.warning("Radarr ping failed: %s", exc)
        return False
