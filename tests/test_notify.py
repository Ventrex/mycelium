import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("TORBOX_API_KEY", "test")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import notify  # noqa: E402


def test_discord_embed_uses_media_title_and_rich_details(monkeypatch):
    posted = {}
    monkeypatch.setattr(notify.settings, "get", lambda key, default=None: {
        "NOTIFY_ON_SUCCESS": True,
        "DISCORD_WEBHOOK_URL": "https://discord.example/webhook",
        "TELEGRAM_BOT_TOKEN": "",
        "TELEGRAM_CHAT_ID": "",
    }.get(key, default))
    monkeypatch.setattr(notify, "_media_details", lambda *args, **kwargs: {
        "title": "Dune: Part Two",
        "year": "2024",
        "runtime": "2u 46m",
        "actors": ["Timothée Chalamet", "Zendaya"],
        "overview": "Paul Atreides unites with Chani and the Fremen.",
        "poster_url": "https://image.tmdb.org/t/p/w342/poster.jpg",
        "season_summary": None,
        "url": "https://www.themoviedb.org/movie/693134",
    })
    monkeypatch.setattr(notify.requests, "post", lambda url, json, timeout: posted.update({
        "url": url,
        "json": json,
        "timeout": timeout,
    }) or MagicMock(status_code=204))

    notify.send("Added: tt15239678", "movie · 1080p", True, imdb_id="tt15239678", media_type="movie")

    embed = posted["json"]["embeds"][0]
    assert embed["title"] == "Added: Dune: Part Two (2024)"
    assert "tt15239678" not in embed["title"]
    assert embed["image"]["url"].endswith("/poster.jpg")
    assert {field["name"] for field in embed["fields"]} >= {"Jaartal", "Speelduur", "Acteurs"}


def test_discord_embed_includes_series_seasons(monkeypatch):
    posted = {}
    monkeypatch.setattr(notify.settings, "get", lambda key, default=None: {
        "NOTIFY_ON_SUCCESS": True,
        "DISCORD_WEBHOOK_URL": "https://discord.example/webhook",
        "TELEGRAM_BOT_TOKEN": "",
        "TELEGRAM_CHAT_ID": "",
    }.get(key, default))
    monkeypatch.setattr(notify, "_media_details", lambda *args, **kwargs: {
        "title": "Foundation",
        "year": "2021",
        "runtime": "49m",
        "actors": ["Jared Harris", "Lee Pace"],
        "overview": "A complex saga of humans scattered on planets throughout the galaxy.",
        "poster_url": "https://image.tmdb.org/t/p/w342/foundation.jpg",
        "season_summary": "3 seizoenen · aangevraagd: S01, S02",
        "url": "https://www.themoviedb.org/tv/93740",
    })
    monkeypatch.setattr(notify.requests, "post", lambda url, json, timeout: posted.update({"json": json}) or MagicMock(status_code=204))

    notify.send("Added: tt0804484", "series · 1080p", True, imdb_id="tt0804484", media_type="series", seasons=[1, 2])

    fields = {field["name"]: field["value"] for field in posted["json"]["embeds"][0]["fields"]}
    assert fields["Seizoenen"] == "3 seizoenen · aangevraagd: S01, S02"


def _patch_webhooks(monkeypatch, **values):
    monkeypatch.setattr(notify.settings, "get", lambda key, default=None: values.get(key, default))


def test_discord_url_movie_uses_movies_webhook(monkeypatch):
    _patch_webhooks(monkeypatch,
                    DISCORD_WEBHOOK_URL="https://discord.example/default",
                    DISCORD_WEBHOOK_URL_MOVIES="https://discord.example/movies",
                    DISCORD_WEBHOOK_URL_SHOWS="https://discord.example/shows")
    assert notify._discord_url_for("movie") == "https://discord.example/movies"


def test_discord_url_series_uses_shows_webhook(monkeypatch):
    _patch_webhooks(monkeypatch,
                    DISCORD_WEBHOOK_URL="https://discord.example/default",
                    DISCORD_WEBHOOK_URL_MOVIES="https://discord.example/movies",
                    DISCORD_WEBHOOK_URL_SHOWS="https://discord.example/shows")
    assert notify._discord_url_for("tv") == "https://discord.example/shows"
    assert notify._discord_url_for("series") == "https://discord.example/shows"


def test_discord_url_falls_back_to_default(monkeypatch):
    _patch_webhooks(monkeypatch, DISCORD_WEBHOOK_URL="https://discord.example/default")
    assert notify._discord_url_for("movie") == "https://discord.example/default"
    assert notify._discord_url_for("tv") == "https://discord.example/default"
    assert notify._discord_url_for(None) == "https://discord.example/default"


def test_discord_url_empty_when_nothing_configured(monkeypatch):
    _patch_webhooks(monkeypatch)
    assert notify._discord_url_for("movie") == ""
    assert notify._discord_url_for("tv") == ""
