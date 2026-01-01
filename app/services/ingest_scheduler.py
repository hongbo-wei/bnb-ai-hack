import logging
import threading
import time

from sqlalchemy.orm import Session

from app.config import INGEST_INTERVAL_SEC, INGEST_WALLET
from app.services.mcp_orchestrator import MCPOrchestrator

logger = logging.getLogger(__name__)


class IngestScheduler:
    def __init__(self, db_factory, interval_sec: int = INGEST_INTERVAL_SEC) -> None:
        self.db_factory = db_factory
        self.interval_sec = interval_sec
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Ingest scheduler started (interval=%ss)", self.interval_sec)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Ingest scheduler stopped")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._tick()
            self._stop_event.wait(self.interval_sec)

    def _tick(self) -> None:
        if not INGEST_WALLET:
            logger.warning("INGEST_WALLET not set; skipping ingestion")
            return
        db: Session = self.db_factory()
        try:
            orchestrator = MCPOrchestrator(db)
            result = orchestrator.ingest_wallet(INGEST_WALLET)
            logger.info("Ingested %s events for %s", result.get("count"), INGEST_WALLET)
        except Exception as exc:
            logger.warning("Ingest scheduler error: %s", exc)
        finally:
            db.close()
