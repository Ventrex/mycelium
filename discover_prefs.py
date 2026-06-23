"""Per-media-type genre browsing preferences for the Shows/Movies tabs.

Stored as one JSON blob per media type in the settings table:
  DISCOVER_PREFS_MOVIE / DISCOVER_PREFS_TV
    {
      "hidden_genres": [27, 99],
      "genre_order": [28, 12, 16],          # explicit order; genres not listed sort after, by TMDB order
      "year_from": 1900,                     # global default lower bound, applies to all genres unless overridden
      "year_to": 2026,                       # global default upper bound
      "genre_years": {"28": {"from": null, "to": 2015}}   # per-genre override; null = inherit the global default
    }
"""
import json
import logging

import db

log = logging.getLogger(__name__)

_DEFAULT = {
    "hidden_genres": [],
    "genre_order": [],
    "year_from": None,
    "year_to": None,
    "genre_years": {},
}


def _key(media_type: str) -> str:
    return f"DISCOVER_PREFS_{'MOVIE' if media_type == 'movie' else 'TV'}"


def get_prefs(media_type: str) -> dict:
    raw = db.get_setting(_key(media_type))
    if not raw:
        return dict(_DEFAULT)
    try:
        loaded = json.loads(raw)
    except (ValueError, TypeError):
        return dict(_DEFAULT)
    merged = dict(_DEFAULT)
    merged.update(loaded)
    return merged


def set_prefs(media_type: str, prefs: dict) -> None:
    merged = dict(_DEFAULT)
    merged.update(prefs or {})
    db.set_setting(_key(media_type), json.dumps(merged))


def effective_year_range(media_type: str, genre_id: int) -> tuple[int | None, int | None]:
    """Year-from/year-to to use when browsing a given genre, applying the
    per-genre override over the global default (each bound independently)."""
    prefs = get_prefs(media_type)
    override = (prefs.get("genre_years") or {}).get(str(genre_id)) or {}
    year_from = override.get("from") if override.get("from") is not None else prefs.get("year_from")
    year_to = override.get("to") if override.get("to") is not None else prefs.get("year_to")
    if year_from and year_to and year_from > year_to:
        year_from = None
    return year_from, year_to


def ordered_visible_genres(media_type: str, all_genres: list[dict]) -> list[dict]:
    """Apply hidden_genres + genre_order to a TMDB genre list."""
    prefs = get_prefs(media_type)
    hidden = set(prefs.get("hidden_genres") or [])
    order = prefs.get("genre_order") or []
    visible = [g for g in all_genres if g.get("id") not in hidden]
    order_index = {gid: i for i, gid in enumerate(order)}
    visible.sort(key=lambda g: order_index.get(g.get("id"), len(order) + g.get("id", 0)))
    return visible
