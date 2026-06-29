import logging

import requests

import settings

log = logging.getLogger(__name__)


def send(title: str, message: str, success: bool = True, *, imdb_id: str | None = None,
         media_type: str | None = None, seasons: list[int] | None = None,
         tmdb_id: int | None = None) -> None:
    if success and not settings.get("NOTIFY_ON_SUCCESS", True):
        return
    if not success and not settings.get("NOTIFY_ON_FAILURE", True):
        return
    details = _media_details(imdb_id, media_type, seasons, tmdb_id) if imdb_id or tmdb_id else None
    if details:
        title = _notification_title(title, details)
        message = _notification_message(message, details)
    discord_url = settings.get("DISCORD_WEBHOOK_URL", "")
    tg_token = settings.get("TELEGRAM_BOT_TOKEN", "")
    tg_chat = settings.get("TELEGRAM_CHAT_ID", "")
    if discord_url:
        _discord(discord_url, title, message, success, details=details)
    if tg_token and tg_chat:
        _telegram(tg_token, tg_chat, title, message, success)


def _media_details(imdb_id: str | None, media_type: str | None,
                   seasons: list[int] | None, tmdb_id: int | None = None) -> dict | None:
    if not imdb_id and not tmdb_id:
        return None
    try:
        import tmdb
        return tmdb.get_notification_details(imdb_id, media_type or "movie", seasons=seasons, tmdb_id=tmdb_id)
    except Exception as exc:
        log.debug("Media metadata lookup skipped for %s: %s", imdb_id, exc)
        return None


def _notification_title(fallback: str, details: dict) -> str:
    prefix = fallback.split(":", 1)[0] if ":" in fallback else fallback
    media_title = details.get("title") or fallback
    year = details.get("year")
    if prefix and prefix != fallback:
        return f"{prefix}: {media_title}{f' ({year})' if year else ''}"
    return f"{media_title}{f' ({year})' if year else ''}"


def _notification_message(message: str, details: dict) -> str:
    parts = [message]
    meta = []
    if details.get("runtime"):
        meta.append(details["runtime"])
    if details.get("actors"):
        meta.append("Acteurs: " + ", ".join(details["actors"]))
    if details.get("season_summary"):
        meta.append(details["season_summary"])
    if details.get("overview"):
        meta.append(details["overview"])
    if details.get("url"):
        meta.append(details["url"])
    if meta:
        parts.append("\n".join(meta))
    return "\n\n".join(p for p in parts if p)


def _discord(url: str, title: str, message: str, success: bool, *, details: dict | None = None) -> None:
    color = 0x4ADE80 if success else 0xF87171
    embed = {"title": title, "description": message[:4096], "color": color}
    if details:
        if details.get("url"):
            embed["url"] = details["url"]
        if details.get("poster_url"):
            embed["image"] = {"url": details["poster_url"]}
        fields = []
        if details.get("year"):
            fields.append({"name": "Jaartal", "value": str(details["year"]), "inline": True})
        if details.get("runtime"):
            fields.append({"name": "Speelduur", "value": details["runtime"], "inline": True})
        if details.get("season_summary"):
            fields.append({"name": "Seizoenen", "value": details["season_summary"][:1024], "inline": False})
        if details.get("actors"):
            fields.append({"name": "Acteurs", "value": ", ".join(details["actors"])[:1024], "inline": False})
        if fields:
            embed["fields"] = fields[:25]
    payload = {"embeds": [embed]}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as exc:
        log.warning("Discord notify failed: %s", exc)


def _telegram(token: str, chat_id: str, title: str, message: str, success: bool) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    emoji = "✅" if success else "❌"
    payload = {
        "chat_id": chat_id,
        "text": f"{emoji} *{title}*\n{message}",
        "parse_mode": "Markdown",
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as exc:
        log.warning("Telegram notify failed: %s", exc)


def test() -> dict:
    results = {}
    discord_url = settings.get("DISCORD_WEBHOOK_URL", "")
    tg_token = settings.get("TELEGRAM_BOT_TOKEN", "")
    tg_chat = settings.get("TELEGRAM_CHAT_ID", "")
    if discord_url:
        try:
            r = requests.post(
                discord_url,
                json={"content": "🧪 Test notification from Mycelium"},
                timeout=10,
            )
            results["discord"] = "ok" if r.status_code < 400 else f"http {r.status_code}"
        except Exception as exc:
            results["discord"] = str(exc)[:100]
    else:
        results["discord"] = "not configured"
    if tg_token and tg_chat:
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            r = requests.post(
                url, json={"chat_id": tg_chat, "text": "🧪 Test notification"}, timeout=10,
            )
            results["telegram"] = "ok" if r.status_code < 400 else f"http {r.status_code}"
        except Exception as exc:
            results["telegram"] = str(exc)[:100]
    else:
        results["telegram"] = "not configured"
    return results
