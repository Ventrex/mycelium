import logging

import requests as req_lib

log = logging.getLogger(__name__)

_BASE = "https://api.themoviedb.org/3"


def _api_key() -> str:
    """Read the key from the runtime settings overlay (DB override, then
    .env) so changes in the Settings UI take effect without a restart."""
    import settings
    return (settings.get("TMDB_API_KEY", "") or "").strip()


def _headers() -> dict:
    return {"Authorization": f"Bearer {_api_key()}", "Accept": "application/json"}


def _get(path: str, params: dict | None = None, timeout: int = 10) -> dict | None:
    if not _api_key():
        log.warning("TMDB_API_KEY not set; skipping %s", path)
        return None
    try:
        resp = req_lib.get(f"{_BASE}{path}", headers=_headers(), params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json() or {}
    except req_lib.RequestException as exc:
        log.warning("TMDB request failed for %s: %s", path, exc)
        return None


def tmdb_to_imdb(tmdb_id: int | str, media_type: str = "movie") -> str | None:
    kind = "movie" if media_type == "movie" else "tv"
    data = _get(f"/{kind}/{tmdb_id}/external_ids")
    if not data:
        return None
    imdb_id = data.get("imdb_id") or None
    if imdb_id:
        log.info("TMDB resolved %s/%s → %s", kind, tmdb_id, imdb_id)
    else:
        log.warning("TMDB returned no imdb_id for %s/%s", kind, tmdb_id)
    return imdb_id


def find_by_imdb(imdb_id: str, kind: str = "tv") -> int | None:
    """Reverse-lookup: IMDB ID → TMDB ID using the /find endpoint."""
    data = _get(f"/find/{imdb_id}", params={"external_source": "imdb_id"})
    if not data:
        return None
    results = data.get("tv_results" if kind == "tv" else "movie_results") or []
    if results:
        tmdb_id = results[0].get("id")
        log.info("TMDB find %s → tmdb_id=%s", imdb_id, tmdb_id)
        return tmdb_id
    return None


def resolve_title(imdb_id: str) -> str | None:
    """Best-effort title lookup for an IMDb ID, checking movie then tv results."""
    data = _get(f"/find/{imdb_id}", params={"external_source": "imdb_id"})
    if not data:
        return None
    for key in ("movie_results", "tv_results"):
        results = data.get(key) or []
        if results:
            return results[0].get("title") or results[0].get("name")
    return None


def get_show_info(tmdb_id: int) -> dict | None:
    """Return top-level show info including number_of_seasons."""
    return _get(f"/tv/{tmdb_id}")


def release_date(imdb_id: str | None = None, tmdb_id: int | None = None,
                 media_type: str = "movie") -> str | None:
    """Return the YYYY-MM-DD theatrical/first-air date for a title, or None if
    unknown. Prefers a direct tmdb_id lookup; falls back to /find by imdb_id."""
    if media_type == "movie":
        if tmdb_id:
            data = _get(f"/movie/{tmdb_id}")
            if data:
                return data.get("release_date") or None
        if imdb_id:
            data = _get(f"/find/{imdb_id}", params={"external_source": "imdb_id"})
            results = (data or {}).get("movie_results") or []
            if results:
                return results[0].get("release_date") or None
    else:
        if tmdb_id:
            data = _get(f"/tv/{tmdb_id}")
            if data:
                return data.get("first_air_date") or None
        if imdb_id:
            data = _get(f"/find/{imdb_id}", params={"external_source": "imdb_id"})
            results = (data or {}).get("tv_results") or []
            if results:
                return results[0].get("first_air_date") or None
    return None


def get_season_episodes(tmdb_id: int, season: int) -> list[dict]:
    """Return episode list for a season; each dict has episode_number and air_date."""
    data = _get(f"/tv/{tmdb_id}/season/{season}")
    if not data:
        return []
    return data.get("episodes") or []


def get_poster_path(imdb_id: str, media_type: str = "movie") -> str | None:
    """Return TMDB poster_path (e.g. /abc123.jpg) for an IMDB ID, or None."""
    import db
    cached = db.get_poster(imdb_id)
    if cached is not None:
        return cached or None
    data = _get(f"/find/{imdb_id}", params={"external_source": "imdb_id"})
    if not data:
        return None
    key = "movie_results" if media_type == "movie" else "tv_results"
    results = data.get(key) or data.get("tv_results") or data.get("movie_results") or []
    poster = results[0].get("poster_path") if results else None
    db.set_poster(imdb_id, poster or "")
    return poster


def get_images(imdb_id: str, media_type: str = "movie") -> tuple[str | None, str | None]:
    """Return (poster_path, backdrop_path) for an IMDb ID via TMDB /find."""
    data = _get(f"/find/{imdb_id}", params={"external_source": "imdb_id"})
    if not data:
        return None, None
    key = "movie_results" if media_type == "movie" else "tv_results"
    results = data.get(key) or data.get("tv_results") or data.get("movie_results") or []
    if not results:
        return None, None
    item = results[0]
    return item.get("poster_path"), item.get("backdrop_path")


def get_movie_runtime_sec(imdb_id: str) -> float | None:
    """Return movie runtime in seconds from TMDB, or None if unavailable."""
    data = _get(f"/find/{imdb_id}", params={"external_source": "imdb_id"})
    if not data:
        return None
    results = data.get("movie_results") or []
    if not results:
        return None
    tmdb_id = results[0].get("id")
    if not tmdb_id:
        return None
    detail = _get(f"/movie/{tmdb_id}")
    if not detail:
        return None
    minutes = detail.get("runtime")
    return float(minutes) * 60.0 if minutes else None


def get_episode_runtime_sec(imdb_id: str, season: int, episode: int) -> float | None:
    """Return episode runtime in seconds from TMDB, or None if unavailable."""
    data = _get(f"/find/{imdb_id}", params={"external_source": "imdb_id"})
    if not data:
        return None
    results = data.get("tv_results") or []
    if not results:
        return None
    tmdb_id = results[0].get("id")
    if not tmdb_id:
        return None
    ep_data = _get(f"/tv/{tmdb_id}/season/{season}/episode/{episode}")
    if not ep_data:
        return None
    minutes = ep_data.get("runtime")
    return float(minutes) * 60.0 if minutes else None


def get_episode_still(tmdb_id: int, season: int, episode: int) -> str | None:
    """Return still_path for a TV episode, or None."""
    data = _get(f"/tv/{tmdb_id}/season/{season}/episode/{episode}")
    if not data:
        return None
    return data.get("still_path")


def search_movie(title: str, year: int | None = None) -> str | None:
    """Search TMDB for a movie by title; return IMDB ID or None."""
    params: dict = {"query": title}
    if year:
        params["year"] = year
    data = _get("/search/movie", params=params)
    if not data:
        return None
    results = data.get("results") or []
    if not results:
        log.warning("TMDB search_movie: no results for %r (year=%s)", title, year)
        return None
    tmdb_id = results[0]["id"]
    return tmdb_to_imdb(tmdb_id, media_type="movie")


def search_tv(title: str) -> str | None:
    """Search TMDB for a TV show by title; return IMDB ID or None."""
    data = _get("/search/tv", params={"query": title})
    if not data:
        return None
    results = data.get("results") or []
    if not results:
        log.warning("TMDB search_tv: no results for %r", title)
        return None
    tmdb_id = results[0]["id"]
    return tmdb_to_imdb(tmdb_id, media_type="tv")


# ── Discovery / Discover ──────────────────────────────────────────────────────

def _norm_item(item: dict, media_type: str | None = None) -> dict:
    """Normalize a TMDB movie/tv result into a uniform dict for our UI."""
    mt = media_type or item.get("media_type") or ("tv" if item.get("first_air_date") else "movie")
    return {
        "tmdb_id": item.get("id"),
        "media_type": mt,
        "title": item.get("title") or item.get("name") or "",
        "original_title": item.get("original_title") or item.get("original_name") or "",
        "year": ((item.get("release_date") or item.get("first_air_date") or "")[:4]) or None,
        "release_date": item.get("release_date") or item.get("first_air_date") or "",
        "rating": round(float(item.get("vote_average") or 0), 1),
        "votes": item.get("vote_count") or 0,
        "popularity": item.get("popularity") or 0,
        "overview": item.get("overview") or "",
        "poster_path": item.get("poster_path"),
        "backdrop_path": item.get("backdrop_path"),
        "genre_ids": item.get("genre_ids") or [],
        "original_language": item.get("original_language") or "",
    }


def multi_search(query: str, page: int = 1) -> list[dict]:
    """Multi-search across movies + TV. Returns normalized list."""
    if not query.strip():
        return []
    data = _get("/search/multi", params={"query": query, "page": page, "include_adult": "false"})
    if not data:
        return []
    out = []
    for item in (data.get("results") or []):
        if item.get("media_type") not in ("movie", "tv"):
            continue
        out.append(_norm_item(item))
    return out


def trending(media_type: str = "all", window: str = "week", page: int = 1) -> list[dict]:
    """media_type: all | movie | tv ; window: day | week"""
    data = _get(f"/trending/{media_type}/{window}", params={"page": page})
    if not data:
        return []
    return [_norm_item(i) for i in (data.get("results") or [])]


def popular(media_type: str = "movie", page: int = 1, region: str | None = None) -> list[dict]:
    params: dict = {"page": page}
    if region:
        params["region"] = region
    data = _get(f"/{media_type}/popular", params=params)
    if not data:
        return []
    return [_norm_item(i, media_type=media_type) for i in (data.get("results") or [])]


def top_rated(media_type: str = "movie", page: int = 1) -> list[dict]:
    data = _get(f"/{media_type}/top_rated", params={"page": page})
    if not data:
        return []
    return [_norm_item(i, media_type=media_type) for i in (data.get("results") or [])]


def now_playing(page: int = 1, region: str | None = None) -> list[dict]:
    params: dict = {"page": page}
    if region:
        params["region"] = region
    data = _get("/movie/now_playing", params=params)
    if not data:
        return []
    return [_norm_item(i, media_type="movie") for i in (data.get("results") or [])]


def upcoming(page: int = 1, region: str | None = None) -> list[dict]:
    params: dict = {"page": page}
    if region:
        params["region"] = region
    data = _get("/movie/upcoming", params=params)
    if not data:
        return []
    return [_norm_item(i, media_type="movie") for i in (data.get("results") or [])]


def on_the_air(page: int = 1) -> list[dict]:
    """Currently airing TV shows."""
    data = _get("/tv/on_the_air", params={"page": page})
    if not data:
        return []
    return [_norm_item(i, media_type="tv") for i in (data.get("results") or [])]


def discover_by_provider(media_type: str, provider_id: int, region: str = "NL",
                          page: int = 1, sort_by: str = "popularity.desc") -> list[dict]:
    """Discover content available on a specific streaming provider in a region."""
    params = {
        "watch_region": region,
        "with_watch_providers": provider_id,
        "with_watch_monetization_types": "flatrate",
        "sort_by": sort_by,
        "page": page,
        "include_adult": "false",
    }
    data = _get(f"/discover/{media_type}", params=params)
    if not data:
        return []
    return [_norm_item(i, media_type=media_type) for i in (data.get("results") or [])]


def list_providers(media_type: str = "movie", region: str = "NL") -> list[dict]:
    """List streaming providers available in a region."""
    data = _get(f"/watch/providers/{media_type}", params={"watch_region": region})
    if not data:
        return []
    out = []
    for p in (data.get("results") or []):
        out.append({
            "id": p.get("provider_id"),
            "name": p.get("provider_name"),
            "logo_path": p.get("logo_path"),
            "priority": p.get("display_priorities", {}).get(region, 999),
        })
    out.sort(key=lambda x: x["priority"])
    return out


def watch_providers_for(tmdb_id: int, media_type: str = "movie", region: str = "NL") -> dict:
    """Return where a specific title streams in a region."""
    kind = "movie" if media_type == "movie" else "tv"
    data = _get(f"/{kind}/{tmdb_id}/watch/providers")
    if not data:
        return {}
    by_region = (data.get("results") or {}).get(region) or {}
    def _names(key):
        return [{"id": x.get("provider_id"), "name": x.get("provider_name"),
                 "logo_path": x.get("logo_path")} for x in (by_region.get(key) or [])]
    return {
        "flatrate": _names("flatrate"),
        "rent": _names("rent"),
        "buy": _names("buy"),
        "link": by_region.get("link"),
    }


def details(media_type: str, tmdb_id: int, region: str = "NL") -> dict | None:
    """Full detail page payload: metadata, credits, videos, providers, external IDs."""
    kind = "movie" if media_type == "movie" else "tv"
    data = _get(f"/{kind}/{tmdb_id}",
                 params={"append_to_response": "credits,videos,external_ids,watch/providers,recommendations,similar"})
    if not data:
        return None
    item = _norm_item(data, media_type=media_type)
    item["imdb_id"] = (data.get("external_ids") or {}).get("imdb_id") or data.get("imdb_id")
    item["runtime"] = data.get("runtime") or (data.get("episode_run_time") or [None])[0]
    item["genres"] = [g.get("name") for g in (data.get("genres") or [])]
    item["genre_ids"] = [g.get("id") for g in (data.get("genres") or [])]
    item["tagline"] = data.get("tagline") or ""
    item["status"] = data.get("status") or ""
    item["homepage"] = data.get("homepage") or ""
    if media_type == "tv":
        item["seasons"] = [
            {"season_number": s.get("season_number"),
             "episode_count": s.get("episode_count"),
             "name": s.get("name"),
             "poster_path": s.get("poster_path"),
             "air_date": s.get("air_date")}
            for s in (data.get("seasons") or []) if s.get("season_number", 0) >= 0
        ]
        item["number_of_seasons"] = data.get("number_of_seasons")
        item["number_of_episodes"] = data.get("number_of_episodes")
    cast = ((data.get("credits") or {}).get("cast") or [])[:12]
    item["cast"] = [{"id": c.get("id"), "name": c.get("name"), "character": c.get("character"),
                     "profile_path": c.get("profile_path")} for c in cast]
    item["crew"] = _key_creators(data)[:8]
    videos = ((data.get("videos") or {}).get("results") or [])
    item["trailers"] = [{"key": v.get("key"), "name": v.get("name"), "site": v.get("site")}
                         for v in videos if v.get("type") == "Trailer" and v.get("site") == "YouTube"][:3]
    providers_payload = (data.get("watch/providers") or {}).get("results") or {}
    region_p = providers_payload.get(region) or {}
    item["providers"] = {
        "flatrate": [{"id": x.get("provider_id"), "name": x.get("provider_name"),
                      "logo_path": x.get("logo_path")} for x in (region_p.get("flatrate") or [])],
        "link": region_p.get("link"),
    }
    item["recommendations"] = [_norm_item(r, media_type=media_type)
                                for r in (data.get("recommendations") or {}).get("results", [])[:12]]
    if media_type == "movie":
        collection = data.get("belongs_to_collection")
        item["collection"] = ({"id": collection.get("id"), "name": collection.get("name"),
                                "poster_path": collection.get("poster_path"),
                                "backdrop_path": collection.get("backdrop_path")}
                               if collection else None)
    return item


# ── Genres / Discover-by-genre ────────────────────────────────────────────────

def genres(media_type: str = "movie") -> list[dict]:
    """Return [{id, name}] for movie or tv genres. Cached 24h in settings table."""
    import json as _json
    import time as _time
    import db
    cache_key = f"_tmdb_genre_cache_{media_type}"
    cached = db.get_setting(cache_key)
    if cached:
        try:
            payload = _json.loads(cached)
            cached_genres = payload.get("genres") or []
            if cached_genres and _time.time() - payload.get("ts", 0) < 86400:
                return cached_genres
        except (ValueError, TypeError):
            pass
    data = _get(f"/genre/{media_type}/list")
    if data is None:
        return []
    result = data.get("genres") or []
    if result:
        db.set_setting(cache_key, _json.dumps({"ts": _time.time(), "genres": result}))
    return result


def languages() -> list[dict]:
    """Return [{iso_639_1, english_name, name}] for all TMDB-known languages.
    Cached 7 days in the settings table since this list barely ever changes."""
    import json as _json
    import time as _time
    import db
    cache_key = "_tmdb_language_cache"
    cached = db.get_setting(cache_key)
    if cached:
        try:
            payload = _json.loads(cached)
            cached_langs = payload.get("languages") or []
            if cached_langs and _time.time() - payload.get("ts", 0) < 604800:
                return cached_langs
        except (ValueError, TypeError):
            pass
    data = _get("/configuration/languages")
    if not data:
        return []
    result = sorted(
        [{"iso_639_1": l.get("iso_639_1"), "english_name": l.get("english_name"), "name": l.get("name")}
         for l in data if l.get("iso_639_1")],
        key=lambda l: l["english_name"] or "",
    )
    if result:
        db.set_setting(cache_key, _json.dumps({"ts": _time.time(), "languages": result}))
    return result


def discover_by_genre(media_type: str, genre_id: int, year_from: int | None = None,
                       year_to: int | None = None, page: int = 1, region: str = "NL",
                       sort_by: str = "popularity.desc") -> list[dict]:
    """Discover movies/tv for a single genre, optionally bounded by release-year range."""
    date_field = "primary_release_date" if media_type == "movie" else "first_air_date"
    params: dict = {
        "with_genres": genre_id,
        "sort_by": sort_by,
        "page": page,
        "include_adult": "false",
        "watch_region": region,
    }
    if year_from:
        params[f"{date_field}.gte"] = f"{year_from}-01-01"
    if year_to:
        params[f"{date_field}.lte"] = f"{year_to}-12-31"
    data = _get(f"/discover/{media_type}", params=params)
    if not data:
        return []
    return [_norm_item(i, media_type=media_type) for i in (data.get("results") or [])]


def search_keyword(query: str) -> int | None:
    """Resolve a free-text keyword (e.g. 'christmas') to its TMDB keyword ID.
    Cached for a week in the settings table since these IDs never change."""
    import json as _json
    import time as _time
    import db
    cache_key = f"_tmdb_keyword_cache_{query}"
    cached = db.get_setting(cache_key)
    if cached:
        try:
            payload = _json.loads(cached)
            if payload.get("id") and _time.time() - payload.get("ts", 0) < 604800:
                return payload["id"]
        except (ValueError, TypeError):
            pass
    data = _get("/search/keyword", params={"query": query})
    if not data:
        return None
    results = data.get("results") or []
    if not results:
        return None
    keyword_id = results[0].get("id")
    db.set_setting(cache_key, _json.dumps({"ts": _time.time(), "id": keyword_id}))
    return keyword_id


def discover_by_keyword(media_type: str, keyword_id: int, page: int = 1, region: str = "NL",
                         sort_by: str = "popularity.desc") -> list[dict]:
    """Discover movies/tv tagged with a specific TMDB keyword (e.g. holiday themes)."""
    params = {
        "with_keywords": keyword_id,
        "sort_by": sort_by,
        "page": page,
        "include_adult": "false",
        "watch_region": region,
    }
    data = _get(f"/discover/{media_type}", params=params)
    if not data:
        return []
    return [_norm_item(i, media_type=media_type) for i in (data.get("results") or [])]


def credits_person_ids(media_type: str, tmdb_id: int) -> list[int]:
    """Lightweight cast lookup: TMDB person IDs credited on a movie/tv item."""
    kind = "movie" if media_type == "movie" else "tv"
    data = _get(f"/{kind}/{tmdb_id}/credits")
    if not data:
        return []
    return [c["id"] for c in (data.get("cast") or []) if c.get("id")]


# ── Person search ─────────────────────────────────────────────────────────────

def search_person(query: str, page: int = 1) -> list[dict]:
    """Search TMDB for people (actors/actresses). Returns normalized person dicts."""
    if not query.strip():
        return []
    data = _get("/search/person", params={"query": query, "page": page, "include_adult": "false"})
    if not data:
        return []
    out = []
    for p in (data.get("results") or []):
        out.append({
            "tmdb_id": p.get("id"),
            "media_type": "person",
            "name": p.get("name"),
            "profile_path": p.get("profile_path"),
            "known_for_department": p.get("known_for_department"),
            "popularity": p.get("popularity") or 0,
            "known_for": [_norm_item(k) for k in (p.get("known_for") or [])
                          if k.get("media_type") in ("movie", "tv")],
        })
    return out


def person_details(person_id: int) -> dict | None:
    """Person bio + filmography (combined movie/tv credits as cast)."""
    data = _get(f"/person/{person_id}", params={"append_to_response": "combined_credits"})
    if not data:
        return None
    credits = ((data.get("combined_credits") or {}).get("cast")) or []
    seen: set[tuple[str, int]] = set()
    filmography = []
    for c in credits:
        mt = c.get("media_type")
        if mt not in ("movie", "tv"):
            continue
        key = (mt, c.get("id"))
        if key in seen:
            continue
        seen.add(key)
        item = _norm_item(c, media_type=mt)
        item["character"] = c.get("character") or ""
        filmography.append(item)
    filmography.sort(key=lambda x: x.get("year") or "0000", reverse=True)
    return {
        "tmdb_id": data.get("id"),
        "name": data.get("name"),
        "biography": data.get("biography") or "",
        "profile_path": data.get("profile_path"),
        "birthday": data.get("birthday"),
        "place_of_birth": data.get("place_of_birth"),
        "known_for_department": data.get("known_for_department"),
        "filmography": filmography,
    }


# ── Collections ────────────────────────────────────────────────────────────────

def collection_details(collection_id: int) -> dict | None:
    """Movie collection (e.g. a trilogy): metadata + member movies."""
    data = _get(f"/collection/{collection_id}")
    if not data:
        return None
    parts = [_norm_item(p, media_type="movie") for p in (data.get("parts") or [])]
    parts.sort(key=lambda x: x.get("year") or "0000")
    return {
        "tmdb_id": data.get("id"),
        "name": data.get("name"),
        "overview": data.get("overview") or "",
        "poster_path": data.get("poster_path"),
        "backdrop_path": data.get("backdrop_path"),
        "parts": parts,
    }


def movie_collection_id(tmdb_id: int) -> int | None:
    """The TMDB collection id a movie belongs to (e.g. Toy Story), or None."""
    data = _get(f"/movie/{tmdb_id}")
    coll = (data or {}).get("belongs_to_collection")
    return coll.get("id") if isinstance(coll, dict) and coll.get("id") else None


# Crew jobs that define an author of a title (so "from the same creators" means
# the same writer/showrunner/director, not the camera operator).
_CREATOR_JOBS = ("Creator", "Writer", "Screenplay", "Story", "Director", "Executive Producer")
_CREATOR_JOB_ORDER = {j: i for i, j in enumerate(_CREATOR_JOBS)}


def _key_creators(data: dict) -> list[dict]:
    """Extract a title's authoring crew (TV created_by + key crew jobs),
    de-duplicated and ordered Creator > Writer > Director."""
    people: list[dict] = []
    seen: set = set()
    for cb in (data.get("created_by") or []):
        pid = cb.get("id")
        if pid and pid not in seen:
            seen.add(pid)
            people.append({"id": pid, "name": cb.get("name"), "job": "Creator",
                           "profile_path": cb.get("profile_path")})
    crew = [c for c in ((data.get("credits") or {}).get("crew") or [])
            if c.get("id") and c.get("job") in _CREATOR_JOBS]
    crew.sort(key=lambda c: _CREATOR_JOB_ORDER.get(c.get("job"), 99))
    for c in crew:
        pid = c.get("id")
        if pid not in seen:
            seen.add(pid)
            people.append({"id": pid, "name": c.get("name"), "job": c.get("job"),
                           "profile_path": c.get("profile_path")})
    return people


def by_creators(media_type: str, tmdb_id: int, limit: int = 18) -> list[dict]:
    """Other titles by the same writer/showrunner/director, of the same media
    type and with at least one overlapping genre (e.g. My Name is Earl ->
    Raising Hope via Greg Garcia). Sorted by popularity."""
    kind = "movie" if media_type == "movie" else "tv"
    base = _get(f"/{kind}/{tmdb_id}", params={"append_to_response": "credits"})
    if not base:
        return []
    base_genres = {g.get("id") for g in (base.get("genres") or [])}
    out: list[dict] = []
    seen_ids = {int(tmdb_id)}
    for person in _key_creators(base)[:3]:
        data = _get(f"/person/{person['id']}/combined_credits")
        if not data:
            continue
        for c in (data.get("crew") or []):
            if c.get("media_type") != media_type or c.get("job") not in _CREATOR_JOBS:
                continue
            cid = c.get("id")
            if not cid or cid in seen_ids:
                continue
            if base_genres and not (set(c.get("genre_ids") or []) & base_genres):
                continue
            seen_ids.add(cid)
            item = _norm_item(c, media_type=media_type)
            item["via"] = person.get("name")
            out.append(item)
    out.sort(key=lambda x: x.get("popularity") or 0, reverse=True)
    return out[:limit]


# Common Dutch / European providers  -  IDs from TMDB
NL_PROVIDERS = {
    "netflix": 8,
    "amazon_prime": 119,
    "disney_plus": 337,
    "hbo_max": 1899,
    "apple_tv_plus": 350,
    "videoland": 563,
    "npo_plus": 271,
    "skyshowtime": 1773,
}


def get_notification_details(imdb_id: str | None, media_type: str = "movie",
                             seasons: list[int] | None = None,
                             tmdb_id: int | None = None) -> dict | None:
    """Return rich metadata for notifications, resolved from an IMDb ID.

    The result is intentionally presentation-ready so notification backends can
    stay small and consistent. Missing values are omitted rather than raising.
    """
    kind = "movie" if media_type == "movie" else "tv"
    found = {}
    if not tmdb_id:
        if not imdb_id:
            return None
        data = _get(f"/find/{imdb_id}", params={"external_source": "imdb_id"})
        if not data:
            return None
        key = "movie_results" if kind == "movie" else "tv_results"
        results = data.get(key) or []
        if not results:
            return None
        found = results[0]
        tmdb_id = found.get("id")
        if not tmdb_id:
            return None

    detail = _get(f"/{kind}/{tmdb_id}", params={"append_to_response": "credits"}) or {}
    title = detail.get("title") or detail.get("name") or found.get("title") or found.get("name") or imdb_id
    date_value = (
        detail.get("release_date") or detail.get("first_air_date")
        or found.get("release_date") or found.get("first_air_date") or ""
    )
    runtime_minutes = detail.get("runtime")
    if not runtime_minutes and kind == "tv":
        runtimes = detail.get("episode_run_time") or []
        runtime_minutes = runtimes[0] if runtimes else None

    actors = []
    for cast in ((detail.get("credits") or {}).get("cast") or [])[:5]:
        name = cast.get("name")
        if name:
            actors.append(name)

    poster_path = detail.get("poster_path") or found.get("poster_path")
    season_summary = None
    if kind == "tv":
        season_numbers = [s.get("season_number") for s in (detail.get("seasons") or [])]
        season_numbers = [s for s in season_numbers if isinstance(s, int) and s > 0]
        requested = []
        for season in seasons or []:
            try:
                season_num = int(season)
            except (TypeError, ValueError):
                continue
            if season_num > 0:
                requested.append(season_num)
        requested = sorted(set(requested))
        total = detail.get("number_of_seasons") or len(season_numbers) or None
        bits = []
        if total:
            bits.append(f"{total} seizoen{'en' if total != 1 else ''}")
        if requested:
            bits.append("aangevraagd: " + ", ".join(f"S{s:02d}" for s in requested))
        elif season_numbers:
            bits.append("beschikbaar: " + ", ".join(f"S{s:02d}" for s in season_numbers[:12]))
        season_summary = " · ".join(bits) if bits else None

    return {
        "imdb_id": imdb_id or (detail.get("external_ids") or {}).get("imdb_id"),
        "tmdb_id": tmdb_id,
        "media_type": media_type,
        "title": title,
        "year": date_value[:4] or None,
        "runtime": _format_runtime(runtime_minutes),
        "actors": actors,
        "overview": detail.get("overview") or found.get("overview") or "",
        "poster_url": f"https://image.tmdb.org/t/p/w342{poster_path}" if poster_path else None,
        "season_summary": season_summary,
        "url": f"https://www.themoviedb.org/{kind}/{tmdb_id}",
    }


def _format_runtime(minutes: int | float | None) -> str | None:
    if not minutes:
        return None
    minutes = int(minutes)
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}u {mins}m"
    if hours:
        return f"{hours}u"
    return f"{mins}m"
