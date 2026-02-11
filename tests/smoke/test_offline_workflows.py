"""
Offline Workflow Smoke Tests

Tests complete workflows without network to verify offline-first operation.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import patch

from src.application import SalesService, InventoryService, AuthService
from src.infrastructure import (
    OrderRepository, ItemRepository, StockLedgerRepository
)
from src.domain import (
    Money, PaymentMethod, OrderStatus, TransactionType, Role, User
)


class TestOfflineOperation:
    """Test all operations work offline (no network calls)."""

    @patch('httpx.AsyncClient')
    def test_create_order_offline(self, mock_http, test_db, sample_user, sample_item):
        """Test creating order without network."""
        # Mock HTTP to ensure it's not called
        mock_http.return_value = None

        sales_service = SalesService()

        # Create order (should work without network)
        order = sales_service.create_order(
            table_id="1",
            created_by=sample_user.id,
        )

        assert order.status == OrderStatus.DRAFT
        assert order.total_amount.cents == 0
        # HTTP should not be called
        mock_http.assert_not_called()

    def test_finalize_order_offline(self, test_db, sample_user, sample_item):
        """Test order finalization without network."""
        sales_service = SalesService()
        stock_service = InventoryService()

        # Setup stock offline
        stock_service.record_stock_in(
            sample_item.id,
            quantity=50,
            reference="LOCAL-STOCK",
            recorded_by=sample_user.id,
        )

        # Create and finalize order entirely offline
        order = sales_service.create_order(
            table_id="2",
            created_by=sample_user.id,
        )

        order = sales_service.add_item(
            order.id,
            sample_item.id,
            quantity=1,
            added_by=sample_user.id,
        )

        finalized = sales_service.finalize_order(
            order.id,
            PaymentMethod.CASH,
            Money.from_float(350.00),
            finalized_by=sample_user.id,
        )

        # Verify all state is local
        assert finalized.status == OrderStatus.FINALIZED
        assert finalized.receipt_number is not None

        # Verify stock deducted locally
        stock = stock_service.get_stock_on_hand(sample_item.id)
        assert stock == 49

    def test_inventory_query_offline(self, test_db, sample_user):
        """Test inventory queries without network."""
        from src.domain import Item

        inventory_service = InventoryService()
        item_repo = ItemRepository()

        # Create items locally
        item1 = Item(
            id=uuid4(),
            name="Item 1",
            category="Test",
            unit_price=Money.from_float(100.00),
            reorder_level=5,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=sample_user.id,
        )
        item_repo.create(item1)

        # Query offline
        items = item_repo.list()
        assert len(items) >= 1
        assert any(i.id == item1.id for i in items)

    def test_authentication_offline(self, test_db, sample_user):
        """Test authentication works offline (cached credentials)."""
        auth_service = AuthService()
        pin = "1234"
        pin_hash = auth_service.hash_pin(pin)

        # Create user locally
        user_repo = AuthService()  # Placeholder
        from src.infrastructure import UserRepository
        repo = UserRepository()
        repo.create(sample_user, pin_hash)

        # Authenticate offline
        user, token = auth_service.login(sample_user.username, pin)
        assert user.id == sample_user.id
        assert token is not None

    def test_audit_logging_offline(self, test_db, sample_user, sample_item):
        """Test audit logs are written locally offline."""
        from src.infrastructure import AuditLogRepository

        sales_service = SalesService()
        audit_repo = AuditLogRepository()

        # Create order and audit log
        order = sales_service.create_order(
            table_id="3",
            created_by=sample_user.id,
        )

        # Query audit log offline
        audit_entries = audit_repo.query_by_entity("Order", str(order.id))
        assert len(audit_entries) > 0
        assert audit_entries[0].operation == "CREATE"

    def test_full_workflow_offline(self, test_db, sample_user, sample_item):
        """Test complete workflow offline without network."""
        sales_service = SalesService()
        stock_service = InventoryService()

        # 1. Record stock offline
        stock_service.record_stock_in(
            sample_item.id,
            quantity=100,
            reference="OFFLINE-INIT",
            recorded_by=sample_user.id,
        )

        # 2. Create order
        order = sales_service.create_order(
            table_id="1",
            created_by=sample_user.id,
        )

        # 3. Add items
        order = sales_service.add_item(
            order.id,
            sample_item.id,
            quantity=3,
            added_by=sample_user.id,
        )

        # 4. Finalize with payment
        finalized = sales_service.finalize_order(
            order.id,
            PaymentMethod.CASH,
            Money.from_float(1000.00),
            finalized_by=sample_user.id,
        )

        # 5. Verify all state is persisted locally
        assert finalized.status == OrderStatus.FINALIZED
        assert finalized.receipt_number is not None

        # 6. Verify stock updated
        remaining = stock_service.get_stock_on_hand(sample_item.id)
        assert remaining == 97  # 100 - 3

        # 7. Verify audit trail
        from src.infrastructure import AuditLogRepository
        audit_repo = AuditLogRepository()
        entries = audit_repo.query_by_entity("Order", str(order.id))
        assert len(entries) > 0


class TestPerformanceOffline:
    """Test performance targets in offline mode."""

    def test_order_creation_performance(self, test_db, sample_user):
        """Test order creation is fast (<100ms)."""
        import time

        sales_service = SalesService()

        start = time.time()
        order = sales_service.create_order(
            table_id="1",
            created_by=sample_user.id,
        )
        elapsed = time.time() - start

        assert elapsed < 0.1  # <100ms
        assert order.status == OrderStatus.DRAFT

    def test_stock_query_performance(self, test_db, sample_item, sample_user):
        """Test stock queries are fast (<200ms)."""
        import time

        stock_service = InventoryService()

        # Populate stock
        stock_service.record_stock_in(
            sample_item.id,
            quantity=1000,
            reference="PERF-TEST",
            recorded_by=sample_user.id,
        )

        # Query stock
        start = time.time()
        stock = stock_service.get_stock_on_hand(sample_item.id)
        elapsed = time.time() - start

        assert elapsed < 0.2  # <200ms
        assert stock == 1000


# TODO: Add network failure simulation tests
# TODO: Add sync queue tests (when Phase 2 sync is ready)
# TODO: Add battery/power loss scenario tests
