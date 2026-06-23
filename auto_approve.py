"""Per-genre auto-approve rules: Netflix-style auto-fill.

Rules are stored as one JSON blob per media type in the settings table:
  AUTO_APPROVE_RULES_MOVIE / AUTO_APPROVE_RULES_TV
    {
      "28": {"enabled": true, "year_from": null, "year_to": 2020, "auto_request_trending": true},
      ...
    }

`enabled` controls whether a manually-submitted request in that genre/year
range bypasses the pending-approval queue (see is_auto_approved()).
`auto_request_trending` controls whether the scheduled run() job proactively
requests popular items in that genre/year range on its own, without anyone
asking - the actual "fill my list automatically" behaviour.
"""
import logging

import db
import processor
import tmdb
from config import AUTO_ADD_MIN_RATING, AUTO_ADD_MIN_VOTES, AUTO_ADD_REGION
from webhook_parser import MediaRequest

log = logging.getLogger(__name__)

AUTO_REQUEST_PER_GENRE_LIMIT = 5


def _key(media_type: str) -> str:
    return f"AUTO_APPROVE_RULES_{'MOVIE' if media_type == 'movie' else 'TV'}"


def get_rules(media_type: str) -> dict:
    import json
    raw = db.get_setting(_key(media_type))
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return {}


def set_rules(media_type: str, rules: dict) -> None:
    import json
    db.set_setting(_key(media_type), json.dumps(rules or {}))


def _rule_for_year(rule: dict, year: int | str | None) -> bool:
    if not year:
        return True
    try:
        year = int(str(year)[:4])
    except (ValueError, TypeError):
        return True
    year_from, year_to = rule.get("year_from"), rule.get("year_to")
    if year_from and year < int(year_from):
        return False
    if year_to and year > int(year_to):
        return False
    return True


def is_auto_approved(media_type: str, genre_ids: list[int] | None, year: int | str | None) -> bool:
    """True if any of the item's genres has an enabled auto-approve rule covering its year."""
    if not genre_ids:
        return False
    rules = get_rules(media_type)
    for gid in genre_ids:
        rule = rules.get(str(gid))
        if rule and rule.get("enabled") and _rule_for_year(rule, year):
            return True
    return False


def _passes_filters(item: dict) -> bool:
    if (item.get("rating") or 0) < AUTO_ADD_MIN_RATING:
        return False
    if (item.get("votes") or 0) < AUTO_ADD_MIN_VOTES:
        return False
    return True


def _queue_movie(item: dict, seen: set[str]) -> bool:
    tmdb_id, title = item.get("tmdb_id"), item.get("title") or ""
    if not tmdb_id or not title:
        return False
    imdb_id = tmdb.tmdb_to_imdb(tmdb_id, media_type="movie")
    if not imdb_id or imdb_id in seen:
        return False
    log.info("Auto-approve: queueing movie %s (%s)", title, imdb_id)
    try:
        processor.process(MediaRequest(title=title, media_type="movie", imdb_id=imdb_id,
                                        seasons=[], tmdb_id=tmdb_id))
        seen.add(imdb_id)
        return True
    except Exception as exc:
        log.warning("Auto-approve: processor failed for %s: %s", title, exc)
        return False


def _queue_series(item: dict, seen: set[str]) -> bool:
    tmdb_id, title = item.get("tmdb_id"), item.get("title") or ""
    if not tmdb_id or not title:
        return False
    imdb_id = tmdb.tmdb_to_imdb(tmdb_id, media_type="tv")
    if not imdb_id or imdb_id in seen:
        return False
    show = tmdb.get_show_info(tmdb_id) or {}
    seasons = list(range(1, (show.get("number_of_seasons") or 1) + 1))
    log.info("Auto-approve: monitoring series %s (%s, %d seasons)", title, imdb_id, len(seasons))
    try:
        db.upsert_monitored_series(imdb_id, tmdb_id, title, seasons)
        seen.add(imdb_id)
        return True
    except Exception as exc:
        log.warning("Auto-approve: upsert_monitored_series failed for %s: %s", title, exc)
        return False


def run() -> int:
    """Scheduled job: for every genre with auto_request_trending enabled,
    fetch the most popular items in that genre/year window and queue the
    ones we don't have yet - this is what auto-fills the library."""
    total = 0
    seen_movies = {r["imdb_id"] for r in db.get_recent(2000) if r.get("media_type") == "movie"}
    seen_series = {s["imdb_id"] for s in db.get_all_monitored_series()}

    for media_type, queue_fn, seen in (("movie", _queue_movie, seen_movies),
                                        ("tv", _queue_series, seen_series)):
        rules = get_rules(media_type)
        for genre_id_str, rule in rules.items():
            if not rule.get("enabled") or not rule.get("auto_request_trending"):
                continue
            genre_id = int(genre_id_str)
            items = tmdb.discover_by_genre(media_type, genre_id, rule.get("year_from"),
                                            rule.get("year_to"), region=AUTO_ADD_REGION)
            added = 0
            for item in items:
                if added >= AUTO_REQUEST_PER_GENRE_LIMIT:
                    break
                if not _passes_filters(item):
                    continue
                if queue_fn(item, seen):
                    added += 1
            if added:
                log.info("Auto-approve genre=%s/%s: %d new item(s) queued", media_type, genre_id, added)
            total += added

    log.info("Auto-approve: %d total item(s) added across all genre rules", total)
    return total
