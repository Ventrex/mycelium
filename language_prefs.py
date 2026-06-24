"""Global content-language preferences for Discover/Search.

Separate from AUDIO_LANGUAGE_PREFERENCE/EXCLUDE_LANGUAGES in settings.py,
which only affect which torrent release is picked once an item is already
requested. This module controls which movies/shows are shown at all, based
on TMDB's original_language field, so e.g. Bollywood (Hindi-language) films
never appear in Discover or Search.

Stored as one JSON blob in the settings table (LANGUAGE_PREFS):
  {
    "allowed": ["en", "nl"],   # if non-empty, only these original languages are shown
    "excluded": ["hi"]         # these original languages are always hidden, regardless of "allowed"
  }
Both lists use ISO 639-1 codes as returned by TMDB.
"""
import json
import logging

import db

log = logging.getLogger(__name__)

_KEY = "LANGUAGE_PREFS"
_DEFAULT = {"allowed": [], "excluded": []}


def get_prefs() -> dict:
    raw = db.get_setting(_KEY)
    if not raw:
        return dict(_DEFAULT)
    try:
        loaded = json.loads(raw)
    except (ValueError, TypeError):
        return dict(_DEFAULT)
    merged = dict(_DEFAULT)
    merged.update(loaded)
    return merged


def set_prefs(prefs: dict) -> None:
    merged = dict(_DEFAULT)
    merged.update(prefs or {})
    db.set_setting(_KEY, json.dumps(merged))


def filter_items(items: list[dict]) -> list[dict]:
    """Drop movies/shows whose original_language isn't wanted. Items without
    an original_language (e.g. person results) always pass through untouched."""
    prefs = get_prefs()
    allowed = set(prefs.get("allowed") or [])
    excluded = set(prefs.get("excluded") or [])
    if not allowed and not excluded:
        return items
    out = []
    for it in items:
        lang = it.get("original_language")
        if not lang:
            out.append(it)
            continue
        if excluded and lang in excluded:
            continue
        if allowed and lang not in allowed:
            continue
        out.append(it)
    return out
