"""
Event Model — Immutable event dataclass for agent communication.

Events are the fundamental unit of communication between agents.
They are immutable, JSON-serializable, and persisted to the event_log table.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4


@dataclass(frozen=True)
class Event:
    """Immutable event — the fundamental unit of agent communication."""
    id: str
    type: str               # Dot-notated: "domain.action" (e.g., "order.create")
    timestamp: str           # ISO 8601 UTC
    source: str              # Agent name or "API"
    correlation_id: str      # Groups related events in a workflow
    payload: Dict[str, Any]  # Event-specific data
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    reply_to: Optional[str] = None        # Event ID this is a reply to
    parent_event_id: Optional[str] = None  # Event ID that caused this event
    target_agent: Optional[str] = None     # Direct agent addressing (None = broadcast)

    @staticmethod
    def create(
        type: str,
        payload: Dict[str, Any],
        source: str = "API",
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        reply_to: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        target_agent: Optional[str] = None,
    ) -> "Event":
        """Factory method to create a new Event with auto-generated id and timestamp."""
        return Event(
            id=str(uuid4()),
            type=type,
            timestamp=datetime.utcnow().isoformat() + "Z",
            source=source,
            correlation_id=correlation_id or str(uuid4()),
            payload=payload,
            user_id=user_id,
            metadata=metadata or {},
            reply_to=reply_to,
            parent_event_id=parent_event_id,
            target_agent=target_agent,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @staticmethod
    def from_dict(data: dict) -> "Event":
        """Deserialize from dictionary."""
        return Event(
            id=data["id"],
            type=data["type"],
            timestamp=data["timestamp"],
            source=data["source"],
            correlation_id=data["correlation_id"],
            payload=data.get("payload", {}),
            user_id=data.get("user_id"),
            metadata=data.get("metadata", {}),
            reply_to=data.get("reply_to"),
            parent_event_id=data.get("parent_event_id"),
            target_agent=data.get("target_agent"),
        )

    @staticmethod
    def from_json(json_str: str) -> "Event":
        """Deserialize from JSON string."""
        return Event.from_dict(json.loads(json_str))


@dataclass
class EventResult:
    """Result of publishing an event (used for request-reply pattern)."""
    success: bool
    event: Optional[Event] = None    # Primary response event (first non-None)
    error: Optional[str] = None      # Error message if failed
    elapsed_ms: float = 0.0          # Processing time in milliseconds
    all_responses: list = field(default_factory=list)  # All handler responses
