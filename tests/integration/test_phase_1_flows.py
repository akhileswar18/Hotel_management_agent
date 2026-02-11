"""Integration tests for full order flow."""

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime

from src.application import SalesService, InventoryService, AuthService
from src.infrastructure import (
    OrderRepository, ItemRepository, UserRepository,
    StockLedgerRepository, AuditLogRepository
)
from src.domain import (
    Money, PaymentMethod, OrderStatus, TransactionType, Role
)


class TestFullOrderFlow:
    """Test complete order lifecycle."""

    def test_create_and_finalize_order(self, test_db, sample_user, sample_item):
        """Test creating and finalizing an order."""
        # Setup
        sales_service = SalesService()
        stock_service = InventoryService()

        # Add stock for item
        stock_service.record_stock_in(
            sample_item.id,
            quantity=100,
            reference="TEST-PO-001",
            recorded_by=sample_user.id,
        )

        # Step 1: Create order
        order = sales_service.create_order(
            table_id="1",
            created_by=sample_user.id,
        )
        assert order.status == OrderStatus.DRAFT
        assert order.total_amount.cents == 0

        # Step 2: Add item
        order = sales_service.add_item(
            order.id,
            sample_item.id,
            quantity=2,
            added_by=sample_user.id,
        )
        assert len(order.line_items) == 1
        assert order.line_items[0].quantity == 2
        # Total should be 2 * ₹300 = ₹600
        assert order.subtotal.cents == 60000

        # Step 3: Finalize order
        finalized = sales_service.finalize_order(
            order.id,
            PaymentMethod.CASH,
            Money.from_float(650.00),
            finalized_by=sample_user.id,
        )
        assert finalized.status == OrderStatus.FINALIZED
        assert finalized.receipt_number is not None
        assert finalized.receipt_number.startswith("REC-")

        # Step 4: Check stock was deducted
        remaining_stock = stock_service.get_stock_on_hand(sample_item.id)
        assert remaining_stock == 98  # 100 - 2

        # Step 5: Verify audit log
        audit_repo = AuditLogRepository()
        audit_entries = audit_repo.query_by_entity("Order", str(order.id))
        assert len(audit_entries) > 0
        assert any(e.operation == "FINALIZE" for e in audit_entries)


class TestInventoryTracking:
    """Test inventory management and stock ledger."""

    def test_stock_ledger_append_only(self, test_db, sample_item, sample_user):
        """Test stock ledger is append-only."""
        stock_repo = StockLedgerRepository()

        # Add stock
        entry1 = stock_repo.create(
            __import__("src.domain", fromlist=["StockLedgerEntry"]).StockLedgerEntry(
                id=uuid4(),
                item_id=sample_item.id,
                transaction_type=TransactionType.PURCHASE,
                quantity_change=100,
                reason="Initial stock",
                created_at=datetime.utcnow(),
                created_by=sample_user.id,
            )
        )

        # Deduct stock
        entry2 = stock_repo.create(
            __import__("src.domain", fromlist=["StockLedgerEntry"]).StockLedgerEntry(
                id=uuid4(),
                item_id=sample_item.id,
                transaction_type=TransactionType.SALE,
                quantity_change=-20,
                reason="Sale",
                created_at=datetime.utcnow(),
                created_by=sample_user.id,
            )
        )

        # Check ledger entries
        ledger = stock_repo.get_by_item(str(sample_item.id))
        assert len(ledger) == 2

        # Check stock on hand
        stock = stock_repo.compute_stock_on_hand(str(sample_item.id))
        assert stock == 80  # 100 - 20

    def test_low_stock_detection(self, test_db, sample_user):
        """Test low stock item detection."""
        from src.domain import Item

        inventory_service = InventoryService()
        item_repo = ItemRepository()

        # Create item with low stock
        item = Item(
            id=uuid4(),
            name="Test Item",
            category="Test",
            unit_price=Money.from_float(100.00),
            reorder_level=10,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=sample_user.id,
        )
        item_repo.create(item)

        # Add only 5 units (below reorder level of 10)
        inventory_service.record_stock_in(
            item.id,
            quantity=5,
            reference="TEST-LOW",
            recorded_by=sample_user.id,
        )

        # Check low stock detection
        low_stock_items = inventory_service.get_low_stock_items()
        assert any(i.id == item.id for i in low_stock_items)


class TestAuthentication:
    """Test user authentication and authorization."""

    def test_login_with_valid_pin(self, sample_user):
        """Test login with correct PIN."""
        auth_service = AuthService()
        pin = "1234"
        pin_hash = auth_service.hash_pin(pin)

        # Get user from repo with PIN
        user_repo = UserRepository()
        user_repo.create(sample_user, pin_hash)

        # Login
        result = auth_service.login("testuser", pin)
        assert result[0].id == sample_user.id
        assert result[1] is not None  # Token

    def test_login_with_invalid_pin(self, sample_user):
        """Test login with wrong PIN fails."""
        auth_service = AuthService()
        auth_service.hash_pin("1234")

        # Try wrong PIN
        with pytest.raises(ValueError):
            auth_service.login("testuser", "9999")

    def test_permission_validation(self, sample_user):
        """Test role-based permission checks."""
        auth_service = AuthService()

        # Waiter can create orders but not void
        assert auth_service.can_perform_action(sample_user, "create_order")
        assert not auth_service.can_perform_action(sample_user, "void_order")

        # Manager can do everything
        from src.domain import User
        manager = User(
            id=uuid4(),
            username="manager",
            role=Role.MANAGER,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert auth_service.can_perform_action(manager, "void_order")
        assert auth_service.can_perform_action(manager, "adjust_stock")


class TestTaxCalculation:
    """Test tax and discount calculations."""

    def test_order_total_with_tax(self, test_db, sample_user, sample_item):
        """Test order totals include 18% tax."""
        from src.domain import calculate_tax

        # ₹300 * 2 = ₹600
        subtotal = Money.from_float(600.00)
        tax = calculate_tax(subtotal, 0.18)

        # ₹600 * 0.18 = ₹108
        assert tax.cents == 10800

        # Total = ₹600 + ₹108 = ₹708
        total = Money(cents=subtotal.cents + tax.cents)
        assert total.to_float() == 708.00

    def test_discount_validation(self):
        """Test discount validation."""
        from src.domain import apply_discount, InvalidDiscountError

        price = Money.from_float(1000.00)

        # Valid 10% discount
        discounted = apply_discount(price, "percentage", 10.0)
        assert discounted.to_float() == 900.00

        # Invalid >50% discount should fail
        with pytest.raises(InvalidDiscountError):
            apply_discount(price, "percentage", 60.0)
