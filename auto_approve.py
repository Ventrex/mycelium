"""Per-genre auto-approve rules: Netflix-style auto-fill.

Rules are stored as one JSON blob per media type in the settings table:
  AUTO_APPROVE_RULES_MOVIE / AUTO_APPROVE_RULES_TV
    {
      "28": {"enabled": true, "year_from": null, "year_to": 2020,
             "auto_request_trending": true, "min_votes": null},
      ...
    }

`enabled` controls whether a manually-submitted request in that genre/year
range bypasses the pending-approval queue (see is_auto_approved()).
`auto_request_trending` controls whether the scheduled run() job proactively
requests popular items in that genre/year range on its own, without anyone
asking - the actual "fill my list automatically" behaviour.
`min_votes` overrides the global AUTO_ADD_MIN_VOTES threshold for this rule
only; leave null to use the global default.
"""
import logging

import db
import processor
import settings as _settings
import tmdb
from config import (
    AUTO_ADD_MIN_RATING,
    AUTO_ADD_MIN_VOTES,
    AUTO_ADD_REGION,
    AUTO_APPROVE_DAILY_LIMIT_MOVIE,
    AUTO_APPROVE_DAILY_LIMIT_TV,
    AUTO_APPROVE_MAX_PAGES,
    AUTO_APPROVE_MOVIE_PER_GENRE_LIMIT,
    AUTO_APPROVE_PER_GENRE_LIMIT,
    AUTO_APPROVE_TV_PER_GENRE_LIMIT,
    AUTO_REQUEST_TRENDING_MOVIE_LIMIT,
    AUTO_REQUEST_TRENDING_TV_LIMIT,
    FAVORITE_ACTOR_PER_ACTOR_LIMIT,
    FAVORITE_ACTOR_RECENCY_YEARS,
)
from webhook_parser import MediaRequest

log = logging.getLogger(__name__)

# TMDB TV genre ids for non-scripted formats we never want to auto-queue from an
# actor's filmography: 10767 Talk, 10763 News, 10764 Reality, 10766 Soap. These
# are the formats an actor only ever "guests" on; a real scripted guest role
# (e.g. Bruce Willis in Friends, a Comedy with a named character) is still kept.
_NON_SCRIPTED_GENRE_IDS = {10767, 10763, 10764, 10766}


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


def _passes_filters(item: dict, min_votes: int | None = None) -> bool:
    # Coerce defensively: a settings override can arrive as a str, and a raw
    # comparison (float < str) would raise and kill the whole auto-approve run.
    try:
        min_rating = float(_settings.get("AUTO_ADD_MIN_RATING", AUTO_ADD_MIN_RATING))
    except (TypeError, ValueError):
        min_rating = AUTO_ADD_MIN_RATING
    if (item.get("rating") or 0) < min_rating:
        return False
    raw_votes = min_votes if min_votes is not None else _settings.get("AUTO_ADD_MIN_VOTES", AUTO_ADD_MIN_VOTES)
    try:
        threshold = int(raw_votes)
    except (TypeError, ValueError):
        threshold = AUTO_ADD_MIN_VOTES
    if (item.get("votes") or 0) < threshold:
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
    seen.add(imdb_id)
    try:
        return processor.process(MediaRequest(title=title, media_type="movie", imdb_id=imdb_id,
                                                seasons=[], tmdb_id=tmdb_id))
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


def _has_blacklisted_person(media_type: str, tmdb_id: int | None, person_bl: set[int]) -> bool:
    """True if any cast member of this item is on the actor blacklist."""
    if not person_bl or not tmdb_id:
        return False
    try:
        cast_ids = tmdb.credits_person_ids(media_type, tmdb_id)
    except Exception:
        return False
    return any(pid in person_bl for pid in cast_ids)


def _is_unreleased(item: dict) -> bool:
    """True if the title's release/air date is in the future. We never auto-queue
    unreleased titles: pre-release blockbusters attract fake/junk cached torrents
    that would otherwise get a .strm and show in the library playing garbage.
    An unknown/empty date is treated as released (the processor does a definitive
    TMDB date check before accepting any release)."""
    rd = (item.get("release_date") or "").strip()
    if not rd:
        return False
    import datetime
    return rd > datetime.date.today().isoformat()


def _is_non_scripted_or_guest(item: dict) -> bool:
    """True for talk shows, news, reality TV, or a self/guest appearance - favoriting
    an actor should queue their actual acting roles, not every programme they once
    guested on as themselves."""
    if set(item.get("genre_ids") or []) & _NON_SCRIPTED_GENRE_IDS:
        return True
    character = (item.get("character") or "").strip().lower()
    return character in ("self", "himself", "herself") or character.startswith("self ")


def _is_recent_or_upcoming(item: dict) -> bool:
    """True if a credit is within the configured recency window. With
    FAVORITE_ACTOR_RECENCY_YEARS=0 (the default) there is no window and the
    actor's whole back catalogue qualifies."""
    try:
        recency = int(_settings.get("FAVORITE_ACTOR_RECENCY_YEARS", FAVORITE_ACTOR_RECENCY_YEARS))
    except (TypeError, ValueError):
        recency = FAVORITE_ACTOR_RECENCY_YEARS
    if recency <= 0:
        return True
    year = item.get("year")
    if not year:
        return True
    try:
        import datetime
        return int(str(year)[:4]) >= datetime.date.today().year - recency
    except (ValueError, TypeError):
        return True


def _run_favorite_actors(seen_movies: set[str], seen_series: set[str],
                          movie_bl: set[int], tv_bl: set[int],
                          movie_remaining: int | None = None,
                          tv_remaining: int | None = None) -> tuple[int, int]:
    """For every favorited actor, queue their recent/upcoming movies and shows
    that aren't already in the library. Movies and series each respect their
    own independent remaining budget (None means no cap for that type), so an
    exhausted movie cap doesn't block queueing series for the same actor.
    Returns (movies_added, series_added)."""
    try:
        per_actor = int(_settings.get("FAVORITE_ACTOR_PER_ACTOR_LIMIT", FAVORITE_ACTOR_PER_ACTOR_LIMIT))
    except (TypeError, ValueError):
        per_actor = FAVORITE_ACTOR_PER_ACTOR_LIMIT
    movies_added = 0
    series_added = 0
    for actor in db.get_favorite_actors():
        movie_done = movie_remaining is not None and movies_added >= movie_remaining
        tv_done = tv_remaining is not None and series_added >= tv_remaining
        if movie_done and tv_done:
            break
        person_id, name = actor.get("tmdb_id"), actor.get("name") or ""
        try:
            detail = tmdb.person_details(person_id)
        except Exception as exc:
            log.warning("Auto-approve: person_details failed for %s: %s", name, exc)
            continue
        if not detail:
            continue
        actor_movies = 0
        actor_series = 0
        for item in detail.get("filmography") or []:
            if per_actor > 0 and actor_movies + actor_series >= per_actor:
                break
            media_type = item.get("media_type")
            if media_type not in ("movie", "tv"):
                continue
            if media_type == "movie":
                if movie_remaining is not None and movies_added + actor_movies >= movie_remaining:
                    continue
            else:
                if tv_remaining is not None and series_added + actor_series >= tv_remaining:
                    continue
            media_bl = movie_bl if media_type == "movie" else tv_bl
            if item.get("tmdb_id") in media_bl or not _is_recent_or_upcoming(item):
                continue
            if _is_unreleased(item) or _is_non_scripted_or_guest(item):
                continue
            queue_fn = _queue_movie if media_type == "movie" else _queue_series
            seen = seen_movies if media_type == "movie" else seen_series
            if queue_fn(item, seen):
                if media_type == "movie":
                    actor_movies += 1
                else:
                    actor_series += 1
        if actor_movies or actor_series:
            log.info("Auto-approve favorite actor %s: %d movie(s), %d series queued",
                      name, actor_movies, actor_series)
        movies_added += actor_movies
        series_added += actor_series
    return movies_added, series_added


def _empty_genre_result(media_type: str, genre_id: int, target: int) -> dict:
    return {
        "media_type": media_type,
        "genre_id": genre_id,
        "target": target,
        "scanned": 0,
        "skipped": 0,
        "queued": 0,
        "exhausted": False,
    }


def _discover_genre_page(media_type: str, genre_id: int, rule: dict, page: int) -> list[dict]:
    return tmdb.discover_by_genre(
        media_type,
        genre_id,
        rule.get("year_from"),
        rule.get("year_to"),
        page=page,
        region=AUTO_ADD_REGION,
    )


def _fill_genre(media_type: str, genre_id: int, rule: dict, target: int,
                seen: set[str], media_bl: set[int], person_bl: set[int],
                max_pages: int) -> dict:
    """Fill one enabled genre to its own successful queue target.

    Skips (already requested/monitored, blacklisted, unreleased, no IMDb, filter
    misses, processor failures, etc.) are tracked for observability but never
    count toward the target. The scan continues until `target` successful queues
    have been made or TMDB pages are exhausted.
    """
    result = _empty_genre_result(media_type, genre_id, target)
    queue_fn = _queue_movie if media_type == "movie" else _queue_series

    if target <= 0:
        result["exhausted"] = True
        log.info(
            "Auto-approve %s genre %s: scanned=%d skipped=%d queued=%d exhausted=%s",
            media_type, genre_id, result["scanned"], result["skipped"],
            result["queued"], result["exhausted"],
        )
        return result

    for page in range(1, max_pages + 1):
        items = _discover_genre_page(media_type, genre_id, rule, page)
        if not items:
            result["exhausted"] = True
            break
        for item in items:
            if result["queued"] >= target:
                break
            result["scanned"] += 1
            try:
                if item.get("tmdb_id") in media_bl:
                    result["skipped"] += 1
                    continue
                if _is_unreleased(item):
                    result["skipped"] += 1
                    continue
                if not _passes_filters(item, rule.get("min_votes")):
                    result["skipped"] += 1
                    continue
                if _has_blacklisted_person(media_type, item.get("tmdb_id"), person_bl):
                    result["skipped"] += 1
                    continue
                if queue_fn(item, seen):
                    result["queued"] += 1
                else:
                    result["skipped"] += 1
            except Exception as exc:
                result["skipped"] += 1
                log.warning("Auto-approve: skipping %s after error: %s",
                            item.get("title") or item.get("tmdb_id"), exc)
        if result["queued"] >= target:
            break
    else:
        result["exhausted"] = result["queued"] < target

    log.info(
        "Auto-approve %s genre %s: scanned=%d skipped=%d queued=%d exhausted=%s",
        media_type, genre_id, result["scanned"], result["skipped"],
        result["queued"], result["exhausted"],
    )
    return result


def _fill_per_genre(seen_movies: set[str], seen_series: set[str],
                    movie_bl: set[int], tv_bl: set[int],
                    person_bl: set[int]) -> dict:
    """Fill every enabled movie and TV genre independently.

    Movie and TV genres have separate per-genre limits. There is deliberately no
    shared movie+TV cap here, so films cannot starve series and one movie genre
    cannot consume another genre's target.
    """
    movie_target = _settings.get("AUTO_APPROVE_MOVIE_PER_GENRE_LIMIT", AUTO_APPROVE_MOVIE_PER_GENRE_LIMIT)
    tv_target = _settings.get("AUTO_APPROVE_TV_PER_GENRE_LIMIT", AUTO_APPROVE_TV_PER_GENRE_LIMIT)
    max_pages = _settings.get("AUTO_APPROVE_MAX_PAGES", AUTO_APPROVE_MAX_PAGES)
    summary = {
        "movies_queued": 0,
        "series_queued": 0,
        "total_queued": 0,
        "genres": {"movie": [], "tv": []},
    }

    for media_type, target, seen, media_bl in (
        ("movie", movie_target, seen_movies, movie_bl),
        ("tv", tv_target, seen_series, tv_bl),
    ):
        rules = get_rules(media_type)
        enabled = [(int(gid), rule) for gid, rule in rules.items() if rule.get("auto_request_trending")]
        if not enabled:
            log.info("Auto-approve: no %s genre has 'Auto-fill trending' enabled", media_type)
            continue
        log.info("Auto-approve: filling %d %s genre(s), per-genre target=%s, max_pages=%s",
                 len(enabled), media_type, target, max_pages)
        for gid, rule in enabled:
            result = _fill_genre(media_type, gid, rule, target, seen, media_bl, person_bl, max_pages)
            summary["genres"][media_type].append(result)
            if media_type == "movie":
                summary["movies_queued"] += result["queued"]
            else:
                summary["series_queued"] += result["queued"]

    summary["total_queued"] = summary["movies_queued"] + summary["series_queued"]
    return summary


def run(total_limit: int | None = None, tv_limit: int | None = None) -> dict:
    """Scheduled/manual job for Netflix-style per-genre auto-fill.

    Each movie genre with auto_request_trending enabled gets its own movie
    target. Each TV genre gets its own TV target. Existing requests, monitored
    series, duplicate IMDb ids, blacklists, unreleased titles, no-IMDb mappings,
    skipped items, and processor failures do not count toward those targets.

    The legacy total_limit/tv_limit arguments and daily settings are intentionally
    not used for genre filling anymore; they remain available for backwards
    compatibility with favorite-actor queueing only.
    """
    legacy_movie_limit = total_limit
    if legacy_movie_limit is None:
        legacy_movie_limit = _settings.get("AUTO_APPROVE_DAILY_LIMIT_MOVIE", AUTO_APPROVE_DAILY_LIMIT_MOVIE)
    legacy_tv_limit = tv_limit
    if legacy_tv_limit is None:
        legacy_tv_limit = _settings.get("AUTO_APPROVE_DAILY_LIMIT_TV", AUTO_APPROVE_DAILY_LIMIT_TV)

    seen_movies = {r["imdb_id"] for r in db.get_recent(2000) if r.get("media_type") == "movie" and r.get("imdb_id")}
    seen_series = {s["imdb_id"] for s in db.get_all_monitored_series() if s.get("imdb_id")}
    movie_bl = db.get_content_blacklist_ids("movie")
    tv_bl = db.get_content_blacklist_ids("tv")
    person_bl = db.get_content_blacklist_ids("person")

    summary = _fill_per_genre(seen_movies, seen_series, movie_bl, tv_bl, person_bl)

    movie_actor_remaining = legacy_movie_limit if legacy_movie_limit and legacy_movie_limit > 0 else None
    tv_actor_remaining = legacy_tv_limit if legacy_tv_limit and legacy_tv_limit > 0 else None
    actor_movies, actor_series = _run_favorite_actors(
        seen_movies, seen_series, movie_bl, tv_bl, movie_actor_remaining, tv_actor_remaining)
    summary["favorite_actor_movies_queued"] = actor_movies
    summary["favorite_actor_series_queued"] = actor_series
    summary["movies_queued"] += actor_movies
    summary["series_queued"] += actor_series
    summary["total_queued"] = summary["movies_queued"] + summary["series_queued"]

    log.info("Auto-approve run complete: %d movie(s) + %d series = %d queued",
             summary["movies_queued"], summary["series_queued"], summary["total_queued"])
    return summary


def run_trending(movie_limit: int | None = None, tv_limit: int | None = None) -> dict:
    """Request the top trending movies and shows, capped per type.

    Reuses the same safety rules as the genre fill: already-requested movies,
    monitored series, blacklisted titles/people and unreleased titles are
    skipped and never count toward the cap. Returns a summary.
    """
    if movie_limit is None:
        movie_limit = _settings.get("AUTO_REQUEST_TRENDING_MOVIE_LIMIT", AUTO_REQUEST_TRENDING_MOVIE_LIMIT)
    if tv_limit is None:
        tv_limit = _settings.get("AUTO_REQUEST_TRENDING_TV_LIMIT", AUTO_REQUEST_TRENDING_TV_LIMIT)
    try:
        movie_limit = int(movie_limit)
        tv_limit = int(tv_limit)
    except (TypeError, ValueError):
        movie_limit, tv_limit = AUTO_REQUEST_TRENDING_MOVIE_LIMIT, AUTO_REQUEST_TRENDING_TV_LIMIT

    seen_movies = {r["imdb_id"] for r in db.get_recent(2000) if r.get("media_type") == "movie" and r.get("imdb_id")}
    seen_series = {s["imdb_id"] for s in db.get_all_monitored_series() if s.get("imdb_id")}
    movie_bl = db.get_content_blacklist_ids("movie")
    tv_bl = db.get_content_blacklist_ids("tv")
    person_bl = db.get_content_blacklist_ids("person")

    summary = {"movies_queued": 0, "series_queued": 0, "total_queued": 0}

    for media_type, limit, seen, media_bl, queue_fn, key in (
        ("movie", movie_limit, seen_movies, movie_bl, _queue_movie, "movies_queued"),
        ("tv", tv_limit, seen_series, tv_bl, _queue_series, "series_queued"),
    ):
        if limit <= 0:
            continue
        try:
            items = tmdb.trending(media_type, "week", page=1)
        except Exception as exc:
            log.warning("Trending auto-request: fetch failed for %s: %s", media_type, exc)
            continue
        for item in items:
            if summary[key] >= limit:
                break
            try:
                if item.get("tmdb_id") in media_bl or _is_unreleased(item):
                    continue
                if _has_blacklisted_person(media_type, item.get("tmdb_id"), person_bl):
                    continue
                if queue_fn(item, seen):
                    summary[key] += 1
            except Exception as exc:
                log.warning("Trending auto-request: skipping %s after error: %s",
                            item.get("title") or item.get("tmdb_id"), exc)

    summary["total_queued"] = summary["movies_queued"] + summary["series_queued"]
    log.info("Trending auto-request complete: %d movie(s) + %d series = %d queued",
             summary["movies_queued"], summary["series_queued"], summary["total_queued"])
    return summary
