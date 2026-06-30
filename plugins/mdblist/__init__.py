from flask import Blueprint

from . import routes as _routes

blueprint = Blueprint("mdblist", __name__)
blueprint.register_blueprint(_routes.bp)

PLUGIN_META = {
    "label":       "MDBList",
    "version":     "1.0.0",
    "description": "Sync your MDBList lists into Mycelium and optionally auto-request them",
    "user_fields": [],
    # No settings_ui: the per-user API key is handled by a dedicated card on the
    # React Settings page (the generic plugin renderer has no text-input field).
}


def run_migrations() -> None:
    import db
    with db._connect() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS mdblist_keys (
                user_id   INTEGER PRIMARY KEY,
                api_key   TEXT NOT NULL,
                synced_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)


def session_data(user_record: dict) -> dict:
    user_id = user_record.get("id")
    if not user_id:
        return {"mdblist_connected": False}
    from . import mdblist_api
    return {"mdblist_connected": mdblist_api.status(user_id)["connected"]}


def register_jobs(scheduler) -> None:
    from . import mdblist_api
    scheduler.add_job(
        mdblist_api.sync_all_users,
        "interval", minutes=30,
        id="mdblist_sync",
        replace_existing=True,
    )
