"""Runtime-editable settings overlay.

Reads DB-stored overrides first, falls back to the static config module
values loaded from .env at startup. Type-aware: bool keys are normalised,
list keys split on commas, integer values parsed.

UI keys are grouped via SETTING_GROUPS for the Settings tab.
"""
from __future__ import annotations

import logging

import config as _config
import db

log = logging.getLogger(__name__)

# Type hints per key  -  drives parsing of stored strings.
_BOOL_KEYS = {
    "CATBOX_MODE",
    "CATBOX_PRELOAD",
    "ALLOW_4K",
    "EXCLUDE_REMUX",
    "EXCLUDE_BLURAY",
    "EXCLUDE_CAM",
    "STRICT_NO_CAM",
    "PREFER_WEBDL",
    "PREFER_HEVC",
    "ZILEAN_ENABLED",
    "CATCHUP_ENABLED",
    "CATBOX_LAZY_ADD",
    "CATBOX_PRELOAD",
    "AUTO_UPGRADE_ENABLED",
    "SEASON_PACK_CONSOLIDATION_ENABLED",
    "NOTIFY_ON_SUCCESS",
    "NOTIFY_ON_FAILURE",
    "MULTI_DEBRID_ENABLED",
    "WEBDAV_ENABLED",
    "AUTH_ENABLED",
    "TRUSTED_PROXY_AUTH",
    "LITE_MODE",
    "SUBLIMINAL_ENABLED",
}
_LIST_KEYS = {
    "QUALITY_PREFERENCE",
    "AUDIO_LANGUAGE_PREFERENCE",
    "EXCLUDE_LANGUAGES",
    "OPENSUBTITLES_LANGUAGES",
}
# People type a language by whatever name/code they know it under. The APIs
# we query (OpenSubtitles, subliminal) expect the ISO 639-1 code, so normalize
# common alternates here, once, for every consumer of OPENSUBTITLES_LANGUAGES.
_LANGUAGE_ALIASES = {
    "dutch": "nl", "dut": "nl", "nld": "nl", "ned": "nl",
    "flemish": "nl", "vlaams": "nl",
}
_INT_KEYS = {
    "MIN_SEEDERS",
    "MAX_SIZE_GB",
    "WEB_PLAYER_MAX_SIZE_GB",
    "CATBOX_IDLE_MINUTES",
    "CATBOX_GC_INTERVAL_MINUTES",
    "TORBOX_POLL_INTERVAL_SEC",
    "TORBOX_POLL_TIMEOUT_SEC",
    "JELLYFIN_REFRESH_DELAY_SEC",
    "MERGE_VERSIONS_INTERVAL_HOURS",
    "CLEANUP_INTERVAL_HOURS",
    "STRM_GENERATOR_INTERVAL_HOURS",
    "MONITOR_INTERVAL_HOURS",
    "MOVIE_SYNC_INTERVAL_MINUTES",
    "MAX_RETRY_ATTEMPTS",
    "BACKUP_INTERVAL_HOURS",
    "BLACKLIST_FAIL_THRESHOLD",
    "TRENDING_PRECACHE_COUNT",
    "TRENDING_CHECK_INTERVAL_HOURS",
    "TRENDING_TV_COUNT",
    "POPULAR_MOVIE_COUNT",
    "POPULAR_TV_COUNT",
    "NETFLIX_NL_TOP_COUNT",
    "PRIME_NL_TOP_COUNT",
    "DISNEY_NL_TOP_COUNT",
    "AUTO_ADD_MIN_VOTES",
    "AUTO_UPGRADE_INTERVAL_HOURS",
    "SEASON_PACK_CHECK_INTERVAL_HOURS",
    "RETRY_QUEUE_INTERVAL_MINUTES",
    "HEALTH_CACHE_SECONDS",
    "CONTINUE_WATCHING_INTERVAL_MINUTES",
    "CATCHUP_DELAY_SEC",
    "CATCHUP_TAKE",
}

# Keys that take effect on the next access (no restart).
HOT_RELOAD = {
    "TORBOX_API_KEY",
    "TORBOX_BASE_URL",
    "JELLYFIN_URL",
    "JELLYFIN_API_KEY",
    "SEERR_URL",
    "SEERR_API_KEY",
    "TMDB_API_KEY",
    "ZILEAN_URL",
    "ZILEAN_ENABLED",
    "CATBOX_MODE",
    "CATBOX_LAZY_ADD",
    "CATBOX_IDLE_MINUTES",
    "QUALITY_PREFERENCE",
    "ALLOW_4K",
    "EXCLUDE_REMUX",
    "EXCLUDE_BLURAY",
    "EXCLUDE_CAM",
    "STRICT_NO_CAM",
    "PREFER_WEBDL",
    "PREFER_HEVC",
    "MIN_SEEDERS",
    "MAX_SIZE_GB",
    "AUDIO_LANGUAGE_PREFERENCE",
    "EXCLUDE_LANGUAGES",
    "OPENSUBTITLES_LANGUAGES",
    "SUBLIMINAL_ENABLED",
    "BLACKLIST_FAIL_THRESHOLD",
    "WEB_PLAYER_MAX_SIZE_GB",
    "NOTIFY_ON_SUCCESS",
    "NOTIFY_ON_FAILURE",
    "DISCORD_WEBHOOK_URL",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "AUTO_UPGRADE_ENABLED",
    "SEASON_PACK_CONSOLIDATION_ENABLED",
    "WEBDAV_ENABLED",
    "MULTI_DEBRID_ENABLED",
    "REALDEBRID_API_KEY",
    "AUTH_ENABLED",
    "AUTH_USERNAME",
    "AUTH_PASSWORD",
    "AUTH_PASSWORD_HASH",
    "TRUSTED_PROXY_AUTH",
    "TRUSTED_PROXY_USER_HEADER",
    "TRUSTED_PROXY_NETWORKS",
    "TRENDING_TV_COUNT", "POPULAR_MOVIE_COUNT", "POPULAR_TV_COUNT",
    "NETFLIX_NL_TOP_COUNT", "PRIME_NL_TOP_COUNT", "DISNEY_NL_TOP_COUNT",
    "AUTO_ADD_MIN_RATING", "AUTO_ADD_MIN_VOTES", "AUTO_ADD_REGION",
    "RADARR_URL", "RADARR_API_KEY", "SONARR_URL", "SONARR_API_KEY",
    "TRAKT_CLIENT_ID", "TRAKT_CLIENT_SECRET",
}

# Logical groups for the Settings UI tab. "category" buckets groups under the
# top-level sub-tabs in the Settings pane so the page isn't one long scroll.
SETTING_GROUPS = [
    {
        "id": "mode",
        "title": "Deployment mode (restart required)",
        "category": "general",
        "keys": ["LITE_MODE"],
    },
    {
        "id": "connections",
        "title": "Connections",
        "category": "general",
        "keys": [
            "TORBOX_API_KEY", "TORBOX_BASE_URL",
            "JELLYFIN_URL", "JELLYFIN_API_KEY",
            "SEERR_URL", "SEERR_API_KEY",
            "TMDB_API_KEY",
            "TRAKT_CLIENT_ID", "TRAKT_CLIENT_SECRET",
            "ZILEAN_ENABLED", "ZILEAN_URL",
            "REALDEBRID_API_KEY", "MULTI_DEBRID_ENABLED",
        ],
    },
    {
        "id": "catbox",
        "title": "Catbox (lazy materialization)",
        "category": "general",
        "keys": ["CATBOX_MODE", "CATBOX_LAZY_ADD", "CATBOX_PRELOAD", "CATBOX_HOST", "CATBOX_IDLE_MINUTES", "CATBOX_GC_INTERVAL_MINUTES"],
    },
    {
        "id": "quality",
        "title": "Quality & filtering",
        "category": "quality",
        "keys": [
            "QUALITY_PREFERENCE", "ALLOW_4K", "EXCLUDE_REMUX", "EXCLUDE_BLURAY", "EXCLUDE_CAM",
            "PREFER_WEBDL", "PREFER_HEVC", "MIN_SEEDERS", "MAX_SIZE_GB", "STRICT_NO_CAM",
            "WEB_PLAYER_MAX_SIZE_GB",
        ],
    },
    {
        "id": "languages",
        "title": "Languages & subtitles",
        "category": "quality",
        "keys": ["AUDIO_LANGUAGE_PREFERENCE", "EXCLUDE_LANGUAGES", "OPENSUBTITLES_LANGUAGES",
                 "OPENSUBTITLES_API_KEY", "SUBLIMINAL_ENABLED"],
    },
    {
        "id": "auto",
        "title": "Automation",
        "category": "automation",
        "keys": [
            "AUTO_UPGRADE_ENABLED", "AUTO_UPGRADE_INTERVAL_HOURS",
            "SEASON_PACK_CONSOLIDATION_ENABLED", "SEASON_PACK_CHECK_INTERVAL_HOURS",
            "TRENDING_PRECACHE_COUNT", "TRENDING_CHECK_INTERVAL_HOURS",
            "BLACKLIST_FAIL_THRESHOLD",
        ],
    },
    {
        "id": "auto_add",
        "title": "Auto-add categories",
        "category": "automation",
        "keys": [
            "TRENDING_PRECACHE_COUNT", "TRENDING_TV_COUNT",
            "POPULAR_MOVIE_COUNT", "POPULAR_TV_COUNT",
            "NETFLIX_NL_TOP_COUNT", "PRIME_NL_TOP_COUNT", "DISNEY_NL_TOP_COUNT",
            "AUTO_ADD_MIN_RATING", "AUTO_ADD_MIN_VOTES", "AUTO_ADD_REGION",
        ],
    },
    {
        "id": "arr_import",
        "title": "Radarr / Sonarr import",
        "category": "automation",
        "keys": ["RADARR_URL", "RADARR_API_KEY", "SONARR_URL", "SONARR_API_KEY"],
    },
    {
        "id": "security",
        "title": "Authentication",
        "category": "security",
        "keys": [
            "AUTH_ENABLED", "AUTH_USERNAME",
            "TRUSTED_PROXY_AUTH", "TRUSTED_PROXY_USER_HEADER",
            "TRUSTED_PROXY_NETWORKS",
            "OIDC_ENABLED", "OIDC_ISSUER_URL", "OIDC_CLIENT_ID",
            "OIDC_PROVIDER_NAME", "OIDC_USER_CLAIM", "OIDC_SCOPES",
        ],
    },
    {
        "id": "notifications",
        "title": "Notifications",
        "category": "security",
        "keys": [
            "NOTIFY_ON_SUCCESS", "NOTIFY_ON_FAILURE",
            "DISCORD_WEBHOOK_URL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
        ],
    },
    {
        "id": "intervals",
        "title": "Schedulers (restart required)",
        "category": "advanced",
        "keys": [
            "STRM_GENERATOR_INTERVAL_HOURS", "CLEANUP_INTERVAL_HOURS",
            "MONITOR_INTERVAL_HOURS", "MOVIE_SYNC_INTERVAL_MINUTES",
            "MERGE_VERSIONS_INTERVAL_HOURS", "BACKUP_INTERVAL_HOURS",
            "RETRY_QUEUE_INTERVAL_MINUTES", "CONTINUE_WATCHING_INTERVAL_MINUTES",
        ],
    },
]

# Display labels + order for the Settings sub-tabs, keyed by group "category".
SETTING_CATEGORIES = [
    {"id": "general", "title": "General"},
    {"id": "quality", "title": "Quality & Subtitles"},
    {"id": "automation", "title": "Automation"},
    {"id": "security", "title": "Security & Notifications"},
    {"id": "advanced", "title": "Advanced"},
]


def _coerce(key: str, raw: str | None):
    if raw is None:
        return None
    if key in _BOOL_KEYS:
        return str(raw).strip().lower() in ("1", "true", "yes", "on")
    if key in _LIST_KEYS:
        return [v.strip() for v in raw.split(",") if v.strip()]
    if key in _INT_KEYS:
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    return raw


def _normalize(key: str, value):
    if key == "OPENSUBTITLES_LANGUAGES" and isinstance(value, list):
        return [_LANGUAGE_ALIASES.get(v.lower(), v.lower()) for v in value]
    return value


def get(key: str, default=None):
    try:
        raw = db.get_setting(key)
    except Exception as exc:
        log.debug("settings.get: DB read failed for %s (%s); falling back to .env", key, exc)
        raw = None
    # An empty-string row is a stale artifact, not a real override: set()
    # deletes the row when handed "" or None, so a stored "" can only come
    # from legacy data. Treat it as absent and fall through to the .env
    # default, otherwise it silently shadows a perfectly good config value.
    if raw is not None and raw != "":
        coerced = _coerce(key, raw)
        if coerced is not None:
            return _normalize(key, coerced)
    if hasattr(_config, key):
        return _normalize(key, getattr(_config, key))
    return default


def set(key: str, value) -> None:
    if value is None or value == "":
        db.set_setting(key, None)
        return
    if isinstance(value, bool):
        stored = "true" if value else "false"
    elif isinstance(value, (list, tuple)):
        stored = ",".join(str(v) for v in value)
    else:
        stored = str(value)
    db.set_setting(key, stored)


def all_for_ui() -> list[dict]:
    """Return groups with each key's current value + type for the UI."""
    overrides = db.get_all_settings()
    out = []
    for group in SETTING_GROUPS:
        items = []
        for key in group["keys"]:
            override_raw = overrides.get(key)
            current = get(key)
            kind = (
                "bool" if key in _BOOL_KEYS
                else "list" if key in _LIST_KEYS
                else "int" if key in _INT_KEYS
                else "str"
            )
            items.append({
                "key": key,
                "value": current,
                "kind": kind,
                "overridden": override_raw is not None,
                "hot_reload": key in HOT_RELOAD,
            })
        out.append({
            "id": group["id"],
            "title": group["title"],
            "category": group.get("category", "general"),
            "items": items,
        })
    return out
