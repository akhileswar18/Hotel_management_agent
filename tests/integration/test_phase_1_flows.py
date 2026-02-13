"""
Integration Tests: Full Phase 1 Flows

Tests the complete order lifecycle, inventory tracking,
authentication, void/refund, and reporting — all exercising
the real SQLite database via the service + repository layers.
"""

import pytest
from uuid import uuid4
from datetime import datetime

from src.application import SalesService, InventoryService, AuthService, ReportingService
from src.infrastructure import (
    OrderRepository, ItemRepository, UserRepository,
    StockLedgerRepository, AuditLogRepository, PaymentRepository,
    VoidRecordRepository,
)
from src.domain import (
    Money, PaymentMethod, OrderStatus, TransactionType, Role,
    InvalidDiscountError, InsufficientStockError,
)


# ============================================================
# ORDER LIFECYCLE TESTS
# ============================================================

class TestCreateOrder:
    """Test order creation."""

    def test_create_draft_order(self, sample_user):
        """Creating an order produces a DRAFT with zero totals."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)

        assert order.status == OrderStatus.DRAFT
        assert order.subtotal.cents == 0
        assert order.tax_amount.cents == 0
        assert order.total_amount.cents == 0
        assert order.table_id == "1"
        assert order.receipt_number is None

    def test_create_order_persists_to_db(self, sample_user):
        """Order is readable from the DB after creation."""
        svc = SalesService()
        order = svc.create_order(table_id="2", created_by=sample_user.id)

        fetched = svc.get_order(order.id)
        assert fetched is not None
        assert fetched.id == order.id
        assert fetched.table_id == "2"

    def test_create_order_audit_logged(self, sample_user):
        """Creating an order writes to the audit_log table."""
        svc = SalesService()
        order = svc.create_order(table_id="3", created_by=sample_user.id)

        audit_repo = AuditLogRepository()
        entries = audit_repo.query_by_entity("Order", str(order.id))
        assert len(entries) >= 1
        assert any(e.operation == "CREATE" for e in entries)


class TestAddItemToOrder:
    """Test adding line items to an order."""

    def test_add_single_item(self, sample_user, stocked_item):
        """Adding an item persists the line item and recalculates totals."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)

        updated = svc.add_item(order.id, stocked_item.id, quantity=2, added_by=sample_user.id)

        assert len(updated.line_items) == 1
        assert updated.line_items[0].quantity == 2
        assert updated.line_items[0].item_name == "Biryani"
        # 2 x Rs.300 = Rs.600 = 60000 cents
        assert updated.subtotal.cents == 60000
        # Tax 18%: 60000 * 0.18 = 10800
        assert updated.tax_amount.cents == 10800
        # Total: 60000 + 10800 = 70800
        assert updated.total_amount.cents == 70800

    def test_add_multiple_items(self, sample_user, stocked_item, stocked_coke):
        """Adding multiple items correctly aggregates totals."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)

        svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)
        updated = svc.add_item(order.id, stocked_coke.id, quantity=3, added_by=sample_user.id)

        assert len(updated.line_items) == 2
        # 1 x 300 + 3 x 50 = 300 + 150 = 450 = 45000 cents
        assert updated.subtotal.cents == 45000

    def test_add_item_persists_to_db(self, sample_user, stocked_item):
        """Line item is readable from the DB after adding."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)
        svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)

        # Re-fetch from DB directly
        fetched = svc.get_order(order.id)
        assert len(fetched.line_items) == 1
        assert fetched.subtotal.cents == 30000  # 1 x Rs.300

    def test_add_item_to_finalized_order_fails(self, sample_user, stocked_item):
        """Cannot add items to a finalized order."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)
        svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)
        svc.finalize_order(
            order.id, PaymentMethod.CASH, Money.from_float(354.0), sample_user.id
        )

        with pytest.raises(ValueError, match="finalized"):
            svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)

    def test_add_item_invalid_quantity_fails(self, sample_user, stocked_item):
        """Cannot add zero or negative quantity."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)

        with pytest.raises(ValueError, match="positive"):
            svc.add_item(order.id, stocked_item.id, quantity=0, added_by=sample_user.id)

    def test_add_nonexistent_item_fails(self, sample_user):
        """Adding an item that doesn't exist raises ValueError."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)

        with pytest.raises(ValueError, match="not found"):
            svc.add_item(order.id, uuid4(), quantity=1, added_by=sample_user.id)


class TestFinalizeOrder:
    """Test order finalization (payment, stock deduction, receipt)."""

    def test_finalize_assigns_receipt_number(self, sample_user, stocked_item):
        """Finalizing an order assigns a unique receipt number."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)
        svc.add_item(order.id, stocked_item.id, quantity=2, added_by=sample_user.id)

        finalized = svc.finalize_order(
            order.id, PaymentMethod.CASH, Money.from_float(708.0), sample_user.id
        )

        assert finalized.status == OrderStatus.FINALIZED
        assert finalized.receipt_number is not None
        assert finalized.receipt_number.startswith("REC-")
        assert finalized.finalized_at is not None

    def test_finalize_deducts_stock(self, sample_user, stocked_item):
        """Finalizing deducts the sold quantities from stock."""
        svc = SalesService()
        inv = InventoryService()

        stock_before = inv.get_stock_on_hand(stocked_item.id)

        order = svc.create_order(table_id="1", created_by=sample_user.id)
        svc.add_item(order.id, stocked_item.id, quantity=5, added_by=sample_user.id)
        svc.finalize_order(
            order.id, PaymentMethod.CASH, Money.from_float(2000.0), sample_user.id
        )

        stock_after = inv.get_stock_on_hand(stocked_item.id)
        assert stock_after == stock_before - 5

    def test_finalize_records_payment(self, sample_user, stocked_item):
        """Finalizing creates a record in the payments table."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)
        svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)

        svc.finalize_order(
            order.id, PaymentMethod.CARD, Money.from_float(354.0), sample_user.id
        )

        payment_repo = PaymentRepository()
        payment = payment_repo.get_by_order(str(order.id))
        assert payment is not None
        assert payment.method == PaymentMethod.CARD
        assert payment.amount.cents == 35400  # Rs.354.00

    def test_finalize_empty_order_fails(self, sample_user):
        """Cannot finalize an order with no items."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)

        with pytest.raises(ValueError, match="no items"):
            svc.finalize_order(
                order.id, PaymentMethod.CASH, Money.from_float(0.0), sample_user.id
            )

    def test_finalize_insufficient_stock_fails(self, sample_user, stocked_item):
        """Cannot add items exceeding available stock."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)
        # Try to sell 999 units (only 100 in stock) — rejected at add_item
        with pytest.raises(ValueError, match="Insufficient stock"):
            svc.add_item(order.id, stocked_item.id, quantity=999, added_by=sample_user.id)

    def test_finalize_audit_logged(self, sample_user, stocked_item):
        """Finalization creates a FINALIZE entry in the audit log."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)
        svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)
        svc.finalize_order(
            order.id, PaymentMethod.CASH, Money.from_float(354.0), sample_user.id
        )

        audit_repo = AuditLogRepository()
        entries = audit_repo.query_by_entity("Order", str(order.id))
        assert any(e.operation == "FINALIZE" for e in entries)

    def test_finalize_already_finalized_fails(self, sample_user, stocked_item):
        """Cannot finalize an already-finalized order."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)
        svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)
        svc.finalize_order(
            order.id, PaymentMethod.CASH, Money.from_float(354.0), sample_user.id
        )

        with pytest.raises(ValueError, match="already finalized"):
            svc.finalize_order(
                order.id, PaymentMethod.CASH, Money.from_float(354.0), sample_user.id
            )


class TestDiscountFlow:
    """Test applying discounts to orders."""

    def test_percentage_discount(self, sample_user, stocked_item):
        """Applying a percentage discount recalculates totals."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)
        svc.add_item(order.id, stocked_item.id, quantity=2, added_by=sample_user.id)

        updated = svc.apply_order_discount(order.id, "percentage", 10.0, sample_user.id)

        # Subtotal still 60000 (2 x Rs.300)
        assert updated.subtotal.cents == 60000
        # Discount: 10% of 60000 = 6000
        assert updated.discount_amount.cents == 6000
        # Tax on (60000 - 6000) = 54000 * 0.18 = 9720
        assert updated.tax_amount.cents == 9720
        # Total: 54000 + 9720 = 63720
        assert updated.total_amount.cents == 63720

    def test_excessive_discount_fails(self, sample_user, stocked_item):
        """Discount > 50% raises InvalidDiscountError."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)
        svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)

        with pytest.raises(InvalidDiscountError):
            svc.apply_order_discount(order.id, "percentage", 60.0, sample_user.id)

    def test_discount_on_empty_order_fails(self, sample_user):
        """Cannot apply discount to order with zero subtotal."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)

        with pytest.raises(ValueError, match="empty order"):
            svc.apply_order_discount(order.id, "percentage", 10.0, sample_user.id)


class TestVoidOrder:
    """Test order void/cancellation."""

    def test_void_draft_order(self, sample_user, stocked_item):
        """Voiding a draft order marks it as voided."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)
        svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)

        voided = svc.void_order(order.id, reason="Customer cancelled", voided_by=sample_user.id)

        assert voided.status == OrderStatus.VOIDED

    def test_void_finalized_order_reverses_stock(self, sample_user, stocked_item):
        """Voiding a finalized order reverses stock deductions."""
        svc = SalesService()
        inv = InventoryService()

        stock_before = inv.get_stock_on_hand(stocked_item.id)

        order = svc.create_order(table_id="1", created_by=sample_user.id)
        svc.add_item(order.id, stocked_item.id, quantity=3, added_by=sample_user.id)
        svc.finalize_order(
            order.id, PaymentMethod.CASH, Money.from_float(2000.0), sample_user.id
        )

        stock_after_finalize = inv.get_stock_on_hand(stocked_item.id)
        assert stock_after_finalize == stock_before - 3

        svc.void_order(order.id, reason="Wrong table", voided_by=sample_user.id)

        stock_after_void = inv.get_stock_on_hand(stocked_item.id)
        assert stock_after_void == stock_before  # Stock fully restored

    def test_void_creates_void_record(self, sample_user, stocked_item):
        """Voiding an order creates a record in the void_records table."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)
        svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)
        svc.void_order(order.id, reason="Duplicate order", voided_by=sample_user.id)

        void_repo = VoidRecordRepository()
        record = void_repo.get_by_order(str(order.id))
        assert record is not None
        assert record.void_reason == "Duplicate order"

    def test_void_already_voided_fails(self, sample_user, stocked_item):
        """Cannot void an already-voided order."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)
        svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)
        svc.void_order(order.id, reason="Test", voided_by=sample_user.id)

        with pytest.raises(ValueError, match="already voided"):
            svc.void_order(order.id, reason="Double void", voided_by=sample_user.id)

    def test_void_audit_logged(self, sample_user, stocked_item):
        """Voiding an order writes a VOID entry to audit log."""
        svc = SalesService()
        order = svc.create_order(table_id="1", created_by=sample_user.id)
        svc.add_item(order.id, stocked_item.id, quantity=1, added_by=sample_user.id)
        svc.void_order(order.id, reason="Test audit", voided_by=sample_user.id)

        audit_repo = AuditLogRepository()
        entries = audit_repo.query_by_entity("Order", str(order.id))
        assert any(e.operation == "VOID" for e in entries)


# ============================================================
# INVENTORY TESTS
# ============================================================

class TestInventoryTracking:
    """Test inventory management and stock ledger."""

    def test_stock_in_increases_stock(self, sample_item, sample_user):
        """Recording stock-in increases stock on hand."""
        inv = InventoryService()
        assert inv.get_stock_on_hand(sample_item.id) == 0

        inv.record_stock_in(sample_item.id, 50, "PO-001", sample_user.id)
        assert inv.get_stock_on_hand(sample_item.id) == 50

        inv.record_stock_in(sample_item.id, 30, "PO-002", sample_user.id)
        assert inv.get_stock_on_hand(sample_item.id) == 80

    def test_stock_adjustment(self, stocked_item, sample_user):
        """Stock adjustments update the ledger correctly."""
        inv = InventoryService()
        assert inv.get_stock_on_hand(stocked_item.id) == 100

        inv.record_adjustment(stocked_item.id, -5, "Wastage - expired", sample_user.id)
        assert inv.get_stock_on_hand(stocked_item.id) == 95

        inv.record_adjustment(stocked_item.id, 3, "Found during recount", sample_user.id)
        assert inv.get_stock_on_hand(stocked_item.id) == 98

    def test_stock_ledger_is_append_only(self, stocked_item, sample_user):
        """Ledger entries accumulate; nothing is deleted or modified."""
        stock_repo = StockLedgerRepository()
        inv = InventoryService()

        before = len(stock_repo.get_by_item(str(stocked_item.id)))

        inv.record_stock_in(stocked_item.id, 10, "PO-X", sample_user.id)
        inv.record_adjustment(stocked_item.id, -2, "Broken", sample_user.id)

        after = len(stock_repo.get_by_item(str(stocked_item.id)))
        assert after == before + 2

    def test_low_stock_detection(self, sample_user, test_db):
        """Items with stock below reorder_level are flagged as low-stock."""
        inv = InventoryService()
        from src.infrastructure import ItemRepository
        from src.domain import Item

        item = Item(
            id=uuid4(),
            name="Low Stock Item",
            category="Test",
            unit_price=Money.from_float(100.0),
            reorder_level=20,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=sample_user.id,
        )
        ItemRepository().create(item)

        # Add 5 units (below reorder_level of 20)
        inv.record_stock_in(item.id, 5, "TEST", sample_user.id)

        low_stock = inv.get_low_stock_items()
        assert any(i.id == item.id for i in low_stock)

    def test_create_item(self, sample_user):
        """Creating a new product via InventoryService persists it."""
        inv = InventoryService()
        item = inv.create_item(
            name="Masala Chai",
            category="Beverages",
            unit_price=Money.from_float(30.0),
            reorder_level=25,
            created_by=sample_user.id,
        )
        assert item.name == "Masala Chai"

        fetched = inv.item_repo.get(str(item.id))
        assert fetched is not None
        assert fetched.name == "Masala Chai"

    def test_negative_stock_in_fails(self, sample_item, sample_user):
        """Recording negative stock-in raises ValueError."""
        inv = InventoryService()
        with pytest.raises(ValueError, match="positive"):
            inv.record_stock_in(sample_item.id, -10, "Bad", sample_user.id)


# ============================================================
# AUTHENTICATION TESTS
# ============================================================

class TestAuthentication:
    """Test user authentication and authorization."""

    def test_login_valid_pin(self, sample_user):
        """Login with correct PIN succeeds and returns token."""
        auth = AuthService()
        user, token = auth.login("testmanager", "1234")
        assert user.id == sample_user.id
        assert token is not None

    def test_login_invalid_pin(self, sample_user):
        """Login with wrong PIN raises ValueError."""
        auth = AuthService()
        with pytest.raises(ValueError, match="Invalid"):
            auth.login("testmanager", "9999")

    def test_login_nonexistent_user(self, test_db):
        """Login with unknown username raises ValueError."""
        auth = AuthService()
        with pytest.raises(ValueError, match="Invalid"):
            auth.login("ghost", "1234")

    def test_manager_can_void(self, sample_user):
        """Manager role has void_order permission."""
        auth = AuthService()
        assert auth.can_perform_action(sample_user, "void_order") is True

    def test_waiter_cannot_void(self, sample_waiter):
        """Waiter role does NOT have void_order permission."""
        auth = AuthService()
        assert auth.can_perform_action(sample_waiter, "void_order") is False

    def test_waiter_can_create_order(self, sample_waiter):
        """Waiter role can create orders."""
        auth = AuthService()
        assert auth.can_perform_action(sample_waiter, "create_order") is True


# ============================================================
# REPORTING TESTS
# ============================================================

class TestReporting:
    """Test reporting service."""

    def test_daily_sales_empty(self, test_db):
        """Daily sales with no transactions returns zero totals."""
        rpt = ReportingService()
        summary = rpt.daily_sales_summary()

        assert summary["total_revenue"] == 0.0
        assert summary["transaction_count"] == 0

    def test_daily_sales_after_orders(self, sample_user, stocked_item, stocked_coke):
        """Daily sales reflects finalized orders."""
        svc = SalesService()

        # Create and finalize order 1
        o1 = svc.create_order("1", sample_user.id)
        svc.add_item(o1.id, stocked_item.id, 2, sample_user.id)
        svc.finalize_order(o1.id, PaymentMethod.CASH, Money.from_float(708.0), sample_user.id)

        # Create and finalize order 2
        o2 = svc.create_order("2", sample_user.id)
        svc.add_item(o2.id, stocked_coke.id, 3, sample_user.id)
        svc.finalize_order(o2.id, PaymentMethod.CARD, Money.from_float(177.0), sample_user.id)

        rpt = ReportingService()
        summary = rpt.daily_sales_summary()

        assert summary["transaction_count"] == 2
        assert summary["total_revenue"] > 0
        assert "CASH" in summary["payment_methods"]
        assert "CARD" in summary["payment_methods"]

    def test_inventory_snapshot(self, stocked_item, stocked_coke):
        """Inventory snapshot lists all items with stock levels."""
        rpt = ReportingService()
        snapshot = rpt.inventory_snapshot()

        assert snapshot["total_items"] >= 2
        names = [i["name"] for i in snapshot["inventory"]]
        assert "Biryani" in names
        assert "Coke" in names


# ============================================================
# FULL END-TO-END FLOW
# ============================================================

class TestFullEndToEnd:
    """Full end-to-end test: login → create order → add items → finalize → check DB."""

    def test_complete_order_flow(self, sample_user, stocked_item, stocked_coke):
        """
        Complete lifecycle:
        1. Create order for table 1
        2. Add 2 Biryani + 3 Coke
        3. Apply 10% discount
        4. Finalize with CASH
        5. Verify: DB persisted, stock deducted, audit logged, payment recorded
        """
        svc = SalesService()
        inv = InventoryService()

        biryani_stock_before = inv.get_stock_on_hand(stocked_item.id)
        coke_stock_before = inv.get_stock_on_hand(stocked_coke.id)

        # Step 1: Create order
        order = svc.create_order(table_id="1", created_by=sample_user.id)
        assert order.status == OrderStatus.DRAFT

        # Step 2: Add items
        svc.add_item(order.id, stocked_item.id, quantity=2, added_by=sample_user.id)
        order = svc.add_item(order.id, stocked_coke.id, quantity=3, added_by=sample_user.id)

        assert len(order.line_items) == 2
        # Subtotal: 2*300 + 3*50 = 600+150 = 750 = 75000 cents
        assert order.subtotal.cents == 75000

        # Step 3: Apply 10% discount
        order = svc.apply_order_discount(order.id, "percentage", 10.0, sample_user.id)
        assert order.discount_amount.cents == 7500  # 10% of 75000

        # Step 4: Finalize
        finalized = svc.finalize_order(
            order.id, PaymentMethod.CASH, Money.from_float(900.0), sample_user.id
        )
        assert finalized.status == OrderStatus.FINALIZED
        assert finalized.receipt_number is not None

        # Step 5: Verify persistence
        db_order = svc.get_order(order.id)
        assert db_order.status == OrderStatus.FINALIZED
        assert len(db_order.line_items) == 2
        assert db_order.receipt_number == finalized.receipt_number

        # Verify stock deducted
        assert inv.get_stock_on_hand(stocked_item.id) == biryani_stock_before - 2
        assert inv.get_stock_on_hand(stocked_coke.id) == coke_stock_before - 3

        # Verify payment recorded
        payment_repo = PaymentRepository()
        payment = payment_repo.get_by_order(str(order.id))
        assert payment is not None
        assert payment.method == PaymentMethod.CASH

        # Verify audit log
        audit_repo = AuditLogRepository()
        audit_entries = audit_repo.query_by_entity("Order", str(order.id))
        operations = [e.operation for e in audit_entries]
        assert "CREATE" in operations
        assert "FINALIZE" in operations
