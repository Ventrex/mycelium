"""Smart retry queue with exponential backoff.

Failed requests (movies, series and single wanted-episodes) are enqueued for
retry at increasing intervals (RETRY_BACKOFF_MINUTES). A scheduler picks up
due items every RETRY_QUEUE_INTERVAL_MINUTES and re-runs them serially,
respecting the TorBox createtorrent budget.

Every item carries an `origin`: "manual" for a user/Seerr request, "auto" for
anything queued by auto-approve/trending/the series monitor. Due items are
processed manual-first, oldest-created-first within each group, so a backlog
of background fill can never delay something a user just clicked.
"""
import logging

import db
from config import RETRY_BACKOFF_MINUTES
from webhook_parser import MediaRequest

log = logging.getLogger(__name__)


def schedule(req: MediaRequest, attempt: int) -> None:
    """Enqueue a failed movie/series request for retry at the next backoff interval."""
    if attempt >= len(RETRY_BACKOFF_MINUTES):
        log.info("Retry: giving up on %s after %d attempts", req.title, attempt)
        return
    delay = RETRY_BACKOFF_MINUTES[attempt] * 60
    db.enqueue_retry(req.imdb_id, req.title, req.media_type, req.seasons, attempt + 1, delay,
                      origin=getattr(req, "origin", "manual"))
    log.info("Retry: queued %s for attempt %d in %dmin (origin=%s)",
             req.title, attempt + 1, RETRY_BACKOFF_MINUTES[attempt], getattr(req, "origin", "manual"))


def schedule_episode(ep: dict, origin: str = "auto") -> None:
    """Enqueue a single wanted-episode for retry. Unlike schedule(), this never
    gives up: a still-wanted episode keeps being retried at the longest backoff
    step forever, matching the 'watch indefinitely' behaviour of the series
    monitor it replaces for rate-limited episodes."""
    attempt = ep.get("attempt_count", 0)
    idx = min(attempt, len(RETRY_BACKOFF_MINUTES) - 1)
    delay = RETRY_BACKOFF_MINUTES[idx] * 60
    db.enqueue_retry(ep["imdb_id"], ep["title"], "episode", None, attempt, delay,
                      origin=origin, wanted_episode_id=ep["id"])
    log.info("Retry: queued episode %s S%02dE%02d for retry in %dmin (origin=%s)",
             ep["title"], ep["season"], ep["episode"], RETRY_BACKOFF_MINUTES[idx], origin)


def run_due() -> int:
    """Process due retries SERIALLY (not as a thread stampede) and stop early
    once the TorBox createtorrent budget is exhausted, so a backlog of
    rate-limited items can't keep re-triggering 429s every cycle.
    Items not processed this round are left in the queue for the next run."""
    import processor  # local import to avoid cycle
    import monitor  # local import to avoid cycle
    import torbox
    due = db.get_due_retries()
    if not due:
        return 0

    usage = torbox.createtorrent_usage()
    if usage["count"] >= torbox._CREATETORRENT_LIMIT_HOUR - 2:
        log.info("Retry: skipping this cycle  -  createtorrent budget %d/%d (resets ~%dm)",
                 usage["count"], torbox._CREATETORRENT_LIMIT_HOUR,
                 max(1, usage["resets_in_sec"] // 60))
        return 0

    log.info("Retry: processing up to %d due retries (budget %d/%d)",
             len(due), usage["count"], torbox._CREATETORRENT_LIMIT_HOUR)
    processed = 0
    for row in due:
        # Re-check budget before each item; bail out (leave the rest queued) when low.
        if torbox.createtorrent_usage()["count"] >= torbox._CREATETORRENT_LIMIT_HOUR - 2:
            log.info("Retry: budget reached after %d item(s)  -  leaving %d for next cycle",
                     processed, len(due) - processed)
            break
        db.remove_retry(row["id"])
        try:
            import metrics_prom
            metrics_prom.retry_attempts_total.inc(1)
        except Exception:
            pass

        if row.get("wanted_episode_id"):
            ep = db.get_wanted_episode(row["wanted_episode_id"])
            if not ep or ep.get("status") != "wanted":
                processed += 1
                continue
            try:
                monitor.retry_episode(ep)
            except processor.RateLimited:
                schedule_episode(ep, origin=row.get("origin", "auto"))
            processed += 1
            continue

        seasons = [int(s) for s in (row.get("seasons") or "").split(",") if s.strip().isdigit()]
        req = MediaRequest(
            title=row["title"], media_type=row["media_type"],
            imdb_id=row["imdb_id"], seasons=seasons,
            origin=row.get("origin", "manual"),
        )
        # Serial: process inline so we observe quota between items instead of
        # firing N parallel createtorrent calls at once.
        processor.process(req, _retry_attempt=row["attempt"])
        processed += 1
    return processed
