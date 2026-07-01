"""Aggregates monitored series into requests-shaped rows, so auto-approved
(and manually monitored) series show up in the same "All Requests" admin list
as movies instead of being invisible there (they never get a `requests` row -
only movies go through processor.process()).

Each series row gets a `seasons` list (season -> episode statuses) built from
wanted_episodes + virtual_items, so the admin UI can expand a series into its
season/episode availability without a separate page.
"""
import logging

import db

log = logging.getLogger(__name__)


def _episode_status(ep: dict, virtual_item: dict | None) -> str:
    if virtual_item:
        return "available"
    if ep["status"] == "not_aired":
        return "upcoming"
    if ep["status"] == "found":
        return "requested"
    return ep["status"] or "wanted"


def _season_status(episode_statuses: set[str]) -> str:
    if not episode_statuses:
        return "wanted"
    if episode_statuses == {"available"}:
        return "success"
    if episode_statuses == {"upcoming"}:
        return "upcoming"
    if "available" in episode_statuses or "requested" in episode_statuses:
        return "wanted"  # partially there  -  still needs attention, styled as wanted
    return "wanted"


def series_rows() -> list[dict]:
    """Every monitored series as one requests-shaped row with a `seasons` list."""
    series_list = db.get_all_monitored_series()
    if not series_list:
        return []

    episodes_by_imdb: dict[str, list[dict]] = {}
    for ep in db.get_all_wanted_episodes():
        episodes_by_imdb.setdefault(ep["imdb_id"], []).append(ep)

    virtual_by_key: dict[tuple, dict] = {}
    for v in db.get_all_virtual_items():
        if v.get("media_type") == "series" and v.get("imdb_id") and v.get("season") and v.get("episode"):
            virtual_by_key[(v["imdb_id"], v["season"], v["episode"])] = v

    rows = []
    for series in series_list:
        imdb_id = series["imdb_id"]
        eps = episodes_by_imdb.get(imdb_id, [])
        by_season: dict[int, list[dict]] = {}
        for ep in eps:
            vi = virtual_by_key.get((imdb_id, ep["season"], ep["episode"]))
            by_season.setdefault(ep["season"], []).append({
                "episode": ep["episode"],
                "status": _episode_status(ep, vi),
                "air_date": ep.get("air_date"),
            })

        seasons = []
        all_statuses: set[str] = set()
        for season_num in sorted(by_season):
            ep_list = sorted(by_season[season_num], key=lambda e: e["episode"])
            statuses = {e["status"] for e in ep_list}
            all_statuses |= statuses
            seasons.append({
                "season": season_num,
                "status": _season_status(statuses),
                "episodes": ep_list,
            })

        if not seasons:
            overall = "wanted"
        elif all_statuses == {"available"}:
            overall = "success"
        elif all_statuses == {"upcoming"}:
            overall = "upcoming"
        else:
            overall = "wanted"

        rows.append({
            "id": f"series-{series['id']}",
            "title": series["title"],
            "imdb_id": imdb_id,
            "media_type": "series",
            "status": overall,
            "created_at": series.get("added_at_date") or series.get("last_checked"),
            "seasons": seasons,
        })
    return rows
