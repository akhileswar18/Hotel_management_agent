"""
Infrastructure Layer: Repository Pattern

Data access abstraction over SQLite.
Repositories handle all database operations and return domain entities.
"""

import sqlite3
import json
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
from uuid import UUID
from datetime import datetime

from src.domain import (
    Order, OrderLineItem, Item, Payment, User, StockLedgerEntry,
    AuditLogEntry, OrderStatus, TransactionType, Role, Money, PaymentMethod
)
from src.infrastructure.database import Database


class BaseRepository(ABC):
    """
    Abstract base repository.

    Provides common CRUD interface. All repositories subclass this.
    """

    def __init__(self) -> None:
        """Initialize with database connection."""
        self.db = Database()
        if self.db._connection is None:
            raise RuntimeError("Database not initialized")
        self.conn = self.db._connection

    @abstractmethod
    def create(self, entity: Any) -> Any:
        """Create entity in database."""
        pass

    @abstractmethod
    def get(self, entity_id: str) -> Optional[Any]:
        """Get entity by ID."""
        pass

    @abstractmethod
    def list(self) -> List[Any]:
        """List all entities."""
        pass


class OrderRepository(BaseRepository):
    """Repository for Order entities."""

    def create(self, order: Order) -> Order:
        """Create new order."""
        query = """
            INSERT INTO orders (
                id, table_id, status, subtotal_cents, discount_cents,
                tax_cents, total_cents, created_at, updated_at,
                created_by, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            str(order.id),
            order.table_id,
            order.status.value,
            order.subtotal.cents,
            order.discount_amount.cents,
            order.tax_amount.cents,
            order.total_amount.cents,
            order.created_at.isoformat() + "Z",
            order.updated_at.isoformat() + "Z",
            str(order.created_by),
            str(order.updated_by) if order.updated_by else None,
        )
        self.conn.execute(query, params)
        self.conn.commit()
        return order

    def get(self, order_id: str) -> Optional[Order]:
        """Fetch order by ID with line items."""
        query = "SELECT * FROM orders WHERE id = ?"
        cursor = self.conn.execute(query, (order_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_order(row)

    def get_by_receipt_number(self, receipt_number: str) -> Optional[Order]:
        """Fetch order by receipt number (for finalized orders)."""
        query = "SELECT * FROM orders WHERE receipt_number = ?"
        cursor = self.conn.execute(query, (receipt_number,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_order(row)

    def list(self) -> List[Order]:
        """List all orders."""
        query = "SELECT * FROM orders ORDER BY created_at DESC"
        cursor = self.conn.execute(query)
        return [self._row_to_order(row) for row in cursor.fetchall()]

    def finalize_order(
        self,
        order_id: str,
        receipt_number: str,
        finalized_by: UUID,
        finalized_at: datetime,
    ) -> None:
        """Finalize order (mark as finalized, assign receipt number)."""
        query = """
            UPDATE orders
            SET status = 'finalized', receipt_number = ?,
                finalized_at = ?, finalized_by = ?, updated_at = ?
            WHERE id = ?
        """
        params = (
            receipt_number,
            finalized_at.isoformat() + "Z",
            str(finalized_by),
            finalized_at.isoformat() + "Z",
            order_id,
        )
        self.conn.execute(query, params)
        self.conn.commit()

    def get_last_receipt_number(self) -> int:
        """Get sequence number for next receipt."""
        query = "SELECT COUNT(*) FROM orders WHERE status = 'finalized'"
        cursor = self.conn.execute(query)
        count = cursor.fetchone()[0]
        return count + 1

    def get_orders_by_date(self, date: datetime) -> List[Order]:
        """Get all orders for a specific date."""
        query = """
            SELECT * FROM orders
            WHERE DATE(created_at) = DATE(?)
            ORDER BY created_at DESC
        """
        cursor = self.conn.execute(query, (date.isoformat(),))
        return [self._row_to_order(row) for row in cursor.fetchall()]

    def _row_to_order(self, row: sqlite3.Row) -> Order:
        """Convert database row to Order entity."""
        order_id = UUID(row["id"])
        # Fetch line items
        line_items_query = "SELECT * FROM order_line_items WHERE order_id = ?"
        cursor = self.conn.execute(line_items_query, (str(order_id),))
        line_items = [self._lineitem_row_to_entity(li_row) for li_row in cursor.fetchall()]

        return Order(
            id=order_id,
            table_id=row["table_id"],
            status=OrderStatus(row["status"]),
            subtotal=Money(cents=row["subtotal_cents"]),
            discount_amount=Money(cents=row["discount_cents"]),
            tax_amount=Money(cents=row["tax_cents"]),
            total_amount=Money(cents=row["total_cents"]),
            line_items=line_items,
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
            created_by=UUID(row["created_by"]),
            updated_by=UUID(row["updated_by"]) if row["updated_by"] else None,
            finalized_at=datetime.fromisoformat(row["finalized_at"].replace("Z", "+00:00")) if row["finalized_at"] else None,
            finalized_by=UUID(row["finalized_by"]) if row["finalized_by"] else None,
            receipt_number=row["receipt_number"],
        )

    def create_line_item(self, line_item: OrderLineItem) -> OrderLineItem:
        """Insert a line item into the database."""
        query = """
            INSERT INTO order_line_items (
                id, order_id, item_id, item_name, quantity,
                unit_price_cents, discount_cents, tax_cents,
                total_cents, created_at, created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            str(line_item.id),
            str(line_item.order_id),
            str(line_item.item_id),
            line_item.item_name,
            line_item.quantity,
            line_item.unit_price.cents,
            line_item.discount_amount.cents,
            line_item.tax_amount.cents,
            line_item.total_amount.cents,
            line_item.created_at.isoformat() + "Z",
            str(line_item.created_by),
        )
        self.conn.execute(query, params)
        self.conn.commit()
        return line_item

    def update_order_totals(
        self,
        order_id: str,
        subtotal_cents: int,
        discount_cents: int,
        tax_cents: int,
        total_cents: int,
        updated_by: UUID,
    ) -> None:
        """Update order monetary totals after adding/removing items."""
        query = """
            UPDATE orders
            SET subtotal_cents = ?, discount_cents = ?, tax_cents = ?,
                total_cents = ?, updated_at = ?, updated_by = ?
            WHERE id = ?
        """
        params = (
            subtotal_cents,
            discount_cents,
            tax_cents,
            total_cents,
            datetime.utcnow().isoformat() + "Z",
            str(updated_by),
            order_id,
        )
        self.conn.execute(query, params)
        self.conn.commit()

    def void_order(self, order_id: str, voided_by: UUID) -> None:
        """Mark order as voided."""
        query = """
            UPDATE orders
            SET status = 'voided', updated_at = ?, updated_by = ?
            WHERE id = ?
        """
        params = (
            datetime.utcnow().isoformat() + "Z",
            str(voided_by),
            order_id,
        )
        self.conn.execute(query, params)
        self.conn.commit()

    def remove_line_item(self, line_item_id: str, order_id: str) -> None:
        """Remove a line item from a draft order."""
        query = "DELETE FROM order_line_items WHERE id = ? AND order_id = ?"
        self.conn.execute(query, (line_item_id, order_id))
        self.conn.commit()

    def update_line_item_quantity(self, line_item_id: str, new_quantity: int, new_total_cents: int) -> None:
        """Update a line item's quantity and total."""
        query = "UPDATE order_line_items SET quantity = ?, total_cents = ? WHERE id = ?"
        self.conn.execute(query, (new_quantity, new_total_cents, line_item_id))
        self.conn.commit()

    def set_order_status(self, order_id: str, status: str, updated_by: UUID) -> None:
        """Set order status to any value."""
        query = """
            UPDATE orders
            SET status = ?, updated_at = ?, updated_by = ?
            WHERE id = ?
        """
        params = (status, datetime.utcnow().isoformat() + "Z", str(updated_by), order_id)
        self.conn.execute(query, params)
        self.conn.commit()

    def list_filtered(self, status: str = None, date_str: str = None) -> list:
        """List orders with optional status and date filters."""
        query = "SELECT * FROM orders WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if date_str:
            query += " AND DATE(created_at) = DATE(?)"
            params.append(date_str)
        query += " ORDER BY created_at DESC"
        cursor = self.conn.execute(query, params)
        return [self._row_to_order(row) for row in cursor.fetchall()]

    @staticmethod
    def _lineitem_row_to_entity(row: sqlite3.Row) -> OrderLineItem:
        """Convert line item row to entity."""
        return OrderLineItem(
            id=UUID(row["id"]),
            order_id=UUID(row["order_id"]),
            item_id=UUID(row["item_id"]),
            item_name=row["item_name"],
            quantity=row["quantity"],
            unit_price=Money(cents=row["unit_price_cents"]),
            discount_amount=Money(cents=row["discount_cents"]),
            tax_amount=Money(cents=row["tax_cents"]),
            total_amount=Money(cents=row["total_cents"]),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            created_by=UUID(row["created_by"]),
        )


class ItemRepository(BaseRepository):
    """Repository for Item/Product entities."""

    def create(self, item: Item) -> Item:
        """Create new item."""
        query = """
            INSERT INTO items (
                id, name, category, unit_price_cents, reorder_level,
                created_at, updated_at, created_by, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            str(item.id),
            item.name,
            item.category,
            item.unit_price.cents,
            item.reorder_level,
            item.created_at.isoformat() + "Z",
            item.updated_at.isoformat() + "Z",
            str(item.created_by),
            str(item.updated_by) if item.updated_by else None,
        )
        self.conn.execute(query, params)
        self.conn.commit()
        return item

    def get(self, item_id: str) -> Optional[Item]:
        """Get item by ID."""
        query = "SELECT * FROM items WHERE id = ?"
        cursor = self.conn.execute(query, (item_id,))
        row = cursor.fetchone()
        return self._row_to_item(row) if row else None

    def list(self) -> List[Item]:
        """List all items."""
        query = "SELECT * FROM items ORDER BY category, name"
        cursor = self.conn.execute(query)
        return [self._row_to_item(row) for row in cursor.fetchall()]

    def list_by_category(self, category: str) -> List[Item]:
        """List items by category."""
        query = "SELECT * FROM items WHERE category = ? ORDER BY name"
        cursor = self.conn.execute(query, (category,))
        return [self._row_to_item(row) for row in cursor.fetchall()]

    def update_item(self, item_id: str, unit_price_cents: Optional[int] = None,
                    reorder_level: Optional[int] = None, updated_by: Optional[str] = None) -> None:
        """Update item price and/or reorder level."""
        updates = []
        params = []
        if unit_price_cents is not None:
            updates.append("unit_price_cents = ?")
            params.append(unit_price_cents)
        if reorder_level is not None:
            updates.append("reorder_level = ?")
            params.append(reorder_level)
        if not updates:
            return
        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat() + "Z")
        if updated_by:
            updates.append("updated_by = ?")
            params.append(updated_by)
        params.append(item_id)
        query = f"UPDATE items SET {', '.join(updates)} WHERE id = ?"
        self.conn.execute(query, params)
        self.conn.commit()

    def archive_item(self, item_id: str, updated_by: str = None) -> None:
        """Soft-delete an item by setting is_active = 0."""
        from datetime import datetime
        query = "UPDATE items SET is_active = 0, updated_at = ?, updated_by = ? WHERE id = ?"
        params = (datetime.utcnow().isoformat() + "Z", updated_by, item_id)
        self.conn.execute(query, params)
        self.conn.commit()

    def list_active(self) -> list:
        """List only active (non-archived) items."""
        query = "SELECT * FROM items WHERE is_active = 1 ORDER BY category, name"
        cursor = self.conn.execute(query)
        return [self._row_to_item(row) for row in cursor.fetchall()]

    def list_by_category_active(self, category: str) -> list:
        """List active items by category."""
        query = "SELECT * FROM items WHERE category = ? AND is_active = 1 ORDER BY name"
        cursor = self.conn.execute(query, (category,))
        return [self._row_to_item(row) for row in cursor.fetchall()]

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> Item:
        """Convert database row to Item entity."""
        return Item(
            id=UUID(row["id"]),
            name=row["name"],
            category=row["category"],
            unit_price=Money(cents=row["unit_price_cents"]),
            reorder_level=row["reorder_level"],
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
            created_by=UUID(row["created_by"]),
            updated_by=UUID(row["updated_by"]) if row["updated_by"] else None,
        )


class UserRepository(BaseRepository):
    """Repository for User entities."""

    def create(self, user: User, pin_hash: str) -> User:
        """Create new user with hashed PIN."""
        query = """
            INSERT INTO users (id, username, pin_hash, role, created_at, updated_at, created_by, updated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            str(user.id),
            user.username,
            pin_hash,
            user.role.value,
            user.created_at.isoformat() + "Z",
            user.updated_at.isoformat() + "Z",
            str(user.created_by) if user.created_by else None,
            str(user.updated_by) if user.updated_by else None,
        )
        self.conn.execute(query, params)
        self.conn.commit()
        return user

    def get(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        query = "SELECT id, username, role, created_at, updated_at, created_by, updated_by FROM users WHERE id = ?"
        cursor = self.conn.execute(query, (user_id,))
        row = cursor.fetchone()
        return self._row_to_user(row) if row else None

    def get_by_username(self, username: str) -> Optional[tuple]:
        """Get user by username (returns tuple of (User, pin_hash))."""
        query = "SELECT id, username, role, pin_hash, created_at, updated_at, created_by, updated_by FROM users WHERE username = ?"
        cursor = self.conn.execute(query, (username,))
        row = cursor.fetchone()
        if not row:
            return None
        user = self._row_to_user(row)
        pin_hash = row["pin_hash"]
        return (user, pin_hash)

    def list(self) -> List[User]:
        """List all users."""
        query = "SELECT id, username, role, created_at, updated_at, created_by, updated_by FROM users"
        cursor = self.conn.execute(query)
        return [self._row_to_user(row) for row in cursor.fetchall()]

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        """Convert database row to User entity."""
        return User(
            id=UUID(row["id"]),
            username=row["username"],
            role=Role(row["role"]),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
            created_by=UUID(row["created_by"]) if row["created_by"] else None,
            updated_by=UUID(row["updated_by"]) if row["updated_by"] else None,
        )


class SessionRepository(BaseRepository):
    """Repository for server-side session management."""

    def create(self, entity: Any) -> Any:
        """Not used; use create_session instead."""
        raise NotImplementedError("Use create_session(session_id, user_id, expires_at)")

    def get(self, entity_id: str) -> Optional[Any]:
        """Get session by ID. Delegates to get_session."""
        return self.get_session(entity_id)

    def list(self) -> List[Any]:
        """List active sessions (minimal implementation for BaseRepository)."""
        return []

    def create_session(self, session_id: str, user_id: str, expires_at: str) -> None:
        """Create a new session record."""
        from datetime import datetime
        query = """
            INSERT INTO sessions (id, user_id, login_at, expires_at)
            VALUES (?, ?, ?, ?)
        """
        params = (session_id, user_id, datetime.utcnow().isoformat() + "Z", expires_at)
        self.conn.execute(query, params)
        self.conn.commit()

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session by ID. Returns None if not found or expired."""
        query = "SELECT * FROM sessions WHERE id = ? AND logout_at IS NULL"
        cursor = self.conn.execute(query, (session_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "login_at": row["login_at"],
            "expires_at": row["expires_at"],
            "logout_at": row["logout_at"],
        }

    def invalidate_session(self, session_id: str) -> None:
        """Mark session as logged out."""
        from datetime import datetime
        query = "UPDATE sessions SET logout_at = ? WHERE id = ?"
        self.conn.execute(query, (datetime.utcnow().isoformat() + "Z", session_id))
        self.conn.commit()

    def refresh_session(self, session_id: str, new_expires_at: str) -> None:
        """Extend session expiry (called on each valid request)."""
        query = "UPDATE sessions SET expires_at = ? WHERE id = ? AND logout_at IS NULL"
        self.conn.execute(query, (new_expires_at, session_id))
        self.conn.commit()

    def invalidate_user_sessions(self, user_id: str) -> None:
        """Invalidate all sessions for a user (used on password change or deactivation)."""
        from datetime import datetime
        query = "UPDATE sessions SET logout_at = ? WHERE user_id = ? AND logout_at IS NULL"
        self.conn.execute(query, (datetime.utcnow().isoformat() + "Z", user_id))
        self.conn.commit()

    def cleanup_expired(self) -> int:
        """Mark expired sessions as logged out. Returns count cleaned."""
        from datetime import datetime
        now = datetime.utcnow().isoformat() + "Z"
        query = "UPDATE sessions SET logout_at = ? WHERE expires_at < ? AND logout_at IS NULL"
        cursor = self.conn.execute(query, (now, now))
        self.conn.commit()
        return cursor.rowcount


class StockLedgerRepository(BaseRepository):
    """Repository for StockLedgerEntry entities (append-only)."""

    def create(self, entry: StockLedgerEntry) -> StockLedgerEntry:
        """Append entry to stock ledger."""
        query = """
            INSERT INTO stock_ledger (
                id, item_id, transaction_type, quantity_change,
                reason, reference_id, created_at, created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            str(entry.id),
            str(entry.item_id),
            entry.transaction_type.value,
            entry.quantity_change,
            entry.reason,
            str(entry.reference_id) if entry.reference_id else None,
            entry.created_at.isoformat() + "Z",
            str(entry.created_by),
        )
        self.conn.execute(query, params)
        self.conn.commit()
        return entry

    def get_by_item(self, item_id: str) -> List[StockLedgerEntry]:
        """Get all ledger entries for an item."""
        query = "SELECT * FROM stock_ledger WHERE item_id = ? ORDER BY created_at"
        cursor = self.conn.execute(query, (item_id,))
        return [self._row_to_entry(row) for row in cursor.fetchall()]

    def get(self, entry_id: str) -> Optional[StockLedgerEntry]:
        """Get specific ledger entry."""
        query = "SELECT * FROM stock_ledger WHERE id = ?"
        cursor = self.conn.execute(query, (entry_id,))
        row = cursor.fetchone()
        return self._row_to_entry(row) if row else None

    def list(self) -> List[StockLedgerEntry]:
        """List all ledger entries."""
        query = "SELECT * FROM stock_ledger ORDER BY created_at DESC"
        cursor = self.conn.execute(query)
        return [self._row_to_entry(row) for row in cursor.fetchall()]

    def compute_stock_on_hand(self, item_id: str) -> int:
        """Compute current stock by summing all ledger entries."""
        query = "SELECT COALESCE(SUM(quantity_change), 0) FROM stock_ledger WHERE item_id = ?"
        cursor = self.conn.execute(query, (item_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> StockLedgerEntry:
        """Convert database row to entity."""
        return StockLedgerEntry(
            id=UUID(row["id"]),
            item_id=UUID(row["item_id"]),
            transaction_type=TransactionType(row["transaction_type"]),
            quantity_change=row["quantity_change"],
            reason=row["reason"],
            reference_id=UUID(row["reference_id"]) if row["reference_id"] else None,
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            created_by=UUID(row["created_by"]),
        )


class AuditLogRepository(BaseRepository):
    """Repository for AuditLogEntry entities (append-only,immutable)."""

    def create(self, entry: AuditLogEntry) -> AuditLogEntry:
        """Create audit log entry."""
        query = """
            INSERT INTO audit_log (
                id, entity_type, entity_id, operation, user_id,
                timestamp, old_state, new_state, reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            str(entry.id),
            entry.entity_type,
            str(entry.entity_id),
            entry.operation,
            str(entry.user_id),
            entry.timestamp.isoformat() + "Z",
            entry.old_state,
            entry.new_state,
            entry.reason,
        )
        self.conn.execute(query, params)
        self.conn.commit()
        return entry

    def get(self, entry_id: str) -> Optional[AuditLogEntry]:
        """Get audit log entry by ID."""
        query = "SELECT * FROM audit_log WHERE id = ?"
        cursor = self.conn.execute(query, (entry_id,))
        row = cursor.fetchone()
        return self._row_to_entry(row) if row else None

    def list(self) -> List[AuditLogEntry]:
        """List all audit entries."""
        query = "SELECT * FROM audit_log ORDER BY timestamp DESC"
        cursor = self.conn.execute(query)
        return [self._row_to_entry(row) for row in cursor.fetchall()]

    def query_by_entity(self, entity_type: str, entity_id: str) -> List[AuditLogEntry]:
        """Query all changes to specific entity."""
        query = """
            SELECT * FROM audit_log
            WHERE entity_type = ? AND entity_id = ?
            ORDER BY timestamp DESC
        """
        cursor = self.conn.execute(query, (entity_type, entity_id))
        return [self._row_to_entry(row) for row in cursor.fetchall()]

    def query_by_user(self, user_id: str) -> List[AuditLogEntry]:
        """Query all changes made by user."""
        query = """
            SELECT * FROM audit_log
            WHERE user_id = ?
            ORDER BY timestamp DESC
        """
        cursor = self.conn.execute(query, (user_id,))
        return [self._row_to_entry(row) for row in cursor.fetchall()]

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> AuditLogEntry:
        """Convert database row to entity."""
        return AuditLogEntry(
            id=UUID(row["id"]),
            entity_type=row["entity_type"],
            entity_id=UUID(row["entity_id"]),
            operation=row["operation"],
            user_id=UUID(row["user_id"]),
            timestamp=datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")),
            old_state=row["old_state"],
            new_state=row["new_state"],
            reason=row["reason"],
        )


class PaymentRepository(BaseRepository):
    """Repository for Payment entities."""

    def create(self, payment: Payment) -> Payment:
        """Record a payment."""
        query = """
            INSERT INTO payments (
                id, order_id, amount_cents, method, reference,
                finalized_at, finalized_by, created_at, created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            str(payment.id),
            str(payment.order_id),
            payment.amount.cents,
            payment.method.value,
            payment.reference,
            payment.finalized_at.isoformat() + "Z",
            str(payment.finalized_by),
            payment.finalized_at.isoformat() + "Z",
            str(payment.created_by),
        )
        self.conn.execute(query, params)
        self.conn.commit()
        return payment

    def get(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        query = "SELECT * FROM payments WHERE id = ?"
        cursor = self.conn.execute(query, (payment_id,))
        row = cursor.fetchone()
        return self._row_to_payment(row) if row else None

    def get_by_order(self, order_id: str) -> Optional[Payment]:
        """Get payment for a specific order."""
        query = "SELECT * FROM payments WHERE order_id = ?"
        cursor = self.conn.execute(query, (order_id,))
        row = cursor.fetchone()
        return self._row_to_payment(row) if row else None

    def list(self) -> List[Payment]:
        """List all payments."""
        query = "SELECT * FROM payments ORDER BY finalized_at DESC"
        cursor = self.conn.execute(query)
        return [self._row_to_payment(row) for row in cursor.fetchall()]

    def get_payments_by_date(self, date: datetime) -> List[Payment]:
        """Get all payments for a specific date."""
        query = """
            SELECT * FROM payments
            WHERE DATE(finalized_at) = DATE(?)
            ORDER BY finalized_at DESC
        """
        cursor = self.conn.execute(query, (date.isoformat(),))
        return [self._row_to_payment(row) for row in cursor.fetchall()]

    def get_daily_summary(self, date: datetime) -> Dict[str, Any]:
        """Get daily payment summary with totals by method."""
        query = """
            SELECT
                method,
                COUNT(*) as count,
                SUM(amount_cents) as total_cents
            FROM payments
            WHERE DATE(finalized_at) = DATE(?)
            GROUP BY method
        """
        cursor = self.conn.execute(query, (date.isoformat(),))
        rows = cursor.fetchall()

        summary: Dict[str, Any] = {
            "total_revenue_cents": 0,
            "transaction_count": 0,
            "by_method": {},
        }
        for row in rows:
            method = row["method"]
            count = row["count"]
            total = row["total_cents"]
            summary["by_method"][method] = {"count": count, "total_cents": total}
            summary["total_revenue_cents"] += total
            summary["transaction_count"] += count

        return summary

    @staticmethod
    def _row_to_payment(row: sqlite3.Row) -> Payment:
        """Convert database row to Payment entity."""
        return Payment(
            id=UUID(row["id"]),
            order_id=UUID(row["order_id"]),
            amount=Money(cents=row["amount_cents"]),
            method=PaymentMethod(row["method"]),
            reference=row["reference"] or "",
            finalized_at=datetime.fromisoformat(row["finalized_at"].replace("Z", "+00:00")),
            finalized_by=UUID(row["finalized_by"]),
            created_by=UUID(row["created_by"]),
        )


class VoidRecordRepository(BaseRepository):
    """Repository for VoidRecord entities."""

    def create(self, record: Any) -> Any:
        """Create a void record."""
        from src.domain import VoidRecord
        void_record: VoidRecord = record
        query = """
            INSERT INTO void_records (
                id, original_order_id, void_reason, voided_at,
                voided_by, approved_by, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            str(void_record.id),
            str(void_record.original_order_id),
            void_record.void_reason,
            void_record.voided_at.isoformat() + "Z",
            str(void_record.voided_by),
            str(void_record.approved_by) if void_record.approved_by else None,
            void_record.voided_at.isoformat() + "Z",
        )
        self.conn.execute(query, params)
        self.conn.commit()
        return void_record

    def get(self, record_id: str) -> Optional[Any]:
        """Get void record by ID."""
        from src.domain import VoidRecord
        query = "SELECT * FROM void_records WHERE id = ?"
        cursor = self.conn.execute(query, (record_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return VoidRecord(
            id=UUID(row["id"]),
            original_order_id=UUID(row["original_order_id"]),
            void_reason=row["void_reason"],
            voided_at=datetime.fromisoformat(row["voided_at"].replace("Z", "+00:00")),
            voided_by=UUID(row["voided_by"]),
            approved_by=UUID(row["approved_by"]) if row["approved_by"] else None,
        )

    def get_by_order(self, order_id: str) -> Optional[Any]:
        """Get void record for a specific order."""
        query = "SELECT * FROM void_records WHERE original_order_id = ?"
        cursor = self.conn.execute(query, (order_id,))
        row = cursor.fetchone()
        if not row:
            return None
        from src.domain import VoidRecord
        return VoidRecord(
            id=UUID(row["id"]),
            original_order_id=UUID(row["original_order_id"]),
            void_reason=row["void_reason"],
            voided_at=datetime.fromisoformat(row["voided_at"].replace("Z", "+00:00")),
            voided_by=UUID(row["voided_by"]),
            approved_by=UUID(row["approved_by"]) if row["approved_by"] else None,
        )

    def list(self) -> List[Any]:
        """List all void records."""
        from src.domain import VoidRecord
        query = "SELECT * FROM void_records ORDER BY voided_at DESC"
        cursor = self.conn.execute(query)
        results = []
        for row in cursor.fetchall():
            results.append(VoidRecord(
                id=UUID(row["id"]),
                original_order_id=UUID(row["original_order_id"]),
                void_reason=row["void_reason"],
                voided_at=datetime.fromisoformat(row["voided_at"].replace("Z", "+00:00")),
                voided_by=UUID(row["voided_by"]),
                approved_by=UUID(row["approved_by"]) if row["approved_by"] else None,
            ))
        return results
