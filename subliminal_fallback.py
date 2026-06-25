"""Multi-provider .srt fallback via the `subliminal` library - free, no API key.

Tried when OpenSubtitles has no result for a language (Podnapisi was removed,
its domain stopped resolving). Unlike srtgen, none of these providers need a
local video file: subliminal builds a Video object straight from a filename
(title/season/episode/year), the same metadata Mycelium already has, and most
of these providers search on that metadata alone.

Providers used (registered in subliminal 2.6.0, language-checked for nl/en):
- addic7ed, tvsubtitles, gestdown: episodes only
- bsplayer: episodes and movies (the only one of these four that covers movies)
LegendasTV was dropped upstream and opensubtitles/podnapisi providers are
redundant with subtitles.py's direct integration, so neither is used here.

Used the same way as podnapisi.py: best-effort, silent on any failure.
"""
import logging
from pathlib import Path

from babelfish import Language
from subliminal import Video
from subliminal.core import download_best_subtitles

import db
import settings as _settings

log = logging.getLogger(__name__)

_PROVIDERS = ["addic7ed", "tvsubtitles", "gestdown", "bsplayer"]
_PROVIDER_CONFIGS = {"addic7ed": {"allow_searches": True}, "bsplayer": {"timeout": 5}}

# bsplayer logs a full traceback at ERROR level on every retry against an
# unreachable mirror (5 retries per video by default); _download() below
# already turns that into one clean warning/debug line, so silence the
# library's own logger to keep it out of the admin Logs tab.
logging.getLogger("subliminal.providers.bsplayer").setLevel(logging.CRITICAL)


class _BSPlayerNoiseFilter(logging.Filter):
    """subliminal.utils.handle_exception() logs uncaught provider errors
    generically (e.g. "Unexpected error. Provider bsplayer") regardless of
    which provider raised them. Drop only the bsplayer ones here so failures
    from the other providers stay visible in the admin Logs tab."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "bsplayer" not in record.getMessage().lower()


logging.getLogger("subliminal.utils").addFilter(_BSPlayerNoiseFilter())


def _enabled() -> bool:
    return bool(_settings.get("SUBLIMINAL_ENABLED", True))


def _languages() -> list[str]:
    raw = _settings.get("OPENSUBTITLES_LANGUAGES", "")
    if isinstance(raw, list):
        return [l.strip().lower() for l in raw if l.strip()]
    return [l.strip().lower() for l in (raw or "").split(",") if l.strip()]


def title_for_imdb(imdb_id: str) -> str | None:
    """Best-effort title lookup for callers that only have an imdb_id - subliminal
    builds videos from a name, not an imdb_id."""
    req = db.get_request_by_imdb(imdb_id)
    if req and req.get("title"):
        return req["title"]
    series = db.get_monitored_series_by_imdb(imdb_id)
    if series and series.get("title"):
        return series["title"]
    return None


def _build_video(title: str, media_type: str, season: int | None, episode: int | None,
                  year: int | None) -> Video:
    if media_type == "series" and season is not None and episode is not None:
        name = f"{title} S{season:02d}E{episode:02d}"
    else:
        name = f"{title} ({year})" if year else title
    return Video.fromname(name)


def _download(title: str, media_type: str, season: int | None, episode: int | None,
              year: int | None, langs: set[str], verbose: bool = False) -> dict[str, bytes]:
    video = _build_video(title, media_type, season, episode, year)
    languages = {Language.fromalpha2(l) for l in langs}
    try:
        results = download_best_subtitles(
            {video}, languages, providers=_PROVIDERS, provider_configs=_PROVIDER_CONFIGS,
        )
    except Exception as exc:
        (log.warning if verbose else log.debug)("subliminal search failed for %r: %s", title, exc)
        return {}
    found: dict[str, bytes] = {}
    for subtitle in results.get(video, []):
        if not subtitle.content:
            continue
        found.setdefault(str(subtitle.language.alpha2), subtitle.content)
    return found


def fetch_for(strm_path: Path, title: str, media_type: str,
              season: int | None = None, episode: int | None = None,
              year: int | None = None, verbose: bool = False) -> int:
    """Download configured-language subtitles next to a .strm file via subliminal's
    provider pool. Returns count of files written. With verbose=True (used by the
    manual "Search" action), logs the reason when a language yields nothing."""
    if not _enabled():
        if verbose:
            log.info("subliminal: disabled, skipping")
        return 0
    if not title:
        if verbose:
            log.warning("subliminal: no title available, skipping")
        return 0
    languages = _languages()
    if not languages:
        if verbose:
            log.warning("subliminal: no OPENSUBTITLES_LANGUAGES configured, skipping")
        return 0
    missing = [l for l in languages if not strm_path.with_suffix(f".{l}.srt").exists()]
    if not missing:
        return 0
    content_by_lang = _download(title, media_type, season, episode, year, set(missing), verbose=verbose)
    written = 0
    for lang in missing:
        content = content_by_lang.get(lang)
        if not content:
            if verbose:
                log.info("subliminal: no results for %r (lang=%s)", title, lang)
            continue
        target = strm_path.with_suffix(f".{lang}.srt")
        try:
            target.write_bytes(content)
            log.info("subliminal subtitle saved: %s (%d bytes)", target.name, len(content))
            written += 1
        except Exception as exc:
            log.warning("subliminal subtitle write failed: %s", exc)
    return written


def fetch_content(title: str, media_type: str, season: int | None, episode: int | None,
                   year: int | None, lang: str) -> bytes | None:
    """Single-language raw subtitle bytes, for callers (like web_player.py) that
    convert straight to .vtt instead of writing a .srt file next to a .strm."""
    return _download(title, media_type, season, episode, year, {lang}).get(lang)
