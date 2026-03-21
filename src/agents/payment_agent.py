"""
PaymentAgent — Handles payment confirmation events.

Payment recording is done in SalesService.finalize_order().
This agent acts as a confirmation agent:
- On order.finalized → emits payment.completed (auto-triggered via EventBus re-dispatch)
- On payment.process → emits payment.completed (explicit payment request)

This ensures PaymentAgent is always wired into the finalize flow regardless
of whether the order was finalized via API, Orchestrator, or Command mode.
"""

from typing import Optional
from src.agents.base import BaseAgent
from src.events.event import Event


class PaymentAgent(BaseAgent):
    """Confirmation agent for payment events."""

    name = "PaymentAgent"
    subscribes_to = ["payment.process", "order.finalized"]
    publishes = ["payment.completed", "payment.failed", "payment.error"]
    writes_to_db = True  # Finalization flow persists payment records
    uses_llm = False

    def handle(self, event: Event) -> Optional[Event]:
        """Route events to handler."""
        try:
            if event.type == "order.finalized":
                return self._handle_order_finalized(event)
            elif event.type == "payment.process":
                return self._handle_payment_process(event)
            return None
        except Exception as e:
            return Event.create(
                type="payment.error",
                source=self.name,
                correlation_id=event.correlation_id,
                payload={
                    "order_id": event.payload.get("order_id", ""),
                    "error_code": type(e).__name__,
                    "message": str(e),
                },
                user_id=event.user_id,
            )

    def _handle_order_finalized(self, event: Event) -> Event:
        """React to order.finalized — emit payment.completed for downstream consumers."""
        payload = event.payload or {}
        return Event.create(
            type="payment.completed",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={
                "order_id": payload.get("order_id", ""),
                "payment_method": payload.get("payment_method", "CASH"),
                "amount": payload.get("total_amount", 0.0),
                "receipt_number": payload.get("receipt_number", ""),
            },
            user_id=event.user_id,
            parent_event_id=event.id,
        )

    def _handle_payment_process(self, event: Event) -> Event:
        """Explicit payment request — emit payment.completed."""
        payload = event.payload or {}
        return Event.create(
            type="payment.completed",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={
                "order_id": payload.get("order_id", ""),
                "payment_method": payload.get("payment_method", "CASH"),
                "amount": payload.get("amount", 0.0),
            },
            user_id=event.user_id,
            parent_event_id=event.id,
        )
