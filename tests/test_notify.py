import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import notify


def test_discord_url_uses_specific_media_webhook_with_default_fallback(monkeypatch):
    values = {
        "DISCORD_WEBHOOK_URL": "https://discord.example/default",
        "DISCORD_WEBHOOK_URL_MOVIES": "https://discord.example/movies",
        "DISCORD_WEBHOOK_URL_SHOWS": "https://discord.example/shows",
    }
    monkeypatch.setattr(notify.settings, "get", lambda key, default=None: values.get(key, default))

    assert notify._discord_url_for("movie") == "https://discord.example/movies"
    assert notify._discord_url_for("series") == "https://discord.example/shows"
    assert notify._discord_url_for("tv") == "https://discord.example/shows"
    assert notify._discord_url_for(None) == "https://discord.example/default"


def test_discord_url_falls_back_and_can_be_empty(monkeypatch):
    values = {
        "DISCORD_WEBHOOK_URL": "https://discord.example/default",
        "DISCORD_WEBHOOK_URL_MOVIES": "",
        "DISCORD_WEBHOOK_URL_SHOWS": "",
    }
    monkeypatch.setattr(notify.settings, "get", lambda key, default=None: values.get(key, default))

    assert notify._discord_url_for("movie") == "https://discord.example/default"
    assert notify._discord_url_for("series") == "https://discord.example/default"

    monkeypatch.setattr(notify.settings, "get", lambda key, default=None: "")
    assert notify._discord_url_for("movie") == ""
    assert notify._discord_url_for("series") == ""
