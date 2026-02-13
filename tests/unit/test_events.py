"""
Unit tests for Event infrastructure.

Tests Event serialization, EventBus dispatch, and EventStore persistence.
"""

import pytest
import json
from src.events.event import Event, EventResult
from src.events.bus import EventBus
from src.events.store import EventStore


class TestEventSerialization:
    """A015: Event serialization roundtrip tests."""

    def test_event_creation(self):
        """Event.create() generates valid event with all fields."""
        event = Event.create(
            type="order.create",
            payload={"table_id": "5"},
            source="TestAgent",
            user_id="user-123",
        )
        assert event.type == "order.create"
        assert event.payload == {"table_id": "5"}
        assert event.source == "TestAgent"
        assert event.user_id == "user-123"
        assert event.id  # UUID generated
        assert event.correlation_id  # UUID generated
        assert event.timestamp.endswith("Z")

    def test_event_to_json_roundtrip(self):
        """Event -> JSON -> Event produces identical object."""
        original = Event.create(
            type="inventory.stock_in",
            payload={"item_id": "abc", "quantity": 50},
            source="API",
        )
        json_str = original.to_json()
        restored = Event.from_json(json_str)
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.payload == original.payload
        assert restored.source == original.source
        assert restored.correlation_id == original.correlation_id

    def test_event_to_dict(self):
        """Event.to_dict() produces serializable dict."""
        event = Event.create(type="test.event", payload={"key": "value"})
        d = event.to_dict()
        assert isinstance(d, dict)
        assert d["type"] == "test.event"
        assert json.dumps(d)  # Must be JSON-serializable

    def test_event_immutable(self):
        """Events are frozen — cannot be modified after creation."""
        event = Event.create(type="test.event", payload={})
        with pytest.raises(AttributeError):
            event.type = "modified"

    def test_event_result(self):
        """EventResult wraps success/failure correctly."""
        event = Event.create(type="test", payload={})
        result = EventResult(success=True, event=event, elapsed_ms=1.5)
        assert result.success
        assert result.event.type == "test"
        assert result.elapsed_ms == 1.5

        fail = EventResult(success=False, error="timeout")
        assert not fail.success
        assert fail.error == "timeout"


class TestEventBusDispatch:
    """A016: EventBus dispatch, subscribe, wildcard tests."""

    def test_subscribe_and_publish(self):
        """Subscribe to event type, publish fires handler."""
        bus = EventBus(store=None)
        bus._store = type('MockStore', (), {'append': lambda self, e: None})()

        received = []
        def handler(event):
            received.append(event)
            return Event.create(type="order.created", payload={"ok": True}, source="test")

        bus.subscribe("order.create", handler)
        event = Event.create(type="order.create", payload={"table_id": "1"})
        result = bus.publish_sync(event)

        assert len(received) == 1
        assert received[0].type == "order.create"
        assert result.success

    def test_wildcard_subscribe(self):
        """Wildcard * receives all events."""
        bus = EventBus(store=None)
        bus._store = type('MockStore', (), {'append': lambda self, e: None})()

        received = []
        bus.subscribe("*", lambda e: received.append(e))

        bus.publish_sync(Event.create(type="order.create", payload={}))
        bus.publish_sync(Event.create(type="inventory.stock_in", payload={}))

        assert len(received) == 2

    def test_prefix_wildcard(self):
        """order.* matches order.create, order.finalize, etc."""
        bus = EventBus(store=None)
        bus._store = type('MockStore', (), {'append': lambda self, e: None})()

        received = []
        bus.subscribe("order.*", lambda e: received.append(e))

        bus.publish_sync(Event.create(type="order.create", payload={}))
        bus.publish_sync(Event.create(type="order.finalize", payload={}))
        bus.publish_sync(Event.create(type="inventory.stock_in", payload={}))

        assert len(received) == 2  # Only order.* events

    def test_no_handler_returns_error(self):
        """Publishing to unsubscribed type returns error result."""
        bus = EventBus(store=None)
        bus._store = type('MockStore', (), {'append': lambda self, e: None})()

        result = bus.publish_sync(Event.create(type="unknown.event", payload={}))
        assert not result.success
        assert "No handlers" in result.error

    def test_handler_exception_goes_to_dead_letter(self):
        """Failed handler puts event in dead letter queue."""
        bus = EventBus(store=None)
        bus._store = type('MockStore', (), {'append': lambda self, e: None})()

        def bad_handler(event):
            raise ValueError("Boom!")

        bus.subscribe("test.fail", bad_handler)
        event = Event.create(type="test.fail", payload={})
        result = bus.publish_sync(event)

        assert not result.success
        assert "Boom!" in result.error
        assert len(bus.dead_letter) == 1

    def test_subscriber_count(self):
        """subscriber_count tracks total subscriptions."""
        bus = EventBus(store=None)
        bus._store = type('MockStore', (), {'append': lambda self, e: None})()

        bus.subscribe("a", lambda e: None)
        bus.subscribe("b", lambda e: None)
        bus.subscribe("b", lambda e: None)
        assert bus.subscriber_count == 3


class TestEventStore:
    """A017: EventStore persistence tests."""

    def test_append_and_query(self):
        """Append event and query it back."""
        store = EventStore()
        event = Event.create(type="test.store", payload={"data": 42}, source="test")
        store.append(event)

        results = store.query(event_type="test.store")
        assert len(results) >= 1
        found = [e for e in results if e.id == event.id]
        assert len(found) == 1
        assert found[0].payload == {"data": 42}

    def test_query_by_correlation_id(self):
        """Query events by correlation_id groups related events."""
        store = EventStore()
        corr_id = "test-corr-" + str(id(self))

        e1 = Event.create(type="order.create", payload={}, correlation_id=corr_id)
        e2 = Event.create(type="order.add_item", payload={}, correlation_id=corr_id)
        e3 = Event.create(type="other.event", payload={}, correlation_id="different")

        store.append(e1)
        store.append(e2)
        store.append(e3)

        results = store.query(correlation_id=corr_id)
        assert len(results) >= 2
        types = [e.type for e in results]
        assert "order.create" in types
        assert "order.add_item" in types

    def test_replay(self):
        """Replay returns all events for a correlation_id."""
        store = EventStore()
        corr_id = "replay-test-" + str(id(self))

        for i in range(5):
            store.append(Event.create(
                type=f"step.{i}", payload={"step": i}, correlation_id=corr_id
            ))

        replayed = store.replay(corr_id)
        assert len(replayed) >= 5

    def test_count(self):
        """Count returns number of events."""
        store = EventStore()
        initial = store.count()
        store.append(Event.create(type="count.test", payload={}))
        assert store.count() >= initial + 1
