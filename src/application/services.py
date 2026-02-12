"""
Application Layer: Services

Orchestrates domain logic and repositories.
Zero business logic here; that stays in domain layer.
Services handle transactions, error handling, and workflow coordination.
"""

from uuid import UUID, uuid4
from datetime import datetime, date
from typing import List, Optional, Tuple, Dict, Any
import bcrypt
import json

from src.domain import (
    Order, OrderLineItem, Item, User, StockLedgerEntry, Payment,
    VoidRecord, AuditLogEntry, Money,
    OrderStatus, TransactionType, Role, PaymentMethod,
    calculate_tax, apply_discount, validate_stock_deduction,
    validate_permission, InvalidDiscountError, InsufficientStockError,
)
from src.infrastructure import (
    OrderRepository, ItemRepository, UserRepository,
    StockLedgerRepository, AuditLogRepository,
    PaymentRepository, VoidRecordRepository, Database,
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

        session_token = str(uuid4())
        return user, session_token

    def logout(self, user_id: str) -> None:
        """
        Log out a user by invalidating their session.

        Args:
            user_id: ID of the user to log out

        Note: In Phase 1, sessions are implicit (no server-side session store).
              This method exists for API contract completeness.
        """
        # Phase 1: Session management is client-side (token in memory).
        # Phase 2 will add server-side session invalidation.
        pass

    def hash_pin(self, pin: str) -> str:
        """Hash PIN using bcrypt."""
        return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()

    def can_perform_action(self, user: User, action: str) -> bool:
        """Check if user can perform action."""
        return validate_permission(user.role.value, action)


class SalesService:
    """Sales and order management service."""

    TAX_RATE = 0.18  # 18% GST — configurable in Phase 2

    def __init__(self) -> None:
        """Initialize sales service."""
        self.order_repo = OrderRepository()
        self.item_repo = ItemRepository()
        self.stock_repo = StockLedgerRepository()
        self.audit_repo = AuditLogRepository()
        self.payment_repo = PaymentRepository()
        self.void_repo = VoidRecordRepository()
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

        self._log_audit(
            entity_type="Order",
            entity_id=order.id,
            operation="CREATE",
            user_id=created_by,
            new_state={"status": "draft", "table_id": table_id},
        )

        return saved_order

    def get_order(self, order_id: UUID) -> Optional[Order]:
        """Fetch order by ID."""
        return self.order_repo.get(str(order_id))

    def remove_item(self, order_id: UUID, line_item_id: UUID, user_id: UUID) -> Order:
        """
        Remove a line item from a draft order and recalculate totals.

        Args:
            order_id: Order ID
            line_item_id: Line item ID to remove
            user_id: User performing the action

        Returns:
            Updated Order

        Raises:
            ValueError: If order not found or not in draft status
        """
        order = self.order_repo.get(str(order_id))
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order.status != OrderStatus.DRAFT:
            raise ValueError("Can only remove items from draft orders")

        # Verify line item belongs to this order
        matching = [li for li in order.line_items if str(li.id) == str(line_item_id)]
        if not matching:
            raise ValueError(f"Line item {line_item_id} not found in order {order_id}")

        # Remove from DB
        self.order_repo.remove_line_item(str(line_item_id), str(order_id))

        # Recalculate totals from remaining items
        updated_order = self.order_repo.get(str(order_id))
        subtotal_cents = sum(li.total_amount.cents for li in updated_order.line_items)
        discount_cents = updated_order.discount_amount.cents
        tax_cents = calculate_tax(Money(cents=subtotal_cents - discount_cents), self.TAX_RATE).cents
        total_cents = subtotal_cents - discount_cents + tax_cents

        self.order_repo.update_order_totals(
            order_id=str(order_id),
            subtotal_cents=subtotal_cents,
            discount_cents=discount_cents,
            tax_cents=tax_cents,
            total_cents=total_cents,
            updated_by=user_id,
        )

        return self.order_repo.get(str(order_id))

    def update_item_quantity(self, order_id: UUID, line_item_id: UUID, new_quantity: int, user_id: UUID) -> Order:
        """
        Update the quantity of an existing line item in a draft order.

        Args:
            order_id: Order ID
            line_item_id: Line item ID to update
            new_quantity: New quantity (must be > 0)
            user_id: User performing the action

        Returns:
            Updated Order

        Raises:
            ValueError: If order not found, not draft, or invalid quantity
        """
        if new_quantity <= 0:
            raise ValueError("Quantity must be positive")

        order = self.order_repo.get(str(order_id))
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order.status != OrderStatus.DRAFT:
            raise ValueError("Can only edit items in draft orders")

        matching = [li for li in order.line_items if str(li.id) == str(line_item_id)]
        if not matching:
            raise ValueError(f"Line item {line_item_id} not found in order {order_id}")

        li = matching[0]
        # Update line item in DB
        new_total_cents = li.unit_price.cents * new_quantity
        self.order_repo.update_line_item_quantity(str(line_item_id), new_quantity, new_total_cents)

        # Recalculate order totals
        updated_order = self.order_repo.get(str(order_id))
        subtotal_cents = sum(item.total_amount.cents for item in updated_order.line_items)
        discount_cents = updated_order.discount_amount.cents
        tax_cents = calculate_tax(Money(cents=subtotal_cents - discount_cents), self.TAX_RATE).cents
        total_cents = subtotal_cents - discount_cents + tax_cents

        self.order_repo.update_order_totals(
            order_id=str(order_id),
            subtotal_cents=subtotal_cents,
            discount_cents=discount_cents,
            tax_cents=tax_cents,
            total_cents=total_cents,
            updated_by=user_id,
        )

        return self.order_repo.get(str(order_id))

    def hold_order(self, order_id: UUID, user_id: UUID) -> Order:
        """Put a draft order on hold."""
        order = self.order_repo.get(str(order_id))
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order.status != OrderStatus.DRAFT:
            raise ValueError("Can only hold draft orders")

        self.order_repo.set_order_status(str(order_id), "held", user_id)
        return self.order_repo.get(str(order_id))

    def resume_order(self, order_id: UUID, user_id: UUID) -> Order:
        """Resume a held order back to draft."""
        order = self.order_repo.get(str(order_id))
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order.status.value != "held":
            raise ValueError("Can only resume held orders")

        self.order_repo.set_order_status(str(order_id), "draft", user_id)
        return self.order_repo.get(str(order_id))

    def list_orders(self, status: str = None, date_str: str = None) -> list:
        """List orders with optional status and date filters."""
        return self.order_repo.list_filtered(status=status, date_str=date_str)

    def add_item(
        self,
        order_id: UUID,
        item_id: UUID,
        quantity: int,
        added_by: UUID,
    ) -> Order:
        """
        Add item to order. Persists line item to DB and recalculates totals.

        Args:
            order_id: Order to add item to
            item_id: Item to add
            quantity: Quantity to add (must be > 0)
            added_by: User adding item

        Returns:
            Updated Order with new line item and recalculated totals

        Raises:
            ValueError: If order finalized, item not found, or invalid quantity
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        order = self.order_repo.get(str(order_id))
        if not order:
            raise ValueError(f"Order {order_id} not found")
        if order.status == OrderStatus.VOIDED:
            raise ValueError("Cannot add items to voided order")
        if order.is_finalized:
            raise ValueError("Cannot add items to finalized order")

        item = self.item_repo.get(str(item_id))
        if not item:
            raise ValueError(f"Item {item_id} not found")

        # Create line item
        line_total = Money(cents=item.unit_price.cents * quantity)
        line_item = OrderLineItem(
            id=uuid4(),
            order_id=order_id,
            item_id=item_id,
            item_name=item.name,
            quantity=quantity,
            unit_price=item.unit_price,
            discount_amount=Money(cents=0),
            tax_amount=Money(cents=0),
            total_amount=line_total,
            created_at=datetime.utcnow(),
            created_by=added_by,
        )

        # Persist line item to DB
        self.order_repo.create_line_item(line_item)

        # Recalculate order totals
        new_subtotal = Money(
            cents=sum(li.total_amount.cents for li in order.line_items) + line_total.cents
        )
        new_tax = calculate_tax(new_subtotal, self.TAX_RATE)
        new_total = Money(
            cents=new_subtotal.cents - order.discount_amount.cents + new_tax.cents
        )

        # Persist updated totals to DB
        self.order_repo.update_order_totals(
            order_id=str(order_id),
            subtotal_cents=new_subtotal.cents,
            discount_cents=order.discount_amount.cents,
            tax_cents=new_tax.cents,
            total_cents=new_total.cents,
            updated_by=added_by,
        )

        # Audit log
        self._log_audit(
            entity_type="OrderLineItem",
            entity_id=line_item.id,
            operation="CREATE",
            user_id=added_by,
            new_state={
                "order_id": str(order_id),
                "item_id": str(item_id),
                "item_name": item.name,
                "quantity": quantity,
                "line_total_cents": line_total.cents,
            },
        )

        # Return the refreshed order from DB (ensures consistency)
        return self.order_repo.get(str(order_id))

    def apply_order_discount(
        self,
        order_id: UUID,
        discount_type: str,
        amount: float,
        applied_by: UUID,
    ) -> Order:
        """
        Apply a discount to an order.

        Args:
            order_id: Order to apply discount to
            discount_type: 'percentage' or 'absolute'
            amount: Discount value (0-50 for percentage, cents for absolute)
            applied_by: User applying the discount

        Returns:
            Updated Order

        Raises:
            ValueError: If order not draft or discount invalid
            InvalidDiscountError: If discount exceeds limits
        """
        order = self.order_repo.get(str(order_id))
        if not order:
            raise ValueError(f"Order {order_id} not found")
        if order.is_finalized:
            raise ValueError("Cannot apply discount to finalized order")
        if order.subtotal.cents == 0:
            raise ValueError("Cannot apply discount to empty order")

        old_discount = order.discount_amount

        # Use domain business rule for discount validation
        discounted_subtotal = apply_discount(order.subtotal, discount_type, amount)
        new_discount = Money(cents=order.subtotal.cents - discounted_subtotal.cents)

        # Recalculate totals
        after_discount = Money(cents=order.subtotal.cents - new_discount.cents)
        new_tax = calculate_tax(after_discount, self.TAX_RATE)
        new_total = Money(cents=after_discount.cents + new_tax.cents)

        # Persist
        self.order_repo.update_order_totals(
            order_id=str(order_id),
            subtotal_cents=order.subtotal.cents,
            discount_cents=new_discount.cents,
            tax_cents=new_tax.cents,
            total_cents=new_total.cents,
            updated_by=applied_by,
        )

        self._log_audit(
            entity_type="Order",
            entity_id=order_id,
            operation="UPDATE",
            user_id=applied_by,
            old_state={"discount_cents": old_discount.cents},
            new_state={"discount_cents": new_discount.cents, "discount_type": discount_type, "discount_amount": amount},
        )

        return self.order_repo.get(str(order_id))

    def finalize_order(
        self,
        order_id: UUID,
        payment_method: PaymentMethod,
        paid_amount: Money,
        finalized_by: UUID,
    ) -> Order:
        """
        Finalize order and process payment.

        Transitions status to finalized, deducts stock, assigns receipt number,
        and records payment in the payments table.

        Args:
            order_id: Order to finalize
            payment_method: Payment method (CASH, CARD, VOUCHER)
            paid_amount: Amount paid
            finalized_by: User finalizing order

        Returns:
            Finalized Order

        Raises:
            ValueError: If order not found, already finalized, or has no items
            InsufficientStockError: If stock insufficient for any item
        """
        order = self.order_repo.get(str(order_id))
        if not order:
            raise ValueError(f"Order {order_id} not found")
        if order.is_finalized:
            raise ValueError("Order already finalized")
        if order.status == OrderStatus.VOIDED:
            raise ValueError("Cannot finalize voided order")
        if not order.line_items:
            raise ValueError("Cannot finalize order with no items")

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

        # Record payment in payments table
        payment = Payment(
            id=uuid4(),
            order_id=order_id,
            amount=paid_amount,
            method=payment_method,
            reference=receipt_number,
            finalized_at=finalized_at,
            finalized_by=finalized_by,
            created_by=finalized_by,
        )
        self.payment_repo.create(payment)

        # Log finalization
        self._log_audit(
            entity_type="Order",
            entity_id=order_id,
            operation="FINALIZE",
            user_id=finalized_by,
            old_state={"status": "draft"},
            new_state={
                "status": "finalized",
                "receipt_number": receipt_number,
                "payment_method": payment_method.value,
                "paid_amount_cents": paid_amount.cents,
            },
        )

        # Return refreshed order from DB
        return self.order_repo.get(str(order_id))

    def void_order(
        self,
        order_id: UUID,
        reason: str,
        voided_by: UUID,
        approved_by: Optional[UUID] = None,
    ) -> Order:
        """
        Void an order. Requires a reason and optionally manager approval.

        Args:
            order_id: Order to void
            reason: Why the order is being voided
            voided_by: User voiding the order
            approved_by: Manager who approved the void (optional)

        Returns:
            Voided Order

        Raises:
            ValueError: If order not found or already voided
        """
        order = self.order_repo.get(str(order_id))
        if not order:
            raise ValueError(f"Order {order_id} not found")
        if order.status == OrderStatus.VOIDED:
            raise ValueError("Order already voided")

        # Mark order as voided
        self.order_repo.void_order(str(order_id), voided_by)

        # Record void in void_records table
        void_record = VoidRecord(
            id=uuid4(),
            original_order_id=order_id,
            void_reason=reason,
            voided_at=datetime.utcnow(),
            voided_by=voided_by,
            approved_by=approved_by,
        )
        self.void_repo.create(void_record)

        # If order was finalized, reverse stock deductions
        if order.is_finalized:
            for line_item in order.line_items:
                reversal = StockLedgerEntry(
                    id=uuid4(),
                    item_id=line_item.item_id,
                    transaction_type=TransactionType.RETURN,
                    quantity_change=line_item.quantity,
                    reason=f"Void reversal for Order {order_id}",
                    reference_id=order_id,
                    created_at=datetime.utcnow(),
                    created_by=voided_by,
                )
                self.stock_repo.create(reversal)

        # Audit log
        self._log_audit(
            entity_type="Order",
            entity_id=order_id,
            operation="VOID",
            user_id=voided_by,
            old_state={"status": order.status.value},
            new_state={"status": "voided", "void_reason": reason},
            reason=reason,
        )

        return self.order_repo.get(str(order_id))

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
            quantity: Quantity to add (must be > 0)
            reference: PO number, invoice, etc.
            recorded_by: User recording stock-in

        Returns:
            Created StockLedgerEntry
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

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

        self._log_audit(
            entity_type="StockLedger",
            entity_id=entry.id,
            operation="CREATE",
            user_id=recorded_by,
            new_state={"item_id": str(item_id), "qty_change": quantity, "reference": reference},
        )

        return entry

    def record_adjustment(
        self,
        item_id: UUID,
        quantity_change: int,
        reason: str,
        adjusted_by: UUID,
    ) -> StockLedgerEntry:
        """
        Record stock adjustment (recount, wastage, etc.).

        Args:
            item_id: Item to adjust
            quantity_change: Positive or negative change
            reason: Reason for adjustment
            adjusted_by: User performing adjustment

        Returns:
            Created StockLedgerEntry
        """
        entry = StockLedgerEntry(
            id=uuid4(),
            item_id=item_id,
            transaction_type=TransactionType.ADJUSTMENT,
            quantity_change=quantity_change,
            reason=reason,
            created_at=datetime.utcnow(),
            created_by=adjusted_by,
        )
        self.stock_repo.create(entry)

        self._log_audit(
            entity_type="StockLedger",
            entity_id=entry.id,
            operation="CREATE",
            user_id=adjusted_by,
            new_state={
                "item_id": str(item_id),
                "qty_change": quantity_change,
                "reason": reason,
            },
        )

        return entry

    def create_item(
        self,
        name: str,
        category: str,
        unit_price: Money,
        reorder_level: int,
        created_by: UUID,
    ) -> Item:
        """
        Create a new inventory item / product.

        Args:
            name: Product name
            category: Product category
            unit_price: Price per unit (Money)
            reorder_level: Minimum stock level before low-stock alert
            created_by: User creating the item

        Returns:
            Created Item entity
        """
        item = Item(
            id=uuid4(),
            name=name,
            category=category,
            unit_price=unit_price,
            reorder_level=reorder_level,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=created_by,
        )
        self.item_repo.create(item)

        self._log_audit(
            entity_type="Item",
            entity_id=item.id,
            operation="CREATE",
            user_id=created_by,
            new_state={
                "name": name,
                "category": category,
                "unit_price_cents": unit_price.cents,
                "reorder_level": reorder_level,
            },
        )

        return item

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

    def update_item(
        self,
        item_id: UUID,
        updated_by: UUID,
        unit_price: Optional[Money] = None,
        reorder_level: Optional[int] = None,
    ) -> Item:
        """
        Update an existing inventory item's price and/or reorder level.

        Args:
            item_id: Item to update
            updated_by: User performing the update
            unit_price: New price (optional)
            reorder_level: New reorder level (optional)

        Returns:
            Updated Item entity
        """
        item = self.item_repo.get(str(item_id))
        if item is None:
            raise ValueError(f"Item {item_id} not found")

        old_state = {
            "unit_price": item.unit_price.to_float(),
            "reorder_level": item.reorder_level,
        }

        self.item_repo.update_item(
            item_id=str(item_id),
            unit_price_cents=unit_price.cents if unit_price else None,
            reorder_level=reorder_level,
            updated_by=str(updated_by),
        )

        updated = self.item_repo.get(str(item_id))

        self._log_audit(
            entity_type="Item",
            entity_id=item_id,
            operation="UPDATE",
            user_id=updated_by,
            old_state=old_state,
            new_state={
                "unit_price": updated.unit_price.to_float(),
                "reorder_level": updated.reorder_level,
            },
        )

        return updated


class ReportingService:
    """Reporting and analytics service (read-only queries)."""

    def __init__(self) -> None:
        """Initialize reporting service."""
        self.order_repo = OrderRepository()
        self.item_repo = ItemRepository()
        self.stock_repo = StockLedgerRepository()
        self.payment_repo = PaymentRepository()
        self.audit_repo = AuditLogRepository()
        self.db = Database()

    def daily_sales_summary(self, report_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Generate daily sales summary.

        Args:
            report_date: Date for report (defaults to today)

        Returns:
            Dict with total revenue, transaction count, payment method breakdown, top items
        """
        if report_date is None:
            report_date = date.today()

        target_dt = datetime(report_date.year, report_date.month, report_date.day)

        # Get payment summary from DB
        payment_summary = self.payment_repo.get_daily_summary(target_dt)

        # Get orders for the date to find top items
        orders = self.order_repo.get_orders_by_date(target_dt)
        finalized_orders = [o for o in orders if o.status == OrderStatus.FINALIZED]

        # Aggregate top items
        item_sales: Dict[str, Dict[str, Any]] = {}
        for order in finalized_orders:
            for li in order.line_items:
                key = str(li.item_id)
                if key not in item_sales:
                    item_sales[key] = {
                        "item_name": li.item_name,
                        "quantity_sold": 0,
                        "revenue_cents": 0,
                    }
                item_sales[key]["quantity_sold"] += li.quantity
                item_sales[key]["revenue_cents"] += li.total_amount.cents

        # Sort by quantity sold, take top 5
        top_items = sorted(
            item_sales.values(),
            key=lambda x: x["quantity_sold"],
            reverse=True,
        )[:5]

        total_revenue_cents = payment_summary.get("total_revenue_cents", 0)
        transaction_count = payment_summary.get("transaction_count", 0)

        return {
            "date": report_date.isoformat(),
            "total_revenue": total_revenue_cents / 100.0,
            "total_revenue_cents": total_revenue_cents,
            "transaction_count": transaction_count,
            "average_order_value": (
                round(total_revenue_cents / transaction_count / 100.0, 2)
                if transaction_count > 0
                else 0.0
            ),
            "payment_methods": {
                method: {
                    "count": data["count"],
                    "total": data["total_cents"] / 100.0,
                }
                for method, data in payment_summary.get("by_method", {}).items()
            },
            "top_items": [
                {
                    "name": item["item_name"],
                    "quantity_sold": item["quantity_sold"],
                    "revenue": item["revenue_cents"] / 100.0,
                }
                for item in top_items
            ],
            "orders_count": len(finalized_orders),
            "voided_count": sum(1 for o in orders if o.status == OrderStatus.VOIDED),
        }

    def inventory_snapshot(self) -> Dict[str, Any]:
        """
        Generate current inventory snapshot.

        Returns:
            Dict with all items, stock levels, and low-stock alerts
        """
        items = self.item_repo.list()
        inventory = []
        low_stock_items = []

        for item in items:
            stock = self.stock_repo.compute_stock_on_hand(str(item.id))
            item_data = {
                "id": str(item.id),
                "name": item.name,
                "category": item.category,
                "unit_price": item.unit_price.to_float(),
                "stock_on_hand": stock,
                "reorder_level": item.reorder_level,
                "is_low_stock": stock < item.reorder_level,
            }
            inventory.append(item_data)
            if stock < item.reorder_level:
                low_stock_items.append(item_data)

        return {
            "total_items": len(items),
            "low_stock_count": len(low_stock_items),
            "inventory": inventory,
            "low_stock_items": low_stock_items,
        }

    def search_transactions(self, start_date: str = None, end_date: str = None, payment_method: str = None) -> list:
        """
        Search finalized orders (transactions) with optional filters.

        Args:
            start_date: ISO date string (YYYY-MM-DD) — inclusive
            end_date: ISO date string (YYYY-MM-DD) — inclusive
            payment_method: Filter by payment method (CASH, CARD, VOUCHER)

        Returns:
            List of dicts with order + payment info
        """
        query = """
            SELECT o.id, o.table_id, o.status, o.subtotal_cents, o.discount_cents,
                   o.tax_cents, o.total_cents, o.receipt_number, o.finalized_at, o.created_at,
                   p.payment_method, p.amount_cents as paid_cents
            FROM orders o
            LEFT JOIN payments p ON o.id = p.order_id
            WHERE o.status = 'finalized'
        """
        params = []
        if start_date:
            query += " AND DATE(o.finalized_at) >= DATE(?)"
            params.append(start_date)
        if end_date:
            query += " AND DATE(o.finalized_at) <= DATE(?)"
            params.append(end_date)
        if payment_method:
            query += " AND p.payment_method = ?"
            params.append(payment_method)
        query += " ORDER BY o.finalized_at DESC"

        cursor = self.db.execute(query, tuple(params))
        results = []
        for row in cursor.fetchall():
            results.append({
                "order_id": row["id"],
                "table_id": row["table_id"],
                "subtotal": row["subtotal_cents"] / 100.0,
                "discount": row["discount_cents"] / 100.0,
                "tax": row["tax_cents"] / 100.0,
                "total": row["total_cents"] / 100.0,
                "receipt_number": row["receipt_number"],
                "finalized_at": row["finalized_at"],
                "payment_method": row["payment_method"],
                "paid_amount": row["paid_cents"] / 100.0 if row["paid_cents"] else 0.0,
            })
        return results
