from __future__ import annotations

import asyncio
import logging
import threading

from app.database import SessionLocal
from app.services.auto_discovery import run_due_users

logger = logging.getLogger("ai-lead-auto-discovery")


def auto_discovery_loop(stop_event: threading.Event, check_every: int = 60) -> None:
    """Alag thread -- email scheduler ko slow nahi karta."""
    logger.info("Auto-discovery loop started.")

    while not stop_event.is_set():
        db = SessionLocal()
        try:
            asyncio.run(run_due_users(db))
        except Exception:
            db.rollback()
            logger.exception("Auto-discovery cycle crashed.")
        finally:
            db.close()

        stop_event.wait(check_every)

    logger.info("Auto-discovery loop stopped.")