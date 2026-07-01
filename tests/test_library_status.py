import os
import sys

os.environ.setdefault("TORBOX_API_KEY", "test")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_series_rows_status_aggregation(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    import db
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    import threading
    monkeypatch.setattr(db, "_tls", threading.local())
    db.init()

    import library_status

    db.upsert_monitored_series("tt0000001", 1, "Fully Available Show", [1])
    db.upsert_wanted_episode("tt0000001", 1, "Fully Available Show", 1, 1, "2020-01-01")
    db.mark_episode_status("tt0000001", 1, 1, "found")
    db.insert_virtual_item("tok-a", "a" * 40, "magnet:?xt=urn:btih:" + "a" * 40,
                            "Fully Available Show S01E01", "series", season=1, episode=1,
                            imdb_id="tt0000001")

    db.upsert_monitored_series("tt0000002", 2, "Partially Wanted Show", [1])
    db.upsert_wanted_episode("tt0000002", 2, "Partially Wanted Show", 1, 1, "2020-01-01")
    db.upsert_wanted_episode("tt0000002", 2, "Partially Wanted Show", 1, 2, "2020-01-08")
    db.mark_episode_status("tt0000002", 1, 1, "found")
    db.insert_virtual_item("tok-b", "b" * 40, "magnet:?xt=urn:btih:" + "b" * 40,
                            "Partially Wanted Show S01E01", "series", season=1, episode=1,
                            imdb_id="tt0000002")
    # episode 2 stays "wanted", nothing registered for it

    db.upsert_monitored_series("tt0000003", 3, "Not Yet Aired Show", [1])
    db.upsert_wanted_episode("tt0000003", 3, "Not Yet Aired Show", 1, 1, "2099-01-01")
    db.mark_episode_status("tt0000003", 1, 1, "not_aired")

    rows = {r["title"]: r for r in library_status.series_rows()}

    assert rows["Fully Available Show"]["status"] == "success"
    assert rows["Fully Available Show"]["seasons"][0]["status"] == "success"

    assert rows["Partially Wanted Show"]["status"] == "wanted"
    ep_statuses = {e["episode"]: e["status"] for e in rows["Partially Wanted Show"]["seasons"][0]["episodes"]}
    assert ep_statuses == {1: "available", 2: "wanted"}

    assert rows["Not Yet Aired Show"]["status"] == "upcoming"
