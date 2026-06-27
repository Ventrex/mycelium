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
    AUTO_APPROVE_PER_GENRE_LIMIT,
)
from webhook_parser import MediaRequest

log = logging.getLogger(__name__)

FAVORITE_ACTOR_PER_ACTOR_LIMIT = 3
FAVORITE_ACTOR_RECENCY_YEARS = 1

# TMDB TV genre ids for non-scripted formats we never want to auto-queue from an
# actor's filmography: 10767 Talk, 10763 News, 10764 Reality.
_NON_SCRIPTED_GENRE_IDS = {10767, 10763, 10764}


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
    """True if a filmography credit looks like new/upcoming work rather than an
    actor's back catalog - favoriting someone shouldn't queue their whole career."""
    year = item.get("year")
    if not year:
        return True
    try:
        import datetime
        return int(str(year)[:4]) >= datetime.date.today().year - FAVORITE_ACTOR_RECENCY_YEARS
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
            if actor_movies + actor_series >= FAVORITE_ACTOR_PER_ACTOR_LIMIT:
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


def _genre_candidates(media_type: str, genre_id: int, rule: dict, media_bl: set[int],
                       person_bl: set[int], max_pages: int):
    """Lazily yield queue-ready (filtered, released, not-blacklisted) items for one
    genre, fetching TMDB pages on demand. Pages are only fetched as the consumer
    pulls items, so a round-robin caller never over-fetches a genre it stops early."""
    for page in range(1, max_pages + 1):
        items = tmdb.discover_by_genre(media_type, genre_id, rule.get("year_from"),
                                        rule.get("year_to"), page=page, region=AUTO_ADD_REGION)
        if not items:
            return  # no more results in this genre/year window
        for item in items:
            try:
                if item.get("tmdb_id") in media_bl:
                    continue
                if _is_unreleased(item):
                    continue
                if not _passes_filters(item, rule.get("min_votes")):
                    continue
                if _has_blacklisted_person(media_type, item.get("tmdb_id"), person_bl):
                    continue
            except Exception as exc:
                log.warning("Auto-approve: skipping %s after error: %s",
                            item.get("title") or item.get("tmdb_id"), exc)
                continue
            yield item


def _fill_round_robin(total_cap: int | None, series_subcap: int | None,
                       seen_movies: set[str], seen_series: set[str],
                       movie_bl: set[int], tv_bl: set[int],
                       person_bl: set[int]) -> tuple[int, int]:
    """Fill the library from every genre with "Auto-fill trending" enabled, across
    BOTH the Movies and Shows tabs, into a single shared budget of `total_cap`
    titles. Genres are visited round-robin (one success per genre per round) so all
    genres are represented at once instead of the first couple draining the budget.
    `series_subcap` optionally limits how many of the total may be series.

    Note: the fill is gated on `auto_request_trending` alone, independent of
    `enabled` (which only governs whether *manual* requests in that genre skip the
    pending-approval queue). Returns (movies_added, series_added)."""
    per_genre_limit = _settings.get("AUTO_APPROVE_PER_GENRE_LIMIT", AUTO_APPROVE_PER_GENRE_LIMIT)
    max_pages = _settings.get("AUTO_APPROVE_MAX_PAGES", AUTO_APPROVE_MAX_PAGES)

    # One lazy candidate stream per eligible genre, movies and series together.
    streams = []  # [media_type, genre_id, generator, queued_count]
    for media_type in ("movie", "tv"):
        media_bl = movie_bl if media_type == "movie" else tv_bl
        for gid, rule in get_rules(media_type).items():
            if not rule.get("auto_request_trending"):
                continue
            gen = _genre_candidates(media_type, int(gid), rule, media_bl, person_bl, max_pages)
            streams.append([media_type, int(gid), gen, 0])

    if not streams:
        log.info("Auto-approve: no genre has 'Auto-fill trending' enabled on either the "
                 "Movies or Shows tab; nothing to fill")
        return 0, 0

    log.info("Auto-approve: round-robin fill across %d genre(s), total cap=%s, series cap=%s",
             len(streams), total_cap if total_cap is not None else "off",
             series_subcap if series_subcap is not None else "off")

    movies_added = series_added = 0
    total = 0
    progressed = True
    while progressed and (total_cap is None or total < total_cap):
        progressed = False
        for s in streams:
            if total_cap is not None and total >= total_cap:
                break
            media_type, genre_id, gen, qc = s
            if qc >= per_genre_limit:
                continue
            is_movie = media_type == "movie"
            if not is_movie and series_subcap is not None and series_added >= series_subcap:
                continue
            seen = seen_movies if is_movie else seen_series
            queue_fn = _queue_movie if is_movie else _queue_series
            # Pull from this genre until one title is actually queued (a False
            # result means already-have or no cached release  -  keep pulling),
            # or the genre's candidate stream runs dry.
            for item in gen:
                if queue_fn(item, seen):
                    s[3] += 1
                    total += 1
                    progressed = True
                    if is_movie:
                        movies_added += 1
                    else:
                        series_added += 1
                    break

    log.info("Auto-approve fill done: %d movie(s) + %d series queued (%d total)",
             movies_added, series_added, total)
    return movies_added, series_added


def run(total_limit: int | None = None, tv_limit: int | None = None) -> int:
    """Scheduled job: for every genre with auto_request_trending enabled (across
    BOTH the Movies and Shows tabs), fetch the most popular items in that
    genre/year window and queue the ones we don't have yet - this is what
    auto-fills the library. Also queues recent work for any favorited actor.

    `total_limit` is the single shared daily budget of new titles (movies + series
    combined), defaulting to AUTO_APPROVE_DAILY_LIMIT_MOVIE; `tv_limit` optionally
    caps how many of those may be series (default AUTO_APPROVE_DAILY_LIMIT_TV; set
    it >= total_limit for no practical series sub-limit). Genres are filled
    round-robin so all of them are represented at once instead of the first couple
    draining the budget. Already-requested movies and monitored series are skipped,
    so nothing is requested twice and skips don't count against the budget."""
    if total_limit is None:
        total_limit = _settings.get("AUTO_APPROVE_DAILY_LIMIT_MOVIE", AUTO_APPROVE_DAILY_LIMIT_MOVIE)
    if tv_limit is None:
        tv_limit = _settings.get("AUTO_APPROVE_DAILY_LIMIT_TV", AUTO_APPROVE_DAILY_LIMIT_TV)
    total_cap = total_limit if total_limit and total_limit > 0 else None
    series_subcap = tv_limit if tv_limit and tv_limit > 0 else None

    seen_movies = {r["imdb_id"] for r in db.get_recent(2000) if r.get("media_type") == "movie"}
    seen_series = {s["imdb_id"] for s in db.get_all_monitored_series()}
    movie_bl = db.get_content_blacklist_ids("movie")
    tv_bl = db.get_content_blacklist_ids("tv")
    person_bl = db.get_content_blacklist_ids("person")

    movies_added, series_added = _fill_round_robin(
        total_cap, series_subcap, seen_movies, seen_series, movie_bl, tv_bl, person_bl)

    total_remaining = None if total_cap is None else max(total_cap - movies_added - series_added, 0)
    if total_remaining is None or total_remaining > 0:
        tv_remaining = total_remaining if series_subcap is None else (
            None if total_remaining is None else min(total_remaining, max(series_subcap - series_added, 0)))
        actor_movies, actor_series = _run_favorite_actors(
            seen_movies, seen_series, movie_bl, tv_bl, total_remaining, tv_remaining)
        movies_added += actor_movies
        series_added += actor_series

    total = movies_added + series_added
    log.info("Auto-approve run complete: %d movie(s) + %d series = %d queued (total cap=%s)",
             movies_added, series_added, total,
             total_cap if total_cap is not None else "off")
    return total
