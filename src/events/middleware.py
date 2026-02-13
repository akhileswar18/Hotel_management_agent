"""
Event Middleware — Logging, timing, and error handling for the event bus.
"""

import time
import logging
from typing import Callable, Optional
from src.events.event import Event

logger = logging.getLogger("hms.events")


class TimingMiddleware:
    """Log event processing duration."""

    def __call__(self, event: Event, handler: Callable) -> Optional[Event]:
        start = time.perf_counter()
        try:
            result = handler(event)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug(f"[{event.type}] handled in {elapsed_ms:.1f}ms by handler")
            return result
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error(f"[{event.type}] FAILED after {elapsed_ms:.1f}ms: {e}")
            raise


class LoggingMiddleware:
    """Log all event dispatches."""

    def __call__(self, event: Event) -> None:
        logger.info(
            f"Event: {event.type} | source={event.source} | "
            f"correlation={event.correlation_id[:8]}... | "
            f"user={event.user_id or 'system'}"
        )


class ErrorCatchMiddleware:
    """Catch and log errors without crashing the bus."""

    def __call__(self, event: Event, handler: Callable) -> Optional[Event]:
        try:
            return handler(event)
        except Exception as e:
            logger.error(f"Agent error handling {event.type}: {e}")
            error_event = Event.create(
                type=f"{event.type.split('.')[0]}.error",
                source="ErrorCatchMiddleware",
                correlation_id=event.correlation_id,
                payload={"original_type": event.type, "error": str(e)},
                user_id=event.user_id,
            )
            return error_event
