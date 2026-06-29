import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import auto_approve


def test_per_genre_limits_are_independent_and_skips_do_not_count(monkeypatch):
    rules = {
        "movie": {
            "28": {"auto_request_trending": True},
            "35": {"auto_request_trending": True},
        },
        "tv": {
            "18": {"auto_request_trending": True},
        },
    }
    pages = {
        ("movie", 28, 1): [
            {"tmdb_id": 1, "title": "Existing Action", "rating": 8, "votes": 500},
            {"tmdb_id": 2, "title": "Action One", "rating": 8, "votes": 500},
            {"tmdb_id": 3, "title": "Action Two", "rating": 8, "votes": 500},
        ],
        ("movie", 35, 1): [
            {"tmdb_id": 4, "title": "Comedy One", "rating": 8, "votes": 500},
            {"tmdb_id": 5, "title": "Comedy Two", "rating": 8, "votes": 500},
        ],
        ("tv", 18, 1): [
            {"tmdb_id": 6, "title": "Existing Drama", "rating": 8, "votes": 500},
            {"tmdb_id": 7, "title": "Drama One", "rating": 8, "votes": 500},
            {"tmdb_id": 8, "title": "Drama Two", "rating": 8, "votes": 500},
        ],
    }

    monkeypatch.setattr(auto_approve, "get_rules", lambda media_type: rules[media_type])
    monkeypatch.setattr(auto_approve._settings, "get", lambda key, default=None: {
        "AUTO_APPROVE_MOVIE_PER_GENRE_LIMIT": 2,
        "AUTO_APPROVE_TV_PER_GENRE_LIMIT": 2,
        "AUTO_APPROVE_MAX_PAGES": 1,
        "AUTO_ADD_MIN_RATING": 6.0,
        "AUTO_ADD_MIN_VOTES": 100,
    }.get(key, default))
    monkeypatch.setattr(auto_approve.tmdb, "discover_by_genre", lambda media_type, genre_id, year_from, year_to, page, region: pages.get((media_type, genre_id, page), []))
    monkeypatch.setattr(auto_approve.tmdb, "tmdb_to_imdb", lambda tmdb_id, media_type: f"tt{tmdb_id}")
    monkeypatch.setattr(auto_approve.tmdb, "get_show_info", lambda tmdb_id: {"number_of_seasons": 1})
    monkeypatch.setattr(auto_approve.processor, "process", lambda request: True)
    monkeypatch.setattr(auto_approve.db, "upsert_monitored_series", lambda *args, **kwargs: None)

    summary = auto_approve._fill_per_genre(
        seen_movies={"tt1"},
        seen_series={"tt6"},
        movie_bl=set(),
        tv_bl=set(),
        person_bl=set(),
    )

    assert summary["movies_queued"] == 4
    assert summary["series_queued"] == 2
    assert summary["total_queued"] == 6
    movie_results = {r["genre_id"]: r for r in summary["genres"]["movie"]}
    tv_result = summary["genres"]["tv"][0]
    assert movie_results[28]["skipped"] == 1
    assert movie_results[28]["queued"] == 2
    assert movie_results[35]["queued"] == 2
    assert tv_result["skipped"] == 1
    assert tv_result["queued"] == 2


def test_per_genre_exhausts_pages_when_target_not_reached(monkeypatch):
    monkeypatch.setattr(auto_approve.tmdb, "discover_by_genre", lambda *args, **kwargs: [])

    result = auto_approve._fill_genre(
        "movie", 28, {}, 3, set(), set(), set(), max_pages=2,
    )

    assert result["queued"] == 0
    assert result["scanned"] == 0
    assert result["exhausted"] is True
