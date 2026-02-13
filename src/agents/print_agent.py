"""
PrintAgent — Handles receipt.print, receipt.email, receipt.reprint.

Uses ESCPOSPrinter and ReceiptEmailSender. Errors are non-fatal (degradable).
"""

from typing import Optional
from src.agents.base import BaseAgent
from src.events.event import Event
from src.infrastructure.printer import ESCPOSPrinter
from src.infrastructure.email_sender import ReceiptEmailSender


class PrintAgent(BaseAgent):
    """Receipt print and email agent."""

    name = "PrintAgent"
    subscribes_to = ["receipt.print", "receipt.email", "receipt.reprint"]
    publishes = ["receipt.printed", "receipt.emailed", "receipt.error"]
    writes_to_db = False
    uses_llm = False
    degradable = True

    def __init__(self):
        self.printer = ESCPOSPrinter()
        self.email_sender = ReceiptEmailSender()

    def handle(self, event: Event) -> Optional[Event]:
        """Route receipt events to handlers."""
        handlers = {
            "receipt.print": self._handle_print,
            "receipt.email": self._handle_email,
            "receipt.reprint": self._handle_reprint,
        }
        handler = handlers.get(event.type)
        if handler:
            try:
                return handler(event)
            except Exception as e:
                return Event.create(
                    type="receipt.error",
                    source=self.name,
                    correlation_id=event.correlation_id,
                    payload={
                        "error_code": type(e).__name__,
                        "message": str(e),
                    },
                    user_id=event.user_id,
                )
        return None

    def _handle_print(self, event: Event) -> Event:
        """Print receipt via ESCPOSPrinter. Payload has order data."""
        order_data = event.payload or {}
        filepath = self.printer.print_receipt(order_data)
        return Event.create(
            type="receipt.printed",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={
                "order_id": order_data.get("order_id"),
                "receipt_number": order_data.get("receipt_number"),
                "filepath": filepath,
            },
            user_id=event.user_id,
        )

    def _handle_email(self, event: Event) -> Event:
        """Email receipt via ReceiptEmailSender. Payload has order data + email."""
        payload = event.payload or {}
        order_data = {k: v for k, v in payload.items() if k != "email"}
        to_email = payload.get("email", "").strip()
        if not to_email:
            raise ValueError("Email address is required")
        self.email_sender.send_receipt(to_email, order_data)
        return Event.create(
            type="receipt.emailed",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={
                "order_id": order_data.get("order_id"),
                "receipt_number": order_data.get("receipt_number"),
                "to_email": to_email,
            },
            user_id=event.user_id,
        )

    def _handle_reprint(self, event: Event) -> Event:
        """Reprint: same as print."""
        return self._handle_print(event)
