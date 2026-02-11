"""
Application Layer: Services

Orchestrates domain logic and repositories.
Zero business logic here; that stays in domain layer.
Services handle transactions, error handling, and workflow coordination.
"""

from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Optional, Tuple
import bcrypt

from src.domain import (
    Order, OrderLineItem, Item, User, StockLedgerEntry, Money,
    OrderStatus, TransactionType, Role, PaymentMethod, calculate_tax,
    validate_stock_deduction, validate_permission, InvalidDiscountError,
    InsufficientStockError,
)
from src.infrastructure import (
    OrderRepository, ItemRepository, UserRepository,
    StockLedgerRepository, AuditLogRepository, Database,
)


class AuthService:
    """User authentication and authorization service."""

    def __init__(self) -> None:
        """Initialize auth service."""
        self.user_repo = UserRepository()

    def login(self, username: str, pin: str) -> Tuple[User, str]:
        """
        Authenticate user with username and PIN.

        Args:
            username: Username
            pin: 4-6 digit PIN

        Returns:
            Tuple of (User, session_token)

        Raises:
            ValueError: If credentials invalid
        """
        result = self.user_repo.get_by_username(username)
        if result is None:
            raise ValueError("Invalid username or PIN")

        user, pin_hash = result

        # Verify PIN using bcrypt
        if not bcrypt.checkpw(pin.encode(), pin_hash.encode()):
            raise ValueError("Invalid username or PIN")

        # TODO: Create session token (Phase 2+)
        session_token = str(uuid4())
        return user, session_token

    def hash_pin(self, pin: str) -> str:
        """Hash PIN using bcrypt."""
        return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()

    def can_perform_action(self, user: User, action: str) -> bool:
        """Check if user can perform action."""
        return validate_permission(user.role.value, action)


class SalesService:
    """Sales and order management service."""

    def __init__(self) -> None:
        """Initialize sales service."""
        self.order_repo = OrderRepository()
        self.item_repo = ItemRepository()
        self.stock_repo = StockLedgerRepository()
        self.audit_repo = AuditLogRepository()
        self.db = Database()

    def create_order(self, table_id: Optional[str], created_by: UUID) -> Order:
        """
        Create new draft order.

        Args:
            table_id: Table number or guest name
            created_by: User creating order

        Returns:
            New Order entity (draft status)
        """
        order = Order(
            id=uuid4(),
            table_id=table_id,
            status=OrderStatus.DRAFT,
            subtotal=Money(cents=0),
            discount_amount=Money(cents=0),
            tax_amount=Money(cents=0),
            total_amount=Money(cents=0),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=created_by,
        )
        saved_order = self.order_repo.create(order)

        # Log creation
        self._log_audit(
            entity_type="Order",
            entity_id=order.id,
            operation="CREATE",
            user_id=created_by,
            new_state={"status": "draft", "table_id": table_id},
        )

        return saved_order

    def add_item(
        self,
        order_id: UUID,
        item_id: UUID,
        quantity: int,
        added_by: UUID,
    ) -> Order:
        """
        Add item to order.

        Recalculates totals (subtotal, tax, total).

        Args:
            order_id: Order to add item to
            item_id: Item to add
            quantity: Quantity to add
            added_by: User adding item

        Returns:
            Updated Order

        Raises:
            ValueError: If order finalized or item not found
        """
        order = self.order_repo.get(str(order_id))
        if not order:
            raise ValueError(f"Order {order_id} not found")
        if order.is_finalized:
            raise ValueError("Cannot add items to finalized order")

        item = self.item_repo.get(str(item_id))
        if not item:
            raise ValueError(f"Item {item_id} not found")

        # Create line item
        line_item = OrderLineItem(
            id=uuid4(),
            order_id=order_id,
            item_id=item_id,
            item_name=item.name,
            quantity=quantity,
            unit_price=item.unit_price,
            discount_amount=Money(cents=0),
            tax_amount=Money(cents=0),  # Tax calculated on total
            total_amount=Money(cents=item.unit_price.cents * quantity),
            created_at=datetime.utcnow(),
            created_by=added_by,
        )

        # Recalculate order totals
        new_subtotal = Money(cents=sum(li.total_amount.cents for li in order.line_items) + line_item.total_amount.cents)
        tax_rate = 0.18  # TODO: Make configurable
        new_tax = calculate_tax(new_subtotal, tax_rate)
        new_total = Money(cents=new_subtotal.cents - order.discount_amount.cents + new_tax.cents)

        # TODO: Save line item to database
        # self.line_item_repo.create(line_item)

        # Log addition
        self._log_audit(
            entity_type="OrderLineItem",
            entity_id=line_item.id,
            operation="CREATE",
            user_id=added_by,
            new_state={"order_id": str(order_id), "item_id": str(item_id), "quantity": quantity},
        )

        # Return updated order (for now, return order with updated values)
        return Order(
            id=order.id,
            table_id=order.table_id,
            status=order.status,
            subtotal=new_subtotal,
            discount_amount=order.discount_amount,
            tax_amount=new_tax,
            total_amount=new_total,
            line_items=order.line_items + [line_item],
            created_at=order.created_at,
            updated_at=datetime.utcnow(),
            created_by=order.created_by,
            updated_by=added_by,
        )

    def finalize_order(
        self,
        order_id: UUID,
        payment_method: PaymentMethod,
        paid_amount: Money,
        finalized_by: UUID,
    ) -> Order:
        """
        Finalize order and process payment.

        Transitions status to finalized, deducts stock, assigns receipt number.

        Args:
            order_id: Order to finalize
            payment_method: Payment method (CASH, CARD, etc.)
            paid_amount: Amount paid
            finalized_by: User finalizing order

        Returns:
            Finalized Order

        Raises:
            ValueError: If order not found or already finalized
            InsufficientStockError: If stock insufficient for any item
        """
        order = self.order_repo.get(str(order_id))
        if not order:
            raise ValueError(f"Order {order_id} not found")
        if order.is_finalized:
            raise ValueError("Order already finalized")

        # Validate stock for all items
        for line_item in order.line_items:
            stock = self.stock_repo.compute_stock_on_hand(str(line_item.item_id))
            validate_stock_deduction(stock, line_item.quantity)

        # Deduct stock for each item
        for line_item in order.line_items:
            ledger_entry = StockLedgerEntry(
                id=uuid4(),
                item_id=line_item.item_id,
                transaction_type=TransactionType.SALE,
                quantity_change=-line_item.quantity,
                reason=f"Sale Order {order_id}",
                reference_id=order_id,
                created_at=datetime.utcnow(),
                created_by=finalized_by,
            )
            self.stock_repo.create(ledger_entry)

            # Log stock deduction
            self._log_audit(
                entity_type="StockLedger",
                entity_id=ledger_entry.id,
                operation="CREATE",
                user_id=finalized_by,
                new_state={
                    "item_id": str(line_item.item_id),
                    "qty_change": -line_item.quantity,
                },
            )

        # Assign receipt number
        receipt_seq = self.order_repo.get_last_receipt_number()
        today = datetime.utcnow()
        receipt_number = f"REC-{today.year}-{today.month:02d}{today.day:02d}-{receipt_seq:06d}"

        finalized_at = datetime.utcnow()
        self.order_repo.finalize_order(
            str(order_id),
            receipt_number,
            finalized_by,
            finalized_at,
        )

        # Log finalization
        self._log_audit(
            entity_type="Order",
            entity_id=order_id,
            operation="FINALIZE",
            user_id=finalized_by,
            old_state={"status": "draft"},
            new_state={"status": "finalized", "receipt_number": receipt_number},
        )

        # Return updated order
        return Order(
            id=order.id,
            table_id=order.table_id,
            status=OrderStatus.FINALIZED,
            subtotal=order.subtotal,
            discount_amount=order.discount_amount,
            tax_amount=order.tax_amount,
            total_amount=order.total_amount,
            line_items=order.line_items,
            created_at=order.created_at,
            updated_at=finalized_at,
            created_by=order.created_by,
            updated_by=finalized_by,
            finalized_at=finalized_at,
            finalized_by=finalized_by,
            receipt_number=receipt_number,
        )

    def _log_audit(
        self,
        entity_type: str,
        entity_id: UUID,
        operation: str,
        user_id: UUID,
        old_state: Optional[dict] = None,
        new_state: Optional[dict] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Create audit log entry."""
        from src.domain import AuditLogEntry
        import json

        entry = AuditLogEntry(
            id=uuid4(),
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            old_state=json.dumps(old_state) if old_state else None,
            new_state=json.dumps(new_state) if new_state else None,
            reason=reason,
        )
        self.audit_repo.create(entry)


class InventoryService:
    """Inventory and stock management service."""

    def __init__(self) -> None:
        """Initialize inventory service."""
        self.stock_repo = StockLedgerRepository()
        self.item_repo = ItemRepository()
        self.audit_repo = AuditLogRepository()

    def get_stock_on_hand(self, item_id: UUID) -> int:
        """Get current stock for item."""
        return self.stock_repo.compute_stock_on_hand(str(item_id))

    def record_stock_in(
        self,
        item_id: UUID,
        quantity: int,
        reference: str,
        recorded_by: UUID,
    ) -> StockLedgerEntry:
        """
        Record stock-in (purchase, return, etc.).

        Args:
            item_id: Item to add stock
            quantity: Quantity to add
            reference: PO number, invoice, etc.
            recorded_by: User recording stock-in

        Returns:
            Created StockLedgerEntry
        """
        entry = StockLedgerEntry(
            id=uuid4(),
            item_id=item_id,
            transaction_type=TransactionType.PURCHASE,
            quantity_change=quantity,
            reason=f"Stock-in: {reference}",
            created_at=datetime.utcnow(),
            created_by=recorded_by,
        )
        self.stock_repo.create(entry)

        # Log
        self._log_audit(
            entity_type="StockLedger",
            entity_id=entry.id,
            operation="CREATE",
            user_id=recorded_by,
            new_state={"item_id": str(item_id), "qty_change": quantity},
        )

        return entry

    def get_low_stock_items(self) -> List[Item]:
        """Get all items below reorder level."""
        all_items = self.item_repo.list()
        low_stock = []
        for item in all_items:
            stock = self.get_stock_on_hand(item.id)
            if stock < item.reorder_level:
                low_stock.append(item)
        return low_stock

    def _log_audit(
        self,
        entity_type: str,
        entity_id: UUID,
        operation: str,
        user_id: UUID,
        old_state: Optional[dict] = None,
        new_state: Optional[dict] = None,
    ) -> None:
        """Create audit log entry."""
        from src.domain import AuditLogEntry
        import json

        entry = AuditLogEntry(
            id=uuid4(),
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            old_state=json.dumps(old_state) if old_state else None,
            new_state=json.dumps(new_state) if new_state else None,
        )
        self.audit_repo.create(entry)


# TODO: Implement ReportingService (daily sales, inventory reports)
# TODO: Implement VoidService (order voidance with approval)
# TODO: Implement sync service (Phase 2+)
