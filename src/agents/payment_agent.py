"""
PaymentAgent — Handles payment.process events (confirmation/notification).

Payment recording is done in SalesService.finalize_order().
This agent acts as a confirmation agent: on payment.process it returns payment.completed
with payment details for downstream consumers (e.g. receipt, notifications).
"""

from typing import Optional
from src.agents.base import BaseAgent
from src.events.event import Event


class PaymentAgent(BaseAgent):
    """Confirmation agent for payment events."""

    name = "PaymentAgent"
    subscribes_to = ["payment.process"]
    publishes = ["payment.completed", "payment.failed", "payment.error"]
    writes_to_db = True
    uses_llm = False

    def handle(self, event: Event) -> Optional[Event]:
        """Route payment.process to handler."""
        if event.type != "payment.process":
            return None
        try:
            return self._handle_payment_process(event)
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

    def _handle_payment_process(self, event: Event) -> Event:
        """Confirm payment: extract details and emit payment.completed."""
        payload = event.payload or {}
        order_id = payload.get("order_id", "")
        payment_method = payload.get("payment_method", "CASH")
        amount = payload.get("amount", 0.0)

        return Event.create(
            type="payment.completed",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={
                "order_id": order_id,
                "payment_method": payment_method,
                "amount": amount,
            },
            user_id=event.user_id,
        )
