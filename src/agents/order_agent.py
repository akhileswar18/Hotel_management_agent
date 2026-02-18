"""
OrderAgent — Handles all order-related events.

Delegates to existing SalesService for actual business logic.
Rule-based, deterministic, writes to DB.
"""

from typing import Optional
from uuid import UUID
from src.agents.base import BaseAgent
from src.events.event import Event
from src.application.services import SalesService


class OrderAgent(BaseAgent):
    """Rule-based order management agent."""

    name = "OrderAgent"
    subscribes_to = [
        "order.create", "order.add_item", "order.remove_item",
        "order.edit_qty", "order.discount", "order.finalize",
        "order.void", "order.hold", "order.resume",
    ]
    publishes = [
        "order.created", "order.updated", "order.finalized",
        "order.voided", "order.held", "order.resumed", "order.error",
    ]
    writes_to_db = True
    uses_llm = False

    def __init__(self):
        self.sales_service = SalesService()

    def handle(self, event: Event) -> Optional[Event]:
        """Route event to appropriate handler method."""
        handlers = {
            "order.create": self._handle_create,
            "order.add_item": self._handle_add_item,
            "order.remove_item": self._handle_remove_item,
            "order.edit_qty": self._handle_edit_qty,
            "order.discount": self._handle_discount,
            "order.finalize": self._handle_finalize,
            "order.void": self._handle_void,
            "order.hold": self._handle_hold,
            "order.resume": self._handle_resume,
        }
        handler = handlers.get(event.type)
        if handler:
            try:
                return handler(event)
            except Exception as e:
                return Event.create(
                    type="order.error",
                    source=self.name,
                    correlation_id=event.correlation_id,
                    payload={
                        "order_id": event.payload.get("order_id", ""),
                        "error_code": type(e).__name__,
                        "message": str(e),
                    },
                    user_id=event.user_id,
                )
        return None

    def _handle_create(self, event: Event) -> Event:
        table_id = event.payload.get("table_id", "1")
        # Prefer event.user_id (set by the original API request), fallback to payload
        user_id = event.user_id or event.payload.get("user_id", "")
        order = self.sales_service.create_order(
            table_id=table_id,
            created_by=UUID(user_id) if user_id else UUID("00000000-0000-0000-0000-000000000000"),
        )
        return Event.create(
            type="order.created",
            source=self.name,
            correlation_id=event.correlation_id,
            payload=self._order_to_payload(order),
            user_id=event.user_id,
        )

    def _handle_add_item(self, event: Event) -> Event:
        order = self.sales_service.add_item(
            order_id=UUID(event.payload["order_id"]),
            item_id=UUID(event.payload["item_id"]),
            quantity=event.payload.get("quantity", 1),
            added_by=UUID(event.user_id) if event.user_id else UUID("00000000-0000-0000-0000-000000000000"),
        )
        return Event.create(
            type="order.updated",
            source=self.name,
            correlation_id=event.correlation_id,
            payload=self._order_to_payload(order),
            user_id=event.user_id,
        )

    def _handle_remove_item(self, event: Event) -> Event:
        order = self.sales_service.remove_item(
            order_id=UUID(event.payload["order_id"]),
            line_item_id=UUID(event.payload["line_item_id"]),
            user_id=UUID(event.user_id) if event.user_id else UUID("00000000-0000-0000-0000-000000000000"),
        )
        return Event.create(
            type="order.updated",
            source=self.name,
            correlation_id=event.correlation_id,
            payload=self._order_to_payload(order),
            user_id=event.user_id,
        )

    def _handle_edit_qty(self, event: Event) -> Event:
        order = self.sales_service.update_item_quantity(
            order_id=UUID(event.payload["order_id"]),
            line_item_id=UUID(event.payload["line_item_id"]),
            new_quantity=event.payload["new_qty"],
            user_id=UUID(event.user_id) if event.user_id else UUID("00000000-0000-0000-0000-000000000000"),
        )
        return Event.create(
            type="order.updated",
            source=self.name,
            correlation_id=event.correlation_id,
            payload=self._order_to_payload(order),
            user_id=event.user_id,
        )

    def _handle_discount(self, event: Event) -> Event:
        order = self.sales_service.apply_order_discount(
            order_id=UUID(event.payload["order_id"]),
            discount_type=event.payload.get("discount_type", "percentage"),
            amount=float(event.payload.get("discount_value", 0)),
            applied_by=UUID(event.user_id) if event.user_id else UUID("00000000-0000-0000-0000-000000000000"),
        )
        return Event.create(
            type="order.updated",
            source=self.name,
            correlation_id=event.correlation_id,
            payload=self._order_to_payload(order),
            user_id=event.user_id,
        )

    def _handle_finalize(self, event: Event) -> Event:
        from src.domain.value_objects import PaymentMethod, Money
        order = self.sales_service.finalize_order(
            order_id=UUID(event.payload["order_id"]),
            payment_method=PaymentMethod(event.payload.get("payment_method", "CASH")),
            paid_amount=Money.from_float(float(event.payload.get("amount_tendered", 0))),
            finalized_by=UUID(event.user_id) if event.user_id else UUID("00000000-0000-0000-0000-000000000000"),
        )
        return Event.create(
            type="order.finalized",
            source=self.name,
            correlation_id=event.correlation_id,
            payload=self._order_to_payload(order),
            user_id=event.user_id,
        )

    def _handle_void(self, event: Event) -> Event:
        order = self.sales_service.void_order(
            order_id=UUID(event.payload["order_id"]),
            reason=event.payload.get("reason", ""),
            voided_by=UUID(event.user_id) if event.user_id else UUID("00000000-0000-0000-0000-000000000000"),
        )
        return Event.create(
            type="order.voided",
            source=self.name,
            correlation_id=event.correlation_id,
            payload=self._order_to_payload(order),
            user_id=event.user_id,
        )

    def _handle_hold(self, event: Event) -> Event:
        order = self.sales_service.hold_order(
            order_id=UUID(event.payload["order_id"]),
            user_id=UUID(event.user_id) if event.user_id else UUID("00000000-0000-0000-0000-000000000000"),
        )
        return Event.create(
            type="order.held",
            source=self.name,
            correlation_id=event.correlation_id,
            payload=self._order_to_payload(order),
            user_id=event.user_id,
        )

    def _handle_resume(self, event: Event) -> Event:
        order = self.sales_service.resume_order(
            order_id=UUID(event.payload["order_id"]),
            user_id=UUID(event.user_id) if event.user_id else UUID("00000000-0000-0000-0000-000000000000"),
        )
        return Event.create(
            type="order.resumed",
            source=self.name,
            correlation_id=event.correlation_id,
            payload=self._order_to_payload(order),
            user_id=event.user_id,
        )

    @staticmethod
    def _order_to_payload(order) -> dict:
        """Convert an Order entity to a dict payload."""
        return {
            "order_id": str(order.id),
            "table_id": order.table_id or "",
            "status": order.status.value,
            "subtotal": order.subtotal.cents / 100.0 if hasattr(order.subtotal, 'cents') else 0,
            "discount_amount": order.discount_amount.cents / 100.0 if hasattr(order.discount_amount, 'cents') else 0,
            "tax_amount": order.tax_amount.cents / 100.0 if hasattr(order.tax_amount, 'cents') else 0,
            "total_amount": order.total_amount.cents / 100.0 if hasattr(order.total_amount, 'cents') else 0,
            "receipt_number": getattr(order, 'receipt_number', '') or '',
            "finalized_at": order.finalized_at.isoformat() if getattr(order, 'finalized_at', None) else None,
            "line_items": [
                {
                    "id": str(li.id),
                    "item_id": str(li.item_id),
                    "item_name": li.item_name,
                    "quantity": li.quantity,
                    "unit_price": li.unit_price.cents / 100.0,
                    "total_amount": li.total_amount.cents / 100.0,
                }
                for li in (order.line_items or [])
            ],
        }
