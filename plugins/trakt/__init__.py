from flask import Blueprint
from . import routes as _routes

blueprint = Blueprint("trakt", __name__)
blueprint.register_blueprint(_routes.bp)

PLUGIN_META = {
    "label":       "Trakt",
    "version":     "1.0.0",
    "description": "Sync watchlist with Trakt.tv and scrobble watch history",
    "user_fields": [],
}


def run_migrations() -> None:
    import db
    with db._connect() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS trakt_tokens (
                user_id       INTEGER PRIMARY KEY,
                access_token  TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at    INTEGER NOT NULL,
                trakt_username TEXT,
                synced_at     TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)


def session_data(user_record: dict) -> dict:
    user_id = user_record.get("id")
    if not user_id:
        return {"trakt_connected": False, "trakt_username": None}
    from . import trakt_api
    tok = trakt_api.get_token(user_id)
    return {
        "trakt_connected": tok is not None,
        "trakt_username":  tok["trakt_username"] if tok else None,
    }


def register_jobs(scheduler) -> None:
    from . import trakt_api
    scheduler.add_job(
        trakt_api.sync_all_users,
        "interval", minutes=30,
        id="trakt_sync",
        replace_existing=True,
    )
