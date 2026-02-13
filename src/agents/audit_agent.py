"""
AuditAgent — Universal event sink.

Subscribes to ALL events (wildcard *) and logs them to audit_log.
Append-only, never modifies data.
"""

import json
from typing import Optional
from uuid import UUID
from datetime import datetime
from src.agents.base import BaseAgent
from src.events.event import Event
from src.infrastructure import AuditLogRepository
from src.domain import AuditLogEntry


class AuditAgent(BaseAgent):
    """Event sink that logs all events to audit_log."""

    name = "AuditAgent"
    subscribes_to = ["*"]  # ALL events
    publishes = []         # Terminal sink
    writes_to_db = True    # Append-only writes
    uses_llm = False

    def __init__(self):
        self.audit_repo = AuditLogRepository()

    def handle(self, event: Event) -> Optional[Event]:
        """Log event to audit_log. Returns None (terminal sink)."""
        try:
            # Extract entity info from event type
            parts = event.type.split(".")
            entity_type = parts[0].title() if parts else "Unknown"
            operation = event.type

            entity_id = (
                event.payload.get("order_id")
                or event.payload.get("item_id")
                or event.payload.get("user_id")
                or event.payload.get("payment_id")
                or ""
            )

            entry = AuditLogEntry(
                id=UUID(event.id),
                entity_type=entity_type,
                entity_id=UUID(entity_id) if entity_id else UUID("00000000-0000-0000-0000-000000000000"),
                operation=operation,
                user_id=UUID(event.user_id) if event.user_id else UUID("00000000-0000-0000-0000-000000000000"),
                timestamp=datetime.fromisoformat(event.timestamp.replace("Z", "+00:00")),
                new_state=json.dumps(event.payload),
            )
            self.audit_repo.create(entry)
        except Exception:
            pass  # Audit failures must not crash the system
        
        return None  # Terminal sink — no response event
