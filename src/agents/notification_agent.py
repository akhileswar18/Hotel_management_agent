"""
NotificationAgent — Terminal sink for notification events.

Stores notifications in-memory for UI polling via get_recent_notifications().
"""

from typing import Optional, List, Dict, Any
from collections import deque
from src.agents.base import BaseAgent
from src.events.event import Event


# Module-level store so the same agent instance is used when registered on app.state
_notifications: deque = deque(maxlen=100)


class NotificationAgent(BaseAgent):
    """In-memory notification sink for UI polling."""

    name = "NotificationAgent"
    subscribes_to = [
        "notification.toast",
        "notification.error",
        "inventory.low_stock",
        "inventory.out_of_stock",
    ]
    publishes = []
    writes_to_db = False
    uses_llm = False

    def __init__(self):
        self._store = _notifications

    def handle(self, event: Event) -> Optional[Event]:
        """Store notification and return None (terminal sink)."""
        handlers = {
            "notification.toast": self._handle_toast,
            "notification.error": self._handle_error,
            "inventory.low_stock": self._handle_low_stock,
            "inventory.out_of_stock": self._handle_out_of_stock,
        }
        handler = handlers.get(event.type)
        if handler:
            handler(event)
        return None

    def _handle_toast(self, event: Event) -> None:
        """Store toast message."""
        payload = event.payload or {}
        msg = payload.get("message_te") or payload.get("message", "")
        self._store.append({
            "type": "toast",
            "message": msg,
            "message_en": payload.get("message", msg),
            "timestamp": event.timestamp,
            "source": event.source,
        })

    def _handle_error(self, event: Event) -> None:
        """Store error with severity."""
        payload = event.payload or {}
        localized = payload.get("message_te") or payload.get("message", "")
        self._store.append({
            "type": "error",
            "message": localized,
            "message_en": payload.get("message", localized),
            "severity": payload.get("severity", "error"),
            "timestamp": event.timestamp,
            "source": event.source,
        })

    def _handle_low_stock(self, event: Event) -> None:
        """Store low stock alert."""
        payload = event.payload or {}
        localized = payload.get("message_te") or payload.get("message", "Low stock alert")
        self._store.append({
            "type": "low_stock",
            "message": localized,
            "message_en": payload.get("message", localized),
            "item_id": payload.get("item_id"),
            "item_name": payload.get("item_name"),
            "stock": payload.get("stock"),
            "reorder_level": payload.get("reorder_level"),
            "timestamp": event.timestamp,
            "source": event.source,
        })

    def _handle_out_of_stock(self, event: Event) -> None:
        """Store out-of-stock alert."""
        payload = event.payload or {}
        localized = payload.get("message_te") or payload.get("message", "Out of stock")
        self._store.append({
            "type": "out_of_stock",
            "message": localized,
            "message_en": payload.get("message", localized),
            "item_id": payload.get("item_id"),
            "item_name": payload.get("item_name"),
            "timestamp": event.timestamp,
            "source": event.source,
        })

    def get_recent_notifications(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return the most recent notifications for UI polling."""
        items = list(self._store)
        return items[-limit:] if limit else items
