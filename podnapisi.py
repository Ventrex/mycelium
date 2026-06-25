"""Podnapisi.net .srt fetch - free, no API key, fallback/alternative to OpenSubtitles.

Podnapisi needs no account, key, or daily quota. Its server still negotiates an
older DH cipher that OpenSSL 3's default security level (SECLEVEL=2) rejects,
so the session below explicitly relaxes that for this host only.

Search is keyword-based (no imdb_id lookup), so callers need a title. Used
the same way as subtitles.py: best-effort, silent on any failure.
"""
import io
import logging
import ssl
from pathlib import Path
from zipfile import ZipFile

import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

import db
import settings as _settings

log = logging.getLogger(__name__)
_BASE = "https://www.podnapisi.net/subtitles"
_SUB_EXTS = (".srt", ".ass", ".ssa", ".sub")


class _SecLevel1Adapter(HTTPAdapter):
    """Podnapisi's TLS setup needs SECLEVEL=1; everything else keeps defaults."""

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx,
        )


def _session() -> requests.Session:
    s = requests.Session()
    s.mount("https://www.podnapisi.net", _SecLevel1Adapter())
    s.headers.update({
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; Mycelium subtitle fetch)",
    })
    return s


def _enabled() -> bool:
    return bool(_settings.get("PODNAPISI_ENABLED", True))


def _languages() -> list[str]:
    raw = _settings.get("OPENSUBTITLES_LANGUAGES", "")
    if isinstance(raw, list):
        return [l.strip().lower() for l in raw if l.strip()]
    return [l.strip().lower() for l in (raw or "").split(",") if l.strip()]


def _search(title: str, season: int | None, episode: int | None,
            language: str, year: int | None = None, verbose: bool = False) -> list[dict]:
    params: dict = {"keywords": title, "language": language}
    if season is not None and episode is not None:
        params["seasons"] = season
        params["episodes"] = episode
        params["movie_type"] = ["tv-series", "mini-series"]
    else:
        params["movie_type"] = "movie"
    if year:
        params["year"] = year
    try:
        r = _session().get(f"{_BASE}/search/advanced", params=params, timeout=10)
        r.raise_for_status()
        return (r.json() or {}).get("data") or []
    except Exception as exc:
        (log.warning if verbose else log.debug)("Podnapisi search failed for %r: %s", title, exc)
        return []


def _download(pid: str) -> bytes | None:
    try:
        r = _session().get(f"{_BASE}/{pid}/download", params={"container": "zip"}, timeout=20)
        r.raise_for_status()
        with ZipFile(io.BytesIO(r.content)) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(_SUB_EXTS)] or zf.namelist()
            if not names:
                return None
            return zf.read(names[0])
    except Exception as exc:
        log.warning("Podnapisi download failed (pid=%s): %s", pid, exc)
        return None


def title_for_imdb(imdb_id: str) -> str | None:
    """Best-effort title lookup for callers that only have an imdb_id - Podnapisi
    has no imdb_id search, only free-text keywords."""
    req = db.get_request_by_imdb(imdb_id)
    if req and req.get("title"):
        return req["title"]
    series = db.get_monitored_series_by_imdb(imdb_id)
    if series and series.get("title"):
        return series["title"]
    return None


def fetch_for(strm_path: Path, title: str, media_type: str,
              season: int | None = None, episode: int | None = None,
              year: int | None = None, verbose: bool = False) -> int:
    """Download configured-language subtitles next to a .strm file.
    Returns count of files written. With verbose=True (used by the manual
    "Search" action), logs the reason when a language yields nothing, so
    failures are visible in the Logs tab instead of swallowed silently."""
    if not _enabled():
        if verbose:
            log.info("Podnapisi: disabled, skipping")
        return 0
    if not title:
        if verbose:
            log.warning("Podnapisi: no title available, skipping")
        return 0
    languages = _languages()
    if not languages:
        if verbose:
            log.warning("Podnapisi: no OPENSUBTITLES_LANGUAGES configured, skipping")
        return 0
    written = 0
    for lang in languages:
        target = strm_path.with_suffix(f".{lang}.srt")
        if target.exists():
            continue
        results = _search(title, season, episode, lang, year, verbose=verbose)
        if not results:
            if verbose:
                log.info("Podnapisi: no results for %r (lang=%s)", title, lang)
            continue
        pid = results[0].get("id")
        if not pid:
            continue
        content = _download(str(pid))
        if not content:
            continue
        try:
            target.write_bytes(content)
            log.info("Podnapisi subtitle saved: %s (%d bytes)", target.name, len(content))
            written += 1
        except Exception as exc:
            log.warning("Podnapisi subtitle write failed: %s", exc)
    return written
