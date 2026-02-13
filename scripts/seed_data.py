"""
Seed Script: Populate HMS Database with Sample Data

Populates users, items, tables, and sample transactions for testing.
Run once after initial migration to set up test data.

Usage:
    python scripts/seed_data.py
    or
    python -m scripts.seed_data
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database import DatabaseConfig
from src.application import AuthService, SalesService
from src.infrastructure import (
    UserRepository, ItemRepository, StockLedgerRepository,
    Database
)
from src.domain import (
    User, Item, Money, Role, StockLedgerEntry, TransactionType,
    PaymentMethod,
)


def seed_database():
    """Populate database with sample data."""
    print("\n" + "=" * 60)
    print("HMS Phase 1.5 - Database Seeding")
    print("=" * 60 + "\n")

    # Initialize database
    db = Database()
    if db._connection is None:
        print("[FAILED] Failed to initialize database")
        return

    # Create users
    print("[1/5] Creating sample users...")
    _seed_users(db)

    # Create items
    print("[2/5] Creating sample products...")
    _seed_items(db)

    # Create sample tables
    print("[3/5] Creating sample tables...")
    _seed_tables(db)

    # Create stock ledger entries
    print("[4/5] Creating initial stock...")
    _seed_stock_ledger(db)

    # Create sample orders (finalized, held, voided) for demo and reports
    print("[5/5] Creating sample orders...")
    _seed_sample_orders(db)

    print("\n" + "=" * 60)
    print("[OK] Seeding complete!")
    print("=" * 60 + "\n")
    print("Sample users created:")
    print("  - Username: waiter     | PIN: 1234  | Role: WAITER")
    print("  - Username: cashier    | PIN: 1234  | Role: CASHIER")
    print("  - Username: manager    | PIN: 1234  | Role: MANAGER")
    print("  - Username: clerk      | PIN: 1234  | Role: CLERK")
    print("\n")


def _seed_users(db: Database):
    """Create sample users."""
    users_data = [
        ("waiter", "1234", Role.WAITER),
        ("cashier", "1234", Role.CASHIER),
        ("manager", "1234", Role.MANAGER),
        ("clerk", "1234", Role.CLERK),
    ]

    auth_service = AuthService()
    user_repo = UserRepository()

    for username, pin, role in users_data:
        # Check if user exists
        existing = user_repo.get_by_username(username)
        if existing:
            print(f"  [SKIP] {username} already exists, skipping")
            continue

        # Hash PIN
        pin_hash = auth_service.hash_pin(pin)

        # Create user
        user = User(
            id=uuid4(),
            username=username,
            role=role,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=None,
        )

        user_repo.create(user, pin_hash)
        print(f"  [OK] Created {username} ({role.value})")


def _seed_items(db: Database):
    """Create sample products."""
    items_data = [
        ("Biryani", "Rice Dishes", 300.00, 20),
        ("Butter Chicken", "Curries", 250.00, 15),
        ("Paneer Tikka", "Appetizers", 180.00, 10),
        ("Coke", "Beverages", 50.00, 50),
        ("Mango Juice", "Beverages", 60.00, 30),
        ("Naan", "Breads", 40.00, 25),
        ("Samosa", "Appetizers", 30.00, 40),
        ("Dosa", "South Indian", 120.00, 15),
        ("Idli", "South Indian", 80.00, 20),
        ("Lassi", "Beverages", 70.00, 25),
        ("Pulao", "Rice Dishes", 200.00, 15),
        ("Dal Makhani", "Curries", 180.00, 20),
        ("Raita", "Sides", 60.00, 30),
        ("Gulab Jamun", "Desserts", 80.00, 25),
        ("Chai", "Beverages", 30.00, 100),
        ("Coffee", "Beverages", 50.00, 80),
        ("Roti", "Breads", 25.00, 40),
        ("Paratha", "Breads", 55.00, 30),
        ("Upma", "South Indian", 90.00, 20),
        ("Vada", "South Indian", 40.00, 35),
        ("Uttapam", "South Indian", 100.00, 15),
        ("Chicken Tikka", "Appetizers", 220.00, 12),
        ("Veg Thali", "Combos", 280.00, 15),
        ("Lemonade", "Beverages", 55.00, 40),
        ("Plain Rice", "Rice Dishes", 80.00, 25),
    ]

    item_repo = ItemRepository()
    user_repo = UserRepository()
    created_items = []

    # Get a system user (first user created, or admin)
    all_users = user_repo.list()
    if not all_users:
        print("  ❌ No users found. Create users first!")
        return created_items

    system_user_id = all_users[0].id  # Use first user (admin/system)

    for name, category, price, reorder_level in items_data:
        # Check if item exists
        existing_items = item_repo.list()
        if any(i.name == name for i in existing_items):
            print(f"  [SKIP] {name} already exists, skipping")
            continue

        item = Item(
            id=uuid4(),
            name=name,
            category=category,
            unit_price=Money.from_float(price),
            reorder_level=reorder_level,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=system_user_id,  # Use actual user ID
        )

        item_repo.create(item)
        created_items.append(item)
        print(f"  [OK] Created {name} (Rs.{price:.2f})")

    return created_items


def _seed_tables(db: Database):
    """Create sample dining tables."""
    # Get connection
    conn = db._connection
    if not conn:
        return

    # Check if tables already exist
    cursor = conn.execute("SELECT COUNT(*) FROM tables_seating")
    count = cursor.fetchone()[0]

    if count > 0:
        print(f"  [SKIP] {count} tables already exist, skipping")
        return

    tables_data = [
        ("1", 4),
        ("2", 4),
        ("3", 6),
        ("4", 2),
        ("5", 8),
        ("6", 4),
        ("7", 4),
        ("8", 6),
    ]

    for table_num, capacity in tables_data:
        conn.execute(
            """
            INSERT INTO tables_seating (id, table_number, capacity, status, created_at, updated_at)
            VALUES (?, ?, ?, 'available', ?, ?)
            """,
            (str(uuid4()), table_num, capacity, datetime.utcnow().isoformat() + "Z", datetime.utcnow().isoformat() + "Z"),
        )

    conn.commit()
    print(f"  [OK] Created {len(tables_data)} dining tables")


def _seed_stock_ledger(db: Database):
    """Create initial stock entries."""
    # Get all items
    item_repo = ItemRepository()
    items = item_repo.list()

    stock_repo = StockLedgerRepository()
    user_repo = UserRepository()

    # Get a system user (first user created)
    all_users = user_repo.list()
    if not all_users:
        print("  [FAILED] No users found. Create users first!")
        return

    system_user = all_users[0].id  # Use actual user ID

    for item in items:
        # Check if item already has stock
        existing_stock = stock_repo.get_by_item(str(item.id))
        if existing_stock:
            print(f"  [SKIP] {item.name} already has stock, skipping")
            continue

        # Create initial stock entry
        initial_qty = item.reorder_level * 3  # 3x reorder level

        entry = StockLedgerEntry(
            id=uuid4(),
            item_id=item.id,
            transaction_type=TransactionType.PURCHASE,
            quantity_change=initial_qty,
            reason="Initial stock setup",
            created_at=datetime.utcnow(),
            created_by=system_user,
        )

        stock_repo.create(entry)
        print(f"  [OK] {item.name}: {initial_qty} units")


def _seed_sample_orders(db: Database):
    """Create realistic sample orders: finalized, held, voided, and a few days of history."""
    try:
        from src.application.services import SalesService
        from datetime import timedelta

        user_repo = UserRepository()
        item_repo = ItemRepository()
        users = user_repo.list()
        items = item_repo.list()
        if not users or not items:
            print("  [SKIP] Need users and items first; skipping sample orders")
            return

        waiter = next((u for u in users if u.role.value == "WAITER"), users[0])
        manager = next((u for u in users if u.role.value == "MANAGER"), users[0])
        cashier = next((u for u in users if u.role.value == "CASHIER"), users[0])

        svc = SalesService()
        table_ids = ["1", "2", "3", "4", "5", "6", "7", "8"]

        # --- Finalized orders (5–10) for demo and reports ---
        finalized = 0
        for i in range(8):
            try:
                order = svc.create_order(table_id=table_ids[i % len(table_ids)], created_by=waiter.id)
                # Add 1–3 items per order
                for j in range((i % 3) + 1):
                    item = items[j % len(items)]
                    svc.add_item(order.id, item.id, quantity=1 + (i + j) % 2, added_by=waiter.id)
                total = svc.get_order(order.id).total_amount
                svc.finalize_order(
                    order.id, PaymentMethod.CASH,
                    Money.from_float(max(total.to_float() + 50, 500.0)),
                    cashier.id,
                )
                finalized += 1
            except Exception as e:
                print(f"  [SKIP] Finalized order {i + 1}: {e}")

        # --- Held orders ---
        for i in range(2):
            try:
                order = svc.create_order(table_id=table_ids[i], created_by=waiter.id)
                svc.add_item(order.id, items[0].id, quantity=1, added_by=waiter.id)
                svc.hold_order(order.id, waiter.id)
                print(f"  [OK] Held order on table {table_ids[i]}")
            except Exception as e:
                print(f"  [SKIP] Held order: {e}")

        # --- Voided orders ---
        for i in range(2):
            try:
                order = svc.create_order(table_id=table_ids[i + 2], created_by=waiter.id)
                svc.add_item(order.id, items[1].id, quantity=1, added_by=waiter.id)
                svc.void_order(order.id, reason="Wrong order / demo void", voided_by=cashier.id, approved_by=manager.id)
                print(f"  [OK] Voided order on table {table_ids[i + 2]}")
            except Exception as e:
                print(f"  [SKIP] Voided order: {e}")

        # Backdate some orders for “a few days of transaction history”
        conn = db._connection
        if conn and finalized > 0:
            cursor = conn.execute(
                "SELECT id FROM orders WHERE status = 'finalized' ORDER BY created_at DESC LIMIT ?",
                (min(5, finalized),),
            )
            rows = cursor.fetchall()
            for idx, row in enumerate(rows):
                days_ago = (idx % 3) + 1  # 1, 2, or 3 days ago
                backdate = (datetime.utcnow() - timedelta(days=days_ago)).isoformat() + "Z"
                conn.execute(
                    "UPDATE orders SET created_at = ?, updated_at = ? WHERE id = ?",
                    (backdate, backdate, row["id"]),
                )
            conn.commit()
            print(f"  [OK] Backdated {len(rows)} orders for multi-day history")

        print(f"  [OK] Sample orders: {finalized} finalized, 2 held, 2 voided")
    except Exception as e:
        print(f"  [SKIP] Sample orders: {e}")


if __name__ == "__main__":
    seed_database()
