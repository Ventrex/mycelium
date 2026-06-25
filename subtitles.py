"""OpenSubtitles .srt fetch for newly created .strm files.

Best-effort: needs OPENSUBTITLES_API_KEY in .env. Free tier allows 5
downloads/day per API key, paid tier higher. Skips silently if not configured.

API docs: https://opensubtitles.stoplight.io/docs/opensubtitles-api/
"""
import logging
from pathlib import Path

import requests

import settings as _settings
from config import OPENSUBTITLES_USER_AGENT

log = logging.getLogger(__name__)
_BASE = "https://api.opensubtitles.com/api/v1"


def _api_key() -> str:
    return _settings.get("OPENSUBTITLES_API_KEY", "")


def _languages() -> list[str]:
    raw = _settings.get("OPENSUBTITLES_LANGUAGES", "")
    if isinstance(raw, list):
        return [l.strip().lower() for l in raw if l.strip()]
    return [l.strip().lower() for l in (raw or "").split(",") if l.strip()]


def _headers() -> dict:
    return {
        "Api-Key": _api_key(),
        "User-Agent": OPENSUBTITLES_USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _search(imdb_id: str | None, season: int | None, episode: int | None,
            language: str, title: str | None = None, verbose: bool = False) -> list[dict]:
    params = {"languages": language}
    if imdb_id:
        # OS expects numeric imdb id (no "tt" prefix)
        params["imdb_id"] = imdb_id.lstrip("t")
    elif title:
        params["query"] = title
    else:
        return []
    if season is not None:
        params["season_number"] = season
    if episode is not None:
        params["episode_number"] = episode
    try:
        r = requests.get(f"{_BASE}/subtitles", headers=_headers(), params=params, timeout=10)
        r.raise_for_status()
        return (r.json() or {}).get("data") or []
    except Exception as exc:
        (log.warning if verbose else log.debug)("OpenSubtitles search failed: %s", exc)
        return []


def _request_download_url(file_id: int) -> str | None:
    try:
        r = requests.post(
            f"{_BASE}/download",
            headers=_headers(),
            json={"file_id": file_id},
            timeout=10,
        )
        r.raise_for_status()
        return (r.json() or {}).get("link")
    except requests.exceptions.HTTPError as exc:
        # OpenSubtitles puts the real reason (e.g. quota exceeded) in the
        # response body; the generic exception string only has the status code.
        detail = ""
        if exc.response is not None:
            try:
                detail = (exc.response.json() or {}).get("message", "")
            except ValueError:
                detail = exc.response.text[:200]
        log.warning("OpenSubtitles download request failed (file_id=%s): %s%s",
                    file_id, exc, f" -- {detail}" if detail else "")
        return None
    except Exception as exc:
        log.warning("OpenSubtitles download request failed (file_id=%s): %s", file_id, exc)
        return None


def fetch_for(strm_path: Path, imdb_id: str | None, media_type: str,
              season: int | None = None, episode: int | None = None,
              title: str | None = None, verbose: bool = False) -> int:
    """Download configured-language subtitles next to a .strm file.
    Returns count of files written. Tries the imdb_id first; if that finds
    nothing and a title is given, retries with a title/query search, since
    not every release is linked to an imdb_id in OpenSubtitles' database.
    With verbose=True (used by the manual "Search" action), logs the reason
    when a language yields nothing, so failures are visible in the Logs tab
    instead of swallowed silently."""
    api_key = _api_key()
    languages = _languages()
    if not api_key:
        if verbose:
            log.warning("OpenSubtitles: no OPENSUBTITLES_API_KEY configured, skipping")
        return 0
    if not languages:
        if verbose:
            log.warning("OpenSubtitles: no OPENSUBTITLES_LANGUAGES configured, skipping")
        return 0
    written = 0
    for lang in languages:
        target = strm_path.with_suffix(f".{lang}.srt")
        if target.exists():
            continue
        results = _search(imdb_id, season, episode, lang, verbose=verbose) if imdb_id else []
        if not results and title:
            results = _search(None, season, episode, lang, title=title, verbose=verbose)
        if not results:
            if verbose:
                log.info("OpenSubtitles: no results for %s (imdb=%s, title=%r, lang=%s)",
                          strm_path.name, imdb_id or "none", title or "none", lang)
            continue
        # Pick most-downloaded file from top result
        top = results[0]
        files = (top.get("attributes") or {}).get("files") or []
        if not files:
            continue
        file_id = files[0].get("file_id")
        if not file_id:
            continue
        url = _request_download_url(file_id)
        if not url:
            continue
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            target.write_bytes(r.content)
            log.info("Subtitle saved: %s (%d bytes)", target.name, len(r.content))
            written += 1
        except Exception as exc:
            log.warning("Subtitle download failed: %s", exc)
    return written
