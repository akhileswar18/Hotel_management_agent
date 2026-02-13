"""
Performance Benchmarks

Verify the system can handle 1000 transactions per day target.
Agent performance: EventBus throughput and event-driven vs direct service timing.
"""

import time
import pytest
from src.application.services import SalesService, InventoryService
from src.domain.value_objects import PaymentMethod, Money
from src.events import EventBus, EventStore
from src.events.event import Event


class TestPerformanceBenchmarks:
    """Performance benchmarks for HMS operations."""

    def test_order_creation_throughput(self, sample_user, stocked_item):
        """Verify order creation meets throughput target (1000/day = ~1/sec)."""
        svc = SalesService()

        iterations = 50  # test 50 orders
        start = time.perf_counter()

        for i in range(iterations):
            order = svc.create_order(table_id=str(i % 10 + 1), created_by=sample_user.id)
            svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)

        elapsed = time.perf_counter() - start
        ops_per_second = iterations / elapsed

        print(f"\nOrder creation: {ops_per_second:.1f} ops/sec ({elapsed:.2f}s for {iterations})")
        assert ops_per_second > 1.0, f"Too slow: {ops_per_second:.1f} ops/sec (need >1.0)"

    def test_finalization_throughput(self, sample_user, stocked_item):
        """Verify order finalization meets throughput target."""
        svc = SalesService()

        # Create orders first
        orders = []
        for i in range(20):
            order = svc.create_order(table_id=str(i % 10 + 1), created_by=sample_user.id)
            svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)
            orders.append(order)

        start = time.perf_counter()
        for order in orders:
            try:
                svc.finalize_order(
                    order.id, PaymentMethod.CASH,
                    Money.from_float(500.0), sample_user.id
                )
            except Exception:
                pass

        elapsed = time.perf_counter() - start
        ops_per_second = len(orders) / elapsed

        print(f"\nFinalization: {ops_per_second:.1f} ops/sec ({elapsed:.2f}s for {len(orders)})")
        assert ops_per_second > 0.5, f"Too slow: {ops_per_second:.1f} ops/sec"

    def test_stock_query_throughput(self, stocked_item):
        """Verify stock queries are fast."""
        inv_svc = InventoryService()

        iterations = 100
        start = time.perf_counter()

        for _ in range(iterations):
            inv_svc.get_stock_on_hand(stocked_item.id)

        elapsed = time.perf_counter() - start
        ops_per_second = iterations / elapsed

        print(f"\nStock query: {ops_per_second:.1f} ops/sec ({elapsed:.2f}s for {iterations})")
        assert ops_per_second > 10.0, f"Too slow: {ops_per_second:.1f} ops/sec"

    def test_report_generation_speed(self, sample_user, stocked_item):
        """Verify report generation completes within 5 seconds."""
        from src.application.services import ReportingService

        svc = SalesService()
        # Create some orders for reporting
        for i in range(5):
            order = svc.create_order(table_id=str(i+1), created_by=sample_user.id)
            svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)
            svc.finalize_order(order.id, PaymentMethod.CASH, Money.from_float(500.0), sample_user.id)

        reporting = ReportingService()
        start = time.perf_counter()
        summary = reporting.daily_sales_summary()
        elapsed = time.perf_counter() - start

        print(f"\nReport generation: {elapsed:.3f}s")
        assert elapsed < 5.0, f"Too slow: {elapsed:.1f}s (need <5s)"


class TestAgentPerformanceBenchmarks:
    """Agent/EventBus performance benchmarks (A082–A084)."""

    def test_event_bus_throughput(self, test_db):
        """Publish 1,000 events with SQLite persistence; assert < 30s (33+ events/sec with full I/O).

        Note: Each event involves SQLite INSERT (EventStore.append).
        For in-memory-only throughput, remove the EventStore.
        """
        bus = EventBus(store=EventStore())
        count = [0]  # mutable so handler can update

        def handler(event):
            count[0] += 1
            return None

        bus.subscribe("benchmark.test", handler)
        n = 1_000
        start = time.perf_counter()
        for i in range(n):
            evt = Event.create(
                type="benchmark.test",
                source="test",
                payload={"i": i},
            )
            bus.publish_sync(evt)
        elapsed = time.perf_counter() - start
        assert count[0] == n, "Handler should see all events"
        rate = n / elapsed
        assert elapsed < 30.0, f"Throughput too low: {elapsed:.2f}s for {n} events ({rate:.0f}/sec)"

    def test_order_finalization_via_events_latency(
        self, test_db, sample_user, stocked_item
    ):
        """Create + add_item + finalize via EventBus; total time < 500ms."""
        from src.api.app import create_app

        app = create_app()
        bus = app.state.event_bus
        user_id = str(sample_user.id)
        item_id = str(stocked_item.id)

        start = time.perf_counter()
        # Create order
        e1 = Event.create(
            type="order.create",
            source="test",
            payload={"table_id": "1", "user_id": user_id},
            user_id=user_id,
        )
        r1 = bus.publish_sync(e1)
        assert r1.success and r1.event
        order_id = r1.event.payload["order_id"]
        # Add item
        e2 = Event.create(
            type="order.add_item",
            source="test",
            payload={"order_id": order_id, "item_id": item_id, "quantity": 1},
            user_id=user_id,
        )
        r2 = bus.publish_sync(e2)
        assert r2.success and r2.event
        total = r2.event.payload["total_amount"]
        # Finalize
        e3 = Event.create(
            type="order.finalize",
            source="test",
            payload={
                "order_id": order_id,
                "payment_method": "CASH",
                "amount_tendered": total,
            },
            user_id=user_id,
        )
        r3 = bus.publish_sync(e3)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        assert r3.success and r3.event
        assert r3.event.type == "order.finalized"
        assert elapsed < 500.0, f"Event-driven finalization too slow: {elapsed:.0f}ms (need <500ms)"

    def test_event_driven_no_regression_vs_direct(
        self, test_db, sample_user, stocked_item
    ):
        """Event-driven create+add+finalize should be no more than 3x slower than direct SalesService."""
        from src.api.app import create_app

        app = create_app()
        bus = app.state.event_bus
        user_id = str(sample_user.id)
        item_id = str(stocked_item.id)
        iterations = 10

        # Event-driven: 10 iterations
        start_ev = time.perf_counter()
        for i in range(iterations):
            e1 = Event.create(
                type="order.create",
                source="test",
                payload={"table_id": str(i), "user_id": user_id},
                user_id=user_id,
            )
            r1 = bus.publish_sync(e1)
            assert r1.success and r1.event
            order_id = r1.event.payload["order_id"]
            e2 = Event.create(
                type="order.add_item",
                source="test",
                payload={"order_id": order_id, "item_id": item_id, "quantity": 1},
                user_id=user_id,
            )
            r2 = bus.publish_sync(e2)
            assert r2.success and r2.event
            total = r2.event.payload["total_amount"]
            e3 = Event.create(
                type="order.finalize",
                source="test",
                payload={
                    "order_id": order_id,
                    "payment_method": "CASH",
                    "amount_tendered": total,
                },
                user_id=user_id,
            )
            r3 = bus.publish_sync(e3)
            assert r3.success and r3.event
        elapsed_ev = time.perf_counter() - start_ev

        # Direct service: 10 iterations
        svc = SalesService()
        start_direct = time.perf_counter()
        for i in range(iterations):
            order = svc.create_order(table_id=str(i + 100), created_by=sample_user.id)
            svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)
            svc.finalize_order(
                order.id, PaymentMethod.CASH, Money.from_float(500.0), sample_user.id
            )
        elapsed_direct = time.perf_counter() - start_direct

        assert elapsed_ev <= 3.0 * elapsed_direct, (
            f"Event-driven ({elapsed_ev:.3f}s) > 3x direct ({elapsed_direct:.3f}s)"
        )
