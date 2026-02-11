"""
Test Configuration and Fixtures

Pytest configuration with shared fixtures for test database,
sample data, and mocks.
"""

import pytest
import sqlite3
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from contextlib import contextmanager

from src.domain import (
    User, Item, Order, Role, Money, OrderStatus, OrderLineItem
)
from src.infrastructure import Database


@pytest.fixture
def test_db():
    """In-memory SQLite database for testing."""
    # Create in-memory database
    import tempfile
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = db_file.name

    # Initialize schema
    from migrations.runner import MigrationRunner
    runner = MigrationRunner(db_path)
    runner.apply_migrations()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return User(
        id=uuid4(),
        username="testuser",
        role=Role.MANAGER,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by=uuid4(),
    )


@pytest.fixture
def sample_item():
    """Sample item/product."""
    return Item(
        id=uuid4(),
        name="Biryani",
        category="Rice Dishes",
        unit_price=Money(cents=30000),  # ₹300.00
        reorder_level=10,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by=uuid4(),
    )


@pytest.fixture
def sample_order(sample_user):
    """Sample order in draft status."""
    return Order(
        id=uuid4(),
        table_id="1",
        status=OrderStatus.DRAFT,
        subtotal=Money(cents=0),
        discount_amount=Money(cents=0),
        tax_amount=Money(cents=0),
        total_amount=Money(cents=0),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by=sample_user.id,
    )
