"""
InventoryAgent — Handles inventory-related events and stock alerts.

Delegates to InventoryService for stock/item operations.
Listens to order.finalized and order.voided to CHECK stock levels and publish
low_stock/out_of_stock alerts (does NOT deduct stock — SalesService does that).
Rule-based, deterministic, writes to DB.
"""

from typing import Optional, Any
from uuid import UUID

from src.agents.base import BaseAgent
from src.events.event import Event
from src.events.bus import EventBus
from src.application.services import InventoryService


class InventoryAgent(BaseAgent):
    """Rule-based inventory management agent."""

    name = "InventoryAgent"
    subscribes_to = [
        "inventory.stock_in",
        "inventory.adjust",
        "inventory.archive",
        "inventory.update",
        "order.finalized",
        "order.voided",
    ]
    publishes = [
        "inventory.stocked_in",
        "inventory.adjusted",
        "inventory.archived",
        "inventory.updated",
        "inventory.low_stock",
        "inventory.out_of_stock",
        "inventory.error",
    ]
    writes_to_db = True
    uses_llm = False

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.inventory_service = InventoryService()
        self._event_bus = event_bus

    def handle(self, event: Event) -> Optional[Event]:
        """Route event to appropriate handler method."""
        handlers = {
            "inventory.stock_in": self._handle_stock_in,
            "inventory.adjust": self._handle_adjust,
            "inventory.archive": self._handle_archive,
            "inventory.update": self._handle_update,
            "order.finalized": self._handle_order_finalized,
            "order.voided": self._handle_order_voided,
        }
        handler = handlers.get(event.type)
        if handler:
            try:
                return handler(event)
            except Exception as e:
                return Event.create(
                    type="inventory.error",
                    source=self.name,
                    correlation_id=event.correlation_id,
                    payload={
                        "error_code": type(e).__name__,
                        "message": str(e),
                        "original_event_type": event.type,
                    },
                    user_id=event.user_id,
                )
        return None

    def _handle_stock_in(self, event: Event) -> Event:
        payload = event.payload
        item_id = UUID(payload["item_id"])
        user_id = self._user_id_from_event(event)
        entry = self.inventory_service.record_stock_in(
            item_id=item_id,
            quantity=int(payload["quantity"]),
            reference=payload.get("reference", ""),
            recorded_by=user_id,
        )
        stock_on_hand = self.inventory_service.get_stock_on_hand(item_id)
        out = Event.create(
            type="inventory.stocked_in",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={
                "id": str(entry.id),
                "item_id": str(entry.item_id),
                "quantity_change": entry.quantity_change,
                "reason": entry.reason,
                "transaction_type": entry.transaction_type.value,
                "stock_on_hand": stock_on_hand,
            },
            user_id=event.user_id,
        )
        self._check_stock_alerts(item_id, event.correlation_id, event.user_id)
        return out

    def _handle_adjust(self, event: Event) -> Event:
        payload = event.payload
        item_id = UUID(payload["item_id"])
        user_id = self._user_id_from_event(event)
        entry = self.inventory_service.record_adjustment(
            item_id=item_id,
            quantity_change=int(payload["quantity_change"]),
            reason=payload.get("reason", ""),
            adjusted_by=user_id,
        )
        stock_on_hand = self.inventory_service.get_stock_on_hand(item_id)
        out = Event.create(
            type="inventory.adjusted",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={
                "id": str(entry.id),
                "item_id": str(entry.item_id),
                "quantity_change": entry.quantity_change,
                "reason": entry.reason,
                "transaction_type": entry.transaction_type.value,
                "stock_on_hand": stock_on_hand,
            },
            user_id=event.user_id,
        )
        self._check_stock_alerts(item_id, event.correlation_id, event.user_id)
        return out

    def _handle_archive(self, event: Event) -> Event:
        payload = event.payload
        item_id = payload["item_id"]
        user_id = event.user_id or ""
        item = self.inventory_service.item_repo.get(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")
        self.inventory_service.item_repo.archive_item(item_id, user_id)
        return Event.create(
            type="inventory.archived",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={"status": "archived", "item_id": item_id, "name": item.name},
            user_id=event.user_id,
        )

    def _handle_update(self, event: Event) -> Event:
        from src.domain import Money

        payload = event.payload
        item_id = UUID(payload["item_id"])
        user_id = self._user_id_from_event(event)
        unit_price = None
        if payload.get("unit_price") is not None:
            unit_price = Money.from_float(float(payload["unit_price"]))
        reorder_level = payload.get("reorder_level")
        item = self.inventory_service.update_item(
            item_id=item_id,
            updated_by=user_id,
            unit_price=unit_price,
            reorder_level=reorder_level,
        )
        stock_on_hand = self.inventory_service.get_stock_on_hand(item_id)
        out = Event.create(
            type="inventory.updated",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={
                "id": str(item.id),
                "name": item.name,
                "category": item.category,
                "unit_price": item.unit_price.to_float(),
                "reorder_level": item.reorder_level,
                "stock_on_hand": stock_on_hand,
            },
            user_id=event.user_id,
        )
        self._check_stock_alerts(item_id, event.correlation_id, event.user_id)
        return out

    def _handle_order_finalized(self, event: Event) -> None:
        """Check stock levels for all line items; publish low_stock/out_of_stock as needed."""
        for li in event.payload.get("line_items", []):
            item_id_str = li.get("item_id")
            if item_id_str:
                try:
                    self._check_stock_alerts(
                        UUID(item_id_str), event.correlation_id, event.user_id
                    )
                except Exception:
                    pass
        return None

    def _handle_order_voided(self, event: Event) -> None:
        """Check stock levels after void (reversal already done by SalesService)."""
        for li in event.payload.get("line_items", []):
            item_id_str = li.get("item_id")
            if item_id_str:
                try:
                    self._check_stock_alerts(
                        UUID(item_id_str), event.correlation_id, event.user_id
                    )
                except Exception:
                    pass
        return None

    def _check_stock_alerts(
        self, item_id: UUID, correlation_id: Optional[str], user_id: Optional[str]
    ) -> None:
        """Check stock vs reorder_level; publish inventory.low_stock or inventory.out_of_stock."""
        if not self._event_bus:
            return
        item = self.inventory_service.item_repo.get(str(item_id))
        if not item:
            return
        stock = self.inventory_service.get_stock_on_hand(item_id)
        if stock <= 0:
            alert = Event.create(
                type="inventory.out_of_stock",
                source=self.name,
                correlation_id=correlation_id,
                payload={
                    "item_id": str(item_id),
                    "item_name": item.name,
                    "stock_on_hand": 0,
                    "reorder_level": item.reorder_level,
                },
                user_id=user_id,
            )
            self._event_bus.publish_sync(alert)
        elif stock < item.reorder_level:
            alert = Event.create(
                type="inventory.low_stock",
                source=self.name,
                correlation_id=correlation_id,
                payload={
                    "item_id": str(item_id),
                    "item_name": item.name,
                    "stock_on_hand": stock,
                    "reorder_level": item.reorder_level,
                },
                user_id=user_id,
            )
            self._event_bus.publish_sync(alert)

    @staticmethod
    def _user_id_from_event(event: Event) -> UUID:
        default = UUID("00000000-0000-0000-0000-000000000000")
        if event.user_id:
            try:
                return UUID(event.user_id)
            except (ValueError, TypeError):
                pass
        return default
