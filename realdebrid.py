"""RealDebrid client with same surface as torbox.py.

Provides check_cached() + add_magnet() so the multi-debrid layer can fall back
to RealDebrid when TorBox doesn't have a release cached. Disabled by default.
"""
import logging
import time

import requests

from config import (
    REALDEBRID_API_KEY,
    REALDEBRID_BASE_URL,
    TORBOX_POLL_INTERVAL_SEC,
    TORBOX_POLL_TIMEOUT_SEC,
)

log = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(REALDEBRID_API_KEY)


def _headers() -> dict:
    return {"Authorization": f"Bearer {REALDEBRID_API_KEY}"}


def check_cached(hashes: list[str], timeout: int = 15) -> set[str]:
    """Return the subset of hashes RealDebrid has cached."""
    if not is_configured() or not hashes:
        return set()
    cached: set[str] = set()
    # RD wants hashes as a / separated path; chunk to keep URLs sane
    for i in range(0, len(hashes), 25):
        chunk = hashes[i : i + 25]
        url = f"{REALDEBRID_BASE_URL.rstrip('/')}/torrents/instantAvailability/{'/'.join(chunk)}"
        try:
            r = requests.get(url, headers=_headers(), timeout=timeout)
            r.raise_for_status()
            data = r.json() or {}
        except requests.RequestException as exc:
            log.warning("RealDebrid instantAvailability failed: %s", exc)
            continue
        for h, hosters in data.items():
            # hosters is a dict; non-empty means at least one cached variant
            if isinstance(hosters, dict) and hosters:
                cached.add(h.lower())
    log.info("RealDebrid cache check: %d/%d cached", len(cached), len(hashes))
    return cached


def add_magnet(magnet: str, timeout: int = 30) -> dict:
    """Add a magnet and auto-select all files. Returns the torrent dict."""
    if not is_configured():
        raise RuntimeError("RealDebrid not configured")
    url = f"{REALDEBRID_BASE_URL.rstrip('/')}/torrents/addMagnet"
    log.info("RealDebrid: adding magnet %s", magnet[:80])
    r = requests.post(url, headers=_headers(), data={"magnet": magnet}, timeout=timeout)
    r.raise_for_status()
    data = r.json() or {}
    rd_id = data.get("id")
    if not rd_id:
        raise RuntimeError(f"RealDebrid addMagnet returned no id: {data}")
    # Select all files so RD starts unrestricting
    sel = requests.post(
        f"{REALDEBRID_BASE_URL.rstrip('/')}/torrents/selectFiles/{rd_id}",
        headers=_headers(), data={"files": "all"}, timeout=timeout,
    )
    sel.raise_for_status()
    return {"id": rd_id, "hash": data.get("uri", "")}


def get_info(rd_id: str, timeout: int = 15) -> dict | None:
    try:
        r = requests.get(
            f"{REALDEBRID_BASE_URL.rstrip('/')}/torrents/info/{rd_id}",
            headers=_headers(), timeout=timeout,
        )
        r.raise_for_status()
        return r.json() or None
    except requests.RequestException as exc:
        log.debug("RealDebrid info failed: %s", exc)
        return None


def wait_until_ready(rd_id: str) -> dict | None:
    """Poll RealDebrid for completion."""
    deadline = time.monotonic() + TORBOX_POLL_TIMEOUT_SEC
    last_status: str | None = None
    while time.monotonic() < deadline:
        info = get_info(rd_id)
        if info:
            status = info.get("status") or ""
            if status != last_status:
                log.info("RealDebrid status: %s", status)
                last_status = status
            if status == "downloaded":
                return info
        time.sleep(TORBOX_POLL_INTERVAL_SEC)
    log.warning("RealDebrid: timed out waiting for %s", rd_id)
    return None


def unrestrict_link(link: str, timeout: int = 15) -> str | None:
    """Convert a RealDebrid hoster link to a direct streaming URL."""
    try:
        r = requests.post(
            f"{REALDEBRID_BASE_URL.rstrip('/')}/unrestrict/link",
            headers=_headers(), data={"link": link}, timeout=timeout,
        )
        r.raise_for_status()
        return (r.json() or {}).get("download")
    except Exception as exc:
        log.warning("RealDebrid unrestrict failed: %s", exc)
        return None
