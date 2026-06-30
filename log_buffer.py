import logging
import time
from collections import deque

_buffer: deque[dict] = deque(maxlen=1000)

_FORMATTER = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")


def _type_for(name: str) -> str:
    """Bucket a logger name into one of the Logs page categories."""
    name = (name or "").lower()
    if name.startswith("auto_approve"):
        return "auto_approve"
    if name.startswith("subtitles") or "subtitle" in name:
        return "subtitles"
    return "server"


class _BufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            _buffer.append({
                "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created)),
                "level": record.levelname,
                "name": record.name,
                "type": _type_for(record.name),
                "message": record.getMessage(),
                "line": _FORMATTER.format(record),
            })
        except Exception:
            pass


_handler = _BufferHandler()


def install() -> None:
    logging.getLogger().addHandler(_handler)


def get_lines(n: int = 100) -> list[str]:
    """Formatted log lines, oldest first (used by the /admin dashboard)."""
    lines = [e["line"] for e in _buffer]
    return lines[-n:]


def get_entries(n: int = 200, log_type: str | None = None) -> list[dict]:
    """Structured log entries, newest first, optionally filtered by category.

    log_type one of: "server", "auto_approve", "subtitles". None or "all"
    returns every category.
    """
    entries = list(_buffer)
    if log_type and log_type not in ("all", ""):
        entries = [e for e in entries if e["type"] == log_type]
    entries = entries[-n:]
    return [
        {"time": e["time"], "level": e["level"], "type": e["type"],
         "name": e["name"], "message": e["message"]}
        for e in reversed(entries)
    ]
