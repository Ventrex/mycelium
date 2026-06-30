import auth
from flask import Blueprint, abort, jsonify, request

from . import mdblist_api

bp = Blueprint("mdblist_routes", __name__)


def _require_user() -> dict:
    rec = auth.current_user_record()
    if not rec or not rec.get("id"):
        abort(401)
    return rec


@bp.get("/ui/api/mdblist/status")
def mdblist_status():
    rec = _require_user()
    return jsonify(mdblist_api.status(rec["id"]))


@bp.post("/ui/api/mdblist/key")
def mdblist_set_key():
    rec = _require_user()
    api_key = str((request.get_json(silent=True) or {}).get("api_key") or "").strip()
    if not api_key:
        return jsonify(error="api_key required"), 400
    mdblist_api.set_key(rec["id"], api_key)
    return jsonify(status="saved")


@bp.post("/ui/api/mdblist/clear")
def mdblist_clear():
    rec = _require_user()
    mdblist_api.clear_key(rec["id"])
    return jsonify(status="cleared")


@bp.post("/ui/api/mdblist/sync")
def mdblist_sync():
    rec = _require_user()
    added = mdblist_api.sync_user(rec["id"])
    return jsonify(status="ok", added=added)
