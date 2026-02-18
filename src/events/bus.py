"""
EventBus — In-process event bus for agent communication.

Provides:
- publish_sync(): Dispatch to all handlers with middleware pipeline
- publish(): Async fire-and-forget
- publish_and_wait(): Async request-reply (blocks until response)
- subscribe(): Register handler for event type (supports wildcards)
- Auto re-dispatch of result events (e.g. order.finalized → InventoryAgent)
- Dead letter queue with configurable retry
- Middleware pipeline (logging, timing, error-catch)
- AgentRegistry integration for subscription management
- Multi-response collection from all handlers
"""

import logging
import time
from typing import Callable, Dict, List, Optional, Any, Set
from src.events.event import Event, EventResult
from src.events.store import EventStore

logger = logging.getLogger("hms.events")

# Result event types that should be auto re-dispatched to trigger downstream agents
# Note: order.created is NOT here — no downstream agent needs it; only noise.
AUTO_REDISPATCH_TYPES: Set[str] = {
    "order.finalized",
    "order.voided",
    "payment.completed",
    "payment.failed",
    "inventory.low_stock",
    "inventory.out_of_stock",
}

# Max re-dispatch depth to prevent infinite loops
MAX_REDISPATCH_DEPTH = 3


class DeadLetterEntry:
    """An event that failed processing, with retry metadata."""

    def __init__(self, event: Event, error: str, handler_name: str = ""):
        self.event = event
        self.error = error
        self.handler_name = handler_name
        self.attempts = 1
        self.max_retries = 3
        self.last_attempt = time.time()

    @property
    def can_retry(self) -> bool:
        return self.attempts < self.max_retries

    def backoff_seconds(self) -> float:
        """Exponential backoff: 1s, 2s, 4s."""
        return 2 ** (self.attempts - 1)


class EventBus:
    """Central in-process event bus for agent communication."""

    def __init__(self, store: Optional[EventStore] = None):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._handler_names: Dict[int, str] = {}  # handler id → name for debugging
        self._store = store or EventStore()
        self._middleware: List[Callable] = []
        self.dead_letter: List[DeadLetterEntry] = []
        self._registry = None  # Optional AgentRegistry
        self._redispatch_depth = 0  # Guard against infinite loops

    def set_registry(self, registry) -> None:
        """Integrate an AgentRegistry for subscription management."""
        self._registry = registry

    def subscribe(self, event_type: str, handler: Callable, name: str = "") -> None:
        """Register a handler for an event type. Supports wildcards (*).

        Args:
            event_type: Event type pattern (exact, prefix.*, or * for all)
            handler: Callable that takes an Event and returns Optional[Event]
            name: Optional handler name for debugging/logging
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        if name:
            self._handler_names[id(handler)] = name

    def _get_handlers(self, event: Event) -> List[Callable]:
        """Get all handlers matching an event type, respecting target_agent."""
        event_type = event.type
        handlers = []

        # If event targets a specific agent and we have a registry, route directly
        if event.target_agent and self._registry:
            agent = self._registry.get_agent(event.target_agent)
            if agent and agent.can_handle(event_type):
                handlers.append(agent.handle)
                return handlers

        # Exact match
        if event_type in self._subscribers:
            handlers.extend(self._subscribers[event_type])

        # Wildcard matches (prefix.*)
        parts = event_type.split(".")
        if len(parts) >= 2:
            prefix_wild = parts[0] + ".*"
            if prefix_wild in self._subscribers:
                handlers.extend(self._subscribers[prefix_wild])

        # Global wildcard (*)
        if "*" in self._subscribers:
            handlers.extend(self._subscribers["*"])

        return handlers

    def _get_handler_name(self, handler: Callable) -> str:
        """Get a human-readable name for a handler."""
        if id(handler) in self._handler_names:
            return self._handler_names[id(handler)]
        if hasattr(handler, "__self__"):
            return f"{handler.__self__.__class__.__name__}.{handler.__name__}"
        return getattr(handler, "__qualname__", str(handler))

    def _run_middleware(self, event: Event, handler: Callable) -> Optional[Event]:
        """Run handler through the middleware pipeline.

        Middleware wraps handler execution: timing, logging, error-catching.
        Each middleware is a callable(event, next_handler) -> Optional[Event].
        """
        if not self._middleware:
            return handler(event)

        # Build middleware chain (innermost = actual handler)
        def build_chain(mw_list, final_handler):
            if not mw_list:
                return final_handler
            current_mw = mw_list[0]
            rest_handler = build_chain(mw_list[1:], final_handler)
            return lambda evt: current_mw(evt, rest_handler)

        chain = build_chain(self._middleware, handler)
        return chain(event)

    def publish_sync(self, event: Event, _depth: int = 0) -> EventResult:
        """Synchronous publish — dispatch to all handlers, collect all responses.

        Features:
        - Runs middleware pipeline around each handler
        - Collects ALL handler responses (primary = first non-None)
        - Auto re-dispatches result events (e.g. order.finalized) to trigger downstream
        - Failed events go to dead letter queue
        - Respects target_agent for direct addressing
        """
        start = time.perf_counter()

        # Log event dispatch
        logger.info(
            f"[EventBus] {event.type} | source={event.source} | "
            f"corr={event.correlation_id[:8]}... | "
            f"user={event.user_id or 'system'}"
            + (f" | target={event.target_agent}" if event.target_agent else "")
        )

        # Persist event to store
        try:
            self._store.append(event)
        except Exception as e:
            logger.warning(f"[EventBus] Failed to persist event {event.id}: {e}")

        handlers = self._get_handlers(event)
        if not handlers:
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug(f"[EventBus] No handlers for {event.type}")
            return EventResult(success=False, error=f"No handlers for {event.type}",
                               elapsed_ms=elapsed)

        primary_response = None
        all_responses = []
        errors = []

        for handler in handlers:
            handler_name = self._get_handler_name(handler)
            try:
                response = self._run_middleware(event, handler)
                if response is not None:
                    all_responses.append(response)
                    if primary_response is None:
                        primary_response = response
                    # Persist response event
                    try:
                        self._store.append(response)
                    except Exception:
                        pass
            except Exception as e:
                error_msg = f"{handler_name}: {e}"
                errors.append(error_msg)
                logger.error(f"[EventBus] Handler {handler_name} failed on {event.type}: {e}")
                self.dead_letter.append(
                    DeadLetterEntry(event=event, error=str(e), handler_name=handler_name)
                )

        elapsed = (time.perf_counter() - start) * 1000

        # Auto re-dispatch result events to trigger downstream agents
        if primary_response and _depth < MAX_REDISPATCH_DEPTH:
            if primary_response.type in AUTO_REDISPATCH_TYPES:
                logger.debug(
                    f"[EventBus] Auto re-dispatching {primary_response.type} "
                    f"(depth={_depth + 1})"
                )
                self.publish_sync(primary_response, _depth=_depth + 1)

        if errors and primary_response is None:
            return EventResult(
                success=False,
                error="; ".join(errors),
                elapsed_ms=elapsed,
                all_responses=all_responses,
            )

        return EventResult(
            success=True,
            event=primary_response,
            elapsed_ms=elapsed,
            all_responses=all_responses,
        )

    async def publish(self, event: Event) -> None:
        """Async fire-and-forget: dispatch to all subscribers."""
        self.publish_sync(event)

    async def publish_and_wait(self, event: Event, timeout: float = 5.0) -> EventResult:
        """Async request-reply: dispatch and return result."""
        return self.publish_sync(event)

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to the pipeline.

        Middleware signature: (event: Event, next_handler: Callable) -> Optional[Event]
        """
        self._middleware.append(middleware)

    def retry_dead_letters(self) -> Dict[str, Any]:
        """Process dead letter queue — retry failed events with backoff.

        Returns summary of retry results.
        """
        if not self.dead_letter:
            return {"retried": 0, "succeeded": 0, "exhausted": 0}

        now = time.time()
        retried = 0
        succeeded = 0
        exhausted = 0
        remaining = []

        for entry in self.dead_letter:
            if not entry.can_retry:
                exhausted += 1
                logger.warning(
                    f"[DeadLetter] Exhausted retries for {entry.event.type} "
                    f"(handler={entry.handler_name}, error={entry.error})"
                )
                continue

            backoff = entry.backoff_seconds()
            if now - entry.last_attempt < backoff:
                remaining.append(entry)
                continue

            # Retry
            entry.attempts += 1
            entry.last_attempt = now
            retried += 1
            logger.info(
                f"[DeadLetter] Retrying {entry.event.type} "
                f"(attempt {entry.attempts}/{entry.max_retries})"
            )

            result = self.publish_sync(entry.event)
            if result.success:
                succeeded += 1
            else:
                remaining.append(entry)

        self.dead_letter = remaining

        summary = {
            "retried": retried,
            "succeeded": succeeded,
            "exhausted": exhausted,
            "remaining": len(remaining),
        }
        if retried > 0:
            logger.info(f"[DeadLetter] Retry summary: {summary}")
        return summary

    @property
    def subscriber_count(self) -> int:
        """Total number of subscriptions."""
        return sum(len(handlers) for handlers in self._subscribers.values())

    @property
    def dead_letter_count(self) -> int:
        """Number of events in dead letter queue."""
        return len(self.dead_letter)
