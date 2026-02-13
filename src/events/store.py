"""
EventStore — Append-only event persistence backed by SQLite.

Stores all events for auditing, debugging, and replay.
"""

import json
from typing import List, Optional
from src.infrastructure.database import Database


class EventStore:
    """Append-only event log backed by SQLite event_log table."""

    def __init__(self):
        self.db = Database()

    def append(self, event) -> None:
        """Persist event to event_log table."""
        from src.events.event import Event
        query = """
            INSERT OR IGNORE INTO event_log (id, type, source, correlation_id, user_id, payload, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            event.id,
            event.type,
            event.source,
            event.correlation_id,
            event.user_id,
            json.dumps(event.payload),
            json.dumps(event.metadata) if event.metadata else None,
            event.timestamp,
        )
        try:
            self.db.execute(query, params)
            self.db.commit()
        except Exception:
            pass  # INSERT OR IGNORE handles duplicates

    def query(
        self,
        event_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        """Query stored events with optional filters."""
        from src.events.event import Event
        conditions = []
        params = []

        if event_type:
            if event_type.endswith(".*"):
                prefix = event_type[:-2]
                conditions.append("type LIKE ?")
                params.append(f"{prefix}.%")
            else:
                conditions.append("type = ?")
                params.append(event_type)

        if correlation_id:
            conditions.append("correlation_id = ?")
            params.append(correlation_id)

        if since:
            conditions.append("created_at >= ?")
            params.append(since)

        where = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM event_log WHERE {where} ORDER BY created_at ASC LIMIT ?"
        params.append(limit)

        cursor = self.db.execute(query, tuple(params))
        rows = cursor.fetchall()

        events = []
        for row in rows:
            events.append(Event(
                id=row["id"],
                type=row["type"],
                timestamp=row["created_at"],
                source=row["source"],
                correlation_id=row["correlation_id"] or "",
                payload=json.loads(row["payload"]) if row["payload"] else {},
                user_id=row["user_id"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            ))
        return events

    def replay(self, correlation_id: str) -> list:
        """Replay all events for a workflow (debugging)."""
        return self.query(correlation_id=correlation_id, limit=1000)

    def count(self, event_type: Optional[str] = None) -> int:
        """Count events, optionally filtered by type."""
        if event_type:
            cursor = self.db.execute(
                "SELECT COUNT(*) FROM event_log WHERE type = ?", (event_type,)
            )
        else:
            cursor = self.db.execute("SELECT COUNT(*) FROM event_log")
        return cursor.fetchone()[0]
