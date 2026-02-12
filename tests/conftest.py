"""
Test Configuration and Fixtures

Pytest configuration with shared fixtures for test database,
sample data, and mocks. Properly resets the Database singleton
so each test gets a clean, isolated database.
"""

import pytest
import sqlite3
import os
import tempfile
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from src.domain import (
    User, Item, Order, Role, Money, OrderStatus, OrderLineItem,
    StockLedgerEntry, TransactionType,
)


def _reset_db_singleton():
    """Reset the Database singleton so it re-initialises with a new path."""
    from src.infrastructure.database import Database
    if Database._connection is not None:
        try:
            Database._connection.close()
        except Exception:
            pass
    Database._connection = None
    Database._instance = None


@pytest.fixture(autouse=True)
def test_db(tmp_path):
    """
    Create an isolated test database for every test.

    Sets DATABASE_URL env var before importing Database,
    resets the singleton, then tears down afterwards.
    """
    db_path = str(tmp_path / "test_hms.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    # Reset singleton so it picks up the new path
    _reset_db_singleton()

    # Import *after* resetting so init_db runs against the temp path
    from src.infrastructure.database import Database
    db = Database()

    yield db_path

    # Cleanup: close connection and reset singleton
    _reset_db_singleton()


@pytest.fixture
def sample_user(test_db):
    """Create and persist a manager user in the test DB."""
    from src.infrastructure import UserRepository
    from src.application import AuthService

    auth = AuthService()
    pin_hash = auth.hash_pin("1234")

    user = User(
        id=uuid4(),
        username="testmanager",
        role=Role.MANAGER,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by=None,
    )

    repo = UserRepository()
    repo.create(user, pin_hash)
    return user


@pytest.fixture
def sample_waiter(test_db):
    """Create and persist a waiter user in the test DB."""
    from src.infrastructure import UserRepository
    from src.application import AuthService

    auth = AuthService()
    pin_hash = auth.hash_pin("5678")

    user = User(
        id=uuid4(),
        username="testwaiter",
        role=Role.WAITER,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by=None,
    )

    repo = UserRepository()
    repo.create(user, pin_hash)
    return user


@pytest.fixture
def sample_item(test_db, sample_user):
    """Create and persist a sample item (Biryani) in the test DB."""
    from src.infrastructure import ItemRepository

    item = Item(
        id=uuid4(),
        name="Biryani",
        category="Rice Dishes",
        unit_price=Money(cents=30000),  # Rs.300.00
        reorder_level=10,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by=sample_user.id,
    )
    repo = ItemRepository()
    repo.create(item)
    return item


@pytest.fixture
def sample_item_coke(test_db, sample_user):
    """Create and persist a second sample item (Coke) in the test DB."""
    from src.infrastructure import ItemRepository

    item = Item(
        id=uuid4(),
        name="Coke",
        category="Beverages",
        unit_price=Money(cents=5000),  # Rs.50.00
        reorder_level=50,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by=sample_user.id,
    )
    repo = ItemRepository()
    repo.create(item)
    return item


@pytest.fixture
def stocked_item(sample_item, sample_user):
    """sample_item with 100 units of stock already added."""
    from src.application import InventoryService

    svc = InventoryService()
    svc.record_stock_in(
        item_id=sample_item.id,
        quantity=100,
        reference="TEST-PO-001",
        recorded_by=sample_user.id,
    )
    return sample_item


@pytest.fixture
def stocked_coke(sample_item_coke, sample_user):
    """sample_item_coke with 200 units of stock."""
    from src.application import InventoryService

    svc = InventoryService()
    svc.record_stock_in(
        item_id=sample_item_coke.id,
        quantity=200,
        reference="TEST-PO-002",
        recorded_by=sample_user.id,
    )
    return sample_item_coke
