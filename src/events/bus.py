"""
EventBus — In-process async event bus using Python asyncio.

Provides:
- publish(): Fire-and-forget dispatch to all subscribers
- publish_and_wait(): Request-reply pattern (blocks until response)
- subscribe(): Register handler for event type (supports wildcards)
"""

import asyncio
import time
from typing import Callable, Dict, List, Optional, Any
from src.events.event import Event, EventResult
from src.events.store import EventStore


class EventBus:
    """Central in-process event bus for agent communication."""

    def __init__(self, store: Optional[EventStore] = None):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._store = store or EventStore()
        self._middleware: List[Callable] = []
        self.dead_letter: List[Event] = []

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Register a handler for an event type. Supports wildcards (*).

        Examples:
            bus.subscribe("order.create", handler)   # Exact match
            bus.subscribe("order.*", handler)         # Prefix wildcard
            bus.subscribe("*", handler)               # All events
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def _get_handlers(self, event_type: str) -> List[Callable]:
        """Get all handlers matching an event type (including wildcards)."""
        handlers = []

        # Exact match
        if event_type in self._subscribers:
            handlers.extend(self._subscribers[event_type])

        # Wildcard matches
        parts = event_type.split(".")
        if len(parts) >= 2:
            prefix_wild = parts[0] + ".*"
            if prefix_wild in self._subscribers:
                handlers.extend(self._subscribers[prefix_wild])

        # Global wildcard
        if "*" in self._subscribers:
            handlers.extend(self._subscribers["*"])

        return handlers

    def publish_sync(self, event: Event) -> Optional[EventResult]:
        """Synchronous publish — dispatch to all handlers, return first response.

        This is the primary dispatch method for non-async contexts (e.g., FastAPI sync routes).
        """
        start = time.perf_counter()

        # Persist event
        try:
            self._store.append(event)
        except Exception:
            pass

        handlers = self._get_handlers(event.type)
        if not handlers:
            return EventResult(success=False, error=f"No handlers for {event.type}")

        result_event = None
        for handler in handlers:
            try:
                response = handler(event)
                if response is not None and result_event is None:
                    result_event = response
                    # Persist response event
                    try:
                        self._store.append(response)
                    except Exception:
                        pass
            except Exception as e:
                self.dead_letter.append(event)
                if result_event is None:
                    elapsed = (time.perf_counter() - start) * 1000
                    return EventResult(success=False, error=str(e), elapsed_ms=elapsed)

        elapsed = (time.perf_counter() - start) * 1000
        if result_event:
            return EventResult(success=True, event=result_event, elapsed_ms=elapsed)
        return EventResult(success=True, elapsed_ms=elapsed)

    async def publish(self, event: Event) -> None:
        """Async fire-and-forget: dispatch to all subscribers."""
        self.publish_sync(event)

    async def publish_and_wait(self, event: Event, timeout: float = 5.0) -> EventResult:
        """Async request-reply: dispatch and return result."""
        return self.publish_sync(event)

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware for pre/post processing."""
        self._middleware.append(middleware)

    @property
    def subscriber_count(self) -> int:
        """Total number of subscriptions."""
        return sum(len(handlers) for handlers in self._subscribers.values())
