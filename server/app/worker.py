"""Evaluation worker.

Runs in-process by default (RUN_INLINE_WORKER=true) so `uvicorn app.main:app` is the
only thing you need locally. In a deployment where you want it separate, set
RUN_INLINE_WORKER=false on the API and run `python -m app.worker` alongside it.
"""

from __future__ import annotations

import logging
import signal
import threading
import time

from app.config import settings
from app.db import SessionLocal
from app.services.evaluation import claim_next, process_evaluation

logger = logging.getLogger("pmcoach.worker")

_stop_event = threading.Event()


def run_once() -> bool:
    """Process at most one queued evaluation. Returns True if work was done."""
    db = SessionLocal()
    try:
        evaluation = claim_next(db)
        if evaluation is None:
            return False
        try:
            process_evaluation(db, evaluation)
        except Exception:  # noqa: BLE001 - a worker must never die on one item
            logger.exception("unhandled error processing evaluation %s", evaluation.attempt_id)
            db.rollback()
            evaluation.status = "failed"
            evaluation.error_code = "worker_exception"
            db.commit()
        return True
    finally:
        db.close()


def loop(stop: threading.Event | None = None) -> None:
    stop = stop or _stop_event
    logger.info(
        "evaluation worker started (provider=%s)", settings.evaluator_provider
    )
    while not stop.is_set():
        try:
            did_work = run_once()
        except Exception:  # noqa: BLE001
            logger.exception("worker loop error")
            did_work = False
        if not did_work:
            stop.wait(settings.worker_poll_seconds)
    logger.info("evaluation worker stopped")


def start_background_worker() -> tuple[threading.Thread, threading.Event]:
    stop = threading.Event()
    thread = threading.Thread(target=loop, args=(stop,), name="evaluation-worker", daemon=True)
    thread.start()
    return thread, stop


def main() -> None:  # pragma: no cover - process entry point
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    def _handle(_signum, _frame):  # noqa: ANN001
        _stop_event.set()

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)
    loop()
    time.sleep(0.1)


if __name__ == "__main__":  # pragma: no cover
    main()
