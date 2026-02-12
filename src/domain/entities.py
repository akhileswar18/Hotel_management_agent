"""
Domain Layer: Entities

Immutable domain entities representing core business concepts.
No database dependencies, all fields are frozen.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from src.domain.value_objects import Money, OrderStatus, TransactionType, PaymentMethod, Role


@dataclass(frozen=True)
class User:
    """
    User entity representing staff member.

    Immutable once created. PIN is stored separately (hashed) in repository.
    """
    id: UUID
    username: str
    role: Role
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


@dataclass(frozen=True)
class Item:
    """
    Product/Menu item entity.

    Represents a saleable item with fixed pricing (discounts applied separately).
    """
    id: UUID
    name: str
    category: str
    unit_price: Money
    reorder_level: int
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: Optional[UUID] = None


@dataclass(frozen=True)
class OrderLineItem:
    """
    Individual line item in an order.

    Immutable snapshot of item state at time of order.
    """
    id: UUID
    order_id: UUID
    item_id: UUID
    item_name: str
    quantity: int
    unit_price: Money
    discount_amount: Money
    tax_amount: Money
    total_amount: Money
    created_at: datetime
    created_by: UUID


@dataclass(frozen=True)
class Order:
    """
    Order/Bill entity representing a single transaction.

    State transitions: draft → finalized → closed (or voided)
    All monetary fields stored as Money (cents-based).
    """
    id: UUID
    table_id: Optional[str]  # Table number or guest name
    status: OrderStatus
    subtotal: Money
    discount_amount: Money
    tax_amount: Money
    total_amount: Money
    line_items: List[OrderLineItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    finalized_at: Optional[datetime] = None
    finalized_by: Optional[UUID] = None
    receipt_number: Optional[str] = None

    @property
    def item_count(self) -> int:
        """Total number of items in order."""
        return sum(item.quantity for item in self.line_items)

    @property
    def is_finalized(self) -> bool:
        """Check if order is finalized."""
        return self.status == OrderStatus.FINALIZED


@dataclass(frozen=True)
class Payment:
    """
    Payment entity linking payment method to order.

    Immutable record of payment transaction.
    """
    id: UUID
    order_id: UUID
    amount: Money
    method: PaymentMethod
    reference: str  # Receipt number, card ref, voucher code
    finalized_at: datetime
    finalized_by: UUID
    created_by: Optional[UUID] = None


@dataclass(frozen=True)
class StockLedgerEntry:
    """
    Stock ledger entry (append-only).

    Never update, only append. Stock is computed by summing all entries.
    """
    id: UUID
    item_id: UUID
    transaction_type: TransactionType
    quantity_change: int  # Positive for stock-in, negative for sale/wastage
    reason: str
    reference_id: Optional[UUID] = None  # order_id, PO_id, etc.
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None


@dataclass(frozen=True)
class VoidRecord:
    """
    Void record for voided orders (never delete original).

    Immutable audit trail for order cancellations.
    """
    id: UUID
    original_order_id: UUID
    void_reason: str
    voided_at: datetime
    voided_by: UUID
    approved_by: Optional[UUID] = None


@dataclass(frozen=True)
class AuditLogEntry:
    """
    Audit log entry (immutable, append-only).

    Every state-changing operation recorded here.
    """
    id: UUID
    entity_type: str  # "Order", "Payment", "StockLedger", etc.
    entity_id: UUID
    operation: str  # "CREATE", "UPDATE", "VOID", "FINALIZE"
    user_id: UUID
    timestamp: datetime
    old_state: Optional[str] = None  # JSON string
    new_state: Optional[str] = None  # JSON string
    reason: Optional[str] = None


# TODO: Add Supplier entity (Phase 2)
# TODO: Add PurchaseOrder entity (Phase 2)
# TODO: Add LoyaltyAccount entity (Phase 3)
