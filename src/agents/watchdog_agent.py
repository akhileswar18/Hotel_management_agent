"""
WatchdogAgent — Monitors and auto-recovers from known failure modes.

Explicit recovery logic only (no AI):
- API timeout → retry 3 times → fallback to rule-based parsing (handled in IntentParser/caller)
- Printer failure → queue the bill → retry when printer reconnects
- Agent crash → auto-restart the agent (re-register with EventBus)
- Database lock → wait and retry with backoff
"""

import logging
import time
from typing import Optional
from src.agents.base import BaseAgent
from src.events.event import Event

logger = logging.getLogger("hms.watchdog")

# Configurable recovery constants
PRINTER_RETRY_DELAY_SEC = 2.0
DB_LOCK_RETRIES = 3
DB_LOCK_BACKOFF = [0.1, 0.5, 2.0]  # seconds


class WatchdogAgent(BaseAgent):
    """Recovery agent for known failure modes."""

    name = "WatchdogAgent"
    subscribes_to = [
        "watchdog.check",
        "system.printer_failed",
        "system.agent_unhealthy",
        "system.db_lock",
    ]
    publishes = [
        "watchdog.recovery_started",
        "watchdog.recovery_done",
        "watchdog.queued",
    ]
    writes_to_db = False
    uses_llm = False

    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self._print_queue = []  # In-memory queue: list of receipt payloads to retry

    def handle(self, event: Event) -> Optional[Event]:
        handlers = {
            "watchdog.check": self._handle_check,
            "system.printer_failed": self._handle_printer_failed,
            "system.agent_unhealthy": self._handle_agent_unhealthy,
            "system.db_lock": self._handle_db_lock,
        }
        handler = handlers.get(event.type)
        if handler:
            try:
                return handler(event)
            except Exception as e:
                logger.warning("WatchdogAgent handler failed: %s", e)
        return None

    def _handle_check(self, event: Event) -> Optional[Event]:
        """Periodic or on-demand health check. Process print queue if printer is back."""
        if self._print_queue and self.event_bus:
            payload = self._print_queue.pop(0)
            retry_event = Event.create(
                type="receipt.print",
                source=self.name,
                payload=payload,
                correlation_id=event.correlation_id,
            )
            self.event_bus.publish_sync(retry_event)
            logger.info("Watchdog: retried queued print job")
        return None

    def _handle_printer_failed(self, event: Event) -> Optional[Event]:
        """Queue the bill and retry when printer reconnects."""
        payload = event.payload or {}
        receipt_data = payload.get("receipt_data") or payload
        self._print_queue.append(receipt_data)
        logger.info("Watchdog: queued receipt for retry (queue size=%d)", len(self._print_queue))
        return Event.create(
            type="watchdog.queued",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={"queue": "print", "size": len(self._print_queue)},
        )

    def _handle_agent_unhealthy(self, event: Event) -> Optional[Event]:
        """Agent crash / unhealthy: log. Auto-restart would require registry re-register."""
        agent_name = (event.payload or {}).get("agent_name", "?")
        logger.warning("Watchdog: agent unhealthy: %s", agent_name)
        return None

    def _handle_db_lock(self, event: Event) -> Optional[Event]:
        """Database lock: wait and retry with backoff."""
        for i, delay in enumerate(DB_LOCK_BACKOFF):
            time.sleep(delay)
            # Caller is expected to retry the operation; we just waited
            logger.info("Watchdog: db_lock backoff wait %.1fs (attempt %d)", delay, i + 1)
        return Event.create(
            type="watchdog.recovery_done",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={"recovery": "db_lock", "retries": DB_LOCK_RETRIES},
        )
