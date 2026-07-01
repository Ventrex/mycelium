import logging

from torrentio import TorrentioStream, _looks_like_season_pack, _QUALITY_PATTERNS
import zilean_index

log = logging.getLogger(__name__)

_BYTES_PER_GB = 1024 ** 3


def _resolve_title(imdb_id: str) -> str | None:
    """Titles are almost always already known locally (every caller has
    already registered a request or monitored series for this imdb_id
    before searching), so this only reaches TMDB on a cold cache miss."""
    import db
    req = db.get_request_by_imdb(imdb_id)
    if req and req.get("title"):
        return req["title"]
    series = db.get_monitored_series_by_imdb(imdb_id)
    if series and series.get("title"):
        return series["title"]
    import tmdb
    return tmdb.resolve_title(imdb_id)


def _classify_quality(raw_title: str) -> str:
    for label, pattern in _QUALITY_PATTERNS.items():
        if pattern.search(raw_title):
            return label
    return "unknown"


def _to_stream(entry: dict, season: int | None) -> TorrentioStream:
    raw_title = entry["raw_title"]
    return TorrentioStream(
        name=raw_title,
        title=raw_title,
        info_hash=entry["info_hash"],
        quality=_classify_quality(raw_title),
        seeders=0,
        size_gb=round(entry.get("size_bytes", 0) / _BYTES_PER_GB, 2),
        is_season_pack=_looks_like_season_pack(raw_title, season),
        source="zilean",
    )


def fetch_streams(
    imdb_id: str,
    title: str | None = None,
    season: int | None = None,
    episode: int | None = None,
) -> list[TorrentioStream]:
    """Search the native DMM hash index (see zilean_index.py). `title` can be
    passed explicitly by callers that already have it; otherwise it's
    resolved from the local requests/monitored_series tables (or TMDB)."""
    resolved_title = title or _resolve_title(imdb_id)
    if not resolved_title:
        log.debug("Zilean: no title known for %s, skipping search", imdb_id)
        return []
    entries = zilean_index.search(resolved_title, season=season, episode=episode)
    streams = [_to_stream(e, season) for e in entries]
    log.info("Zilean (native index) returned %d result(s) for %r", len(streams), resolved_title)
    return streams
