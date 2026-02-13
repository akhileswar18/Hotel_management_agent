# HMS Testing Strategy & Setup

**Version**: 0.1.0 | **Status**: All Phases Complete | **Last Updated**: 2026-02-13

> **Current Test Results**: 73 tests passing (22 unit + 41 integration + 6 smoke + 4 performance). See `tests/performance/` for performance benchmarks.

---

## Overview

Testing is critical to HMS's core principle: **Correctness > Reliability > Usability > Performance > Features**.

This document outlines:
1. Testing strategy and coverage targets
2. How to run tests locally
3. Test organization and fixtures
4. Specific test scenarios for Phase 1

---

## Testing Strategy

### Coverage Targets

| Component | Type | Target | Notes |
|-----------|------|--------|-------|
| Domain Logic | Unit | ≥90% | Tax, discounts, stock rules must be 100% tested |
| Services | Integration | ≥80% | All critical flows end-to-end |
| Repositories | Integration | ≥75% | CRUD + queries |
| API Endpoints | Integration | ≥70% | HTTP request/response cycle |
| Offline Mode | Smoke | ✅ Must Pass | No network calls allowed |

### Test Pyramid

```
        ▲
       /|\
      / | \  Smoke Tests (10%)
     /  |  \ - End-to-end, offline
    /   |   \
   /____|____\
  /     |     \  Integration (30%)
 /      |      \ - Services + DB
/       |       \
________|______
  Unit Tests  (60%)
  - Pure functions, no DB
  - Domain layer
  - Business rules
```

---

## Running Tests

### Quick Start

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### By Test Type

```bash
# Unit tests only (no DB required)
pytest tests/unit/ -v

# Integration tests (requires DB)
pytest tests/integration/ -v

# Smoke tests (offline scenario testing)
pytest tests/smoke/ -v

# Specific test file
pytest tests/unit/test_business_rules.py -v

# Specific test class
pytest tests/unit/test_business_rules.py::TestMoneyClass -v

# Specific test
pytest tests/unit/test_business_rules.py::TestMoneyClass::test_money_creation -v
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html

# View in browser
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows

# Print coverage summary
pytest tests/ --cov=src --cov-report=term-missing
```

### Continuous Testing

```bash
# Run tests on file changes (requires pytest-watch)
pip install pytest-watch
ptw tests/ -- --cov=src
```

---

## Test Organization

### Unit Tests (tests/unit/)

**No database, no network, no side effects.**

Testing pure domain functions:

```
tests/unit/
├── test_business_rules.py   # Tax, discount, stock rules
├── test_value_objects.py    # Money, enums, immutability
└── test_entities.py         # Entity creation, constraints
```

**Run:**
```bash
pytest tests/unit/ -v
```

**Example:**
```python
def test_calculate_tax():
    """Test 18% tax calculation."""
    subtotal = Money(cents=10000)  # ₹100.00
    tax = calculate_tax(subtotal, 0.18)
    assert tax.cents == 1800  # ₹18.00
```

### Integration Tests (tests/integration/)

**With database and services, no network.**

Testing full workflows:

```
tests/integration/
├── test_sales_flow.py      # Order creation → finalization
├── test_inventory_flow.py  # Stock-in, deduction
├── test_auth_flow.py       # Login, permissions
└── test_api.py             # HTTP endpoints
```

**Run:**
```bash
pytest tests/integration/ -v
```

**Setup:**
- Uses `conftest.py` fixtures
- In-memory SQLite setup/teardown per test
- Sample data (fixtures) provided

**Example:**
```python
def test_create_order_finalize_payment(sample_user, sample_item):
    """Test full order lifecycle."""
    sales_service = SalesService()

    # Create order
    order = sales_service.create_order(table_id="1", created_by=sample_user.id)

    # Add item
    order = sales_service.add_item(order.id, sample_item.id, qty=2, added_by=sample_user.id)

    # Finalize
    finalized = sales_service.finalize_order(
        order.id,
        payment_method=PaymentMethod.CASH,
        paid_amount=Money(cents=70000),
        finalized_by=sample_user.id,
    )

    assert finalized.status == OrderStatus.FINALIZED
    assert finalized.receipt_number is not None
```

### Smoke Tests (tests/smoke/)

**Full workflows, no network, realistic scenarios.**

```
tests/smoke/
└── test_offline_workflow.py  # End-to-end without network
```

**Run:**
```bash
pytest tests/smoke/ -v
```

**Scenarios:**
- Create order offline
- Finalize payment offline
- Query inventory offline
- Generate daily report offline

---

## Test Fixtures

Shared fixtures defined in `tests/conftest.py`:

```python
@pytest.fixture
def test_db():
    """In-memory SQLite for each test."""
    # Auto-cleanup after test

@pytest.fixture
def sample_user():
    """Sample MANAGER user."""
    return User(...)

@pytest.fixture
def sample_item():
    """Sample product (Biryani, ₹300)."""
    return Item(...)

@pytest.fixture
def sample_order(sample_user):
    """Sample draft order."""
    return Order(...)
```

**Usage:**
```python
def test_something(test_db, sample_user, sample_item):
    # test_db: clean database
    # sample_user: manager user (ID: uuid4())
    # sample_item: biryani item (₹300)
    pass
```

---

## Key Test Scenarios

### Phase 1 Must-Test Flows

#### 1. Order Creation & Finalization
```python
✓ Create draft order
✓ Add items to draft order
✓ Recalculate totals on each item added
✓ Apply discount (validates max 50%)
✓ Finalize with payment
✓ Generate receipt number
✓ Deduct stock from inventory
✓ Log to audit trail
```

#### 2. Stock Management
```python
✓ Record stock-in (purchase)
✓ Deduct stock on sale (finalized order)
✓ Prevent negative stock without approval
✓ Compute stock-on-hand from ledger
✓ Identify low-stock items
```

#### 3. User Authentication
```python
✓ Login with valid PIN (bcrypt verified)
✓ Reject invalid PIN
✓ Enforce permissions (waiter ≠ manager)
✓ Prevent waiter from voiding orders
✓ Allow manager any action
```

#### 4. Audit Logging
```python
✓ Log order creation
✓ Log order finalization
✓ Log stock movements
✓ Log user login/logout
✓ Log permission denials
✓ Cannot edit audit logs (immutable)
```

#### 5. Offline Operation
```python
✓ Create order without network
✓ Finalize payment offline
✓ Query inventory offline
✓ Generate reports offline
✓ Queue sync transactions (Phase 2)
```

---

## Common Test Patterns

### Testing Pure Functions
```python
def test_calculate_tax():
    # Arrange
    subtotal = Money(cents=10000)
    tax_rate = 0.18

    # Act
    result = calculate_tax(subtotal, tax_rate)

    # Assert
    assert result.cents == 1800
```

### Testing Services with Fixtures
```python
def test_sales_flow(test_db, sample_user, sample_item):
    # Arrange
    sales_service = SalesService()

    # Act
    order = sales_service.create_order("1", sample_user.id)
    order = sales_service.add_item(order.id, sample_item.id, 2, sample_user.id)
    finalized = sales_service.finalize_order(...)

    # Assert
    assert finalized.status == OrderStatus.FINALIZED
    assert finalized.receipt_number.startswith("REC-")
```

### Testing Error Cases
```python
def test_insufficient_stock():
    with pytest.raises(InsufficientStockError):
        validate_stock_deduction(current_stock=5, qty_to_deduct=10)
```

---

## Debugging Tests

### Print Statement Debugging
```python
def test_something():
    result = some_function()
    print(f"Result: {result}")  # Shows in test output with -s
    assert result == expected

# Run with output:
pytest tests/ -s -v
```

### Use Debugger
```python
def test_something():
    import pdb; pdb.set_trace()  # Drop into debugger
    result = some_function()

# Run:
pytest tests/ -s --pdb
```

### View Logs in Tests
```bash
# Show logs from test (if using logging)
pytest tests/ -v --log-cli-level=DEBUG
```

---

## CI/CD Integration

### GitHub Actions (Recommended)

Create `.github/workflows/tests.yml`:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/ --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v3
```

### Pre-Commit Hooks

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
set -e
echo "Running lints..."
black --check src/ tests/
flake8 src/ tests/
mypy src/ --strict
echo "Running tests..."
pytest tests/unit/ -q
echo "✓ All checks passed"
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## Performance Benchmarks (Phase 1)

Target performance for unit tests:

| Operation | Target | Notes |
|-----------|--------|-------|
| Tax calculation | <1ms | Pure function |
| Discount validation | <1ms | Pure function |
| Stock deduction | <10ms | DB write |
| Order finalization | <500ms | Multiple DB writes + audit |
| Daily sales report | <5000ms | Aggregate ~1000 transactions |

---

## Known Issues & Workarounds

### SQLite Locked Error in Tests
```
sqlite3.OperationalError: database is locked
```

**Cause**: Multiple test processes access same DB.

**Fix**:
```bash
# Use in-process workers
pytest tests/ -n0  # Disable xdist parallelization
```

### Slow Tests
```bash
# Profile test speed
pytest tests/ --durations=10  # Show 10 slowest tests

# Run only fast tests
pytest tests/ -m "not slow"
```

---

## Maintenance

### Adding New Tests

1. Determine test type (unit/integration/smoke)
2. Create test in appropriate directory
3. Use fixtures from `conftest.py`
4. Run locally: `pytest tests/ -v`
5. Ensure coverage doesn't drop
6. Add any new fixtures to `conftest.py`

### Updating Fixtures

If adding new domain entities:

1. Update `tests/conftest.py` with new fixture
2. Update `tests/integration/__init__.py` for imports
3. Document fixture in comments

### Test Documentation

Each test class should have:

```python
class TestFeatureName:
    """
    Test [feature].

    Tests cover:
    - Happy path
    - Edge cases
    - Error conditions
    """
```

---

## Resources

- **Pytest Docs**: https://docs.pytest.org/
- **Coverage.py**: https://coverage.readthedocs.io/
- **HMS Constitution**: [constitution.md](../constitution.md)
- **HMS Specification**: [specification.md](../specification.md)

---

**Status**: All Phases Complete (73 tests) | **Next**: Maintenance & regression
