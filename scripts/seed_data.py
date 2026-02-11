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
from src.application import AuthService
from src.infrastructure import (
    UserRepository, ItemRepository, StockLedgerRepository,
    Database
)
from src.domain import (
    User, Item, Money, Role, StockLedgerEntry, TransactionType
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
    print("[1/4] Creating sample users...")
    _seed_users(db)

    # Create items
    print("[2/4] Creating sample products...")
    _seed_items(db)

    # Create sample tables
    print("[3/4] Creating sample tables...")
    _seed_tables(db)

    # Create stock ledger entries
    print("[4/4] Creating initial stock...")
    _seed_stock_ledger(db)

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


if __name__ == "__main__":
    seed_database()

# TODO: Add more realistic sample data
# TODO: Add sample orders for testing reports
# TODO: Add transaction history for demonstration
