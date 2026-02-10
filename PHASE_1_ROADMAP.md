# Phase 1 (MVP) Task Breakdown & Roadmap

**Version**: 1.0 | **Date**: February 9, 2026 | **Status**: Ready for Implementation

---

## Table of Contents

1. [Recommended Folder Structure](#recommended-folder-structure)
2. [Required Dependencies & Setup](#required-dependencies--setup)
3. [Epics, Stories & Tasks](#epics-stories--tasks)
4. [Task Dependencies Graph](#task-dependencies-graph)
5. [Definition of Done](#definition-of-done)
6. [Timeline Estimate](#timeline-estimate)

---

## Recommended Folder Structure

```
Hotel_management_agent/
├── constitution.md                    # Non-negotiable principles
├── specification.md                   # High-level spec
├── ARCHITECTURE.md                    # Technical architecture
├── PHASE_1_ROADMAP.md                # This file
│
├── src/
│   ├── __init__.py
│   ├── main.py                        # Entry point (Flet app + FastAPI server)
│   │
│   ├── domain/                        # Pure business logic (no DB, no UI)
│   │   ├── __init__.py
│   │   ├── entities.py                # Order, Item, Payment entities
│   │   ├── value_objects.py           # Money, OrderStatus enums
│   │   └── business_rules.py          # calculate_tax(), apply_discount(), etc.
│   │
│   ├── application/                   # Service layer (orchestration)
│   │   ├── __init__.py
│   │   ├── sales_service.py           # SalesService
│   │   ├── inventory_service.py       # InventoryService
│   │   ├── auth_service.py            # AuthService
│   │   ├── reporting_service.py       # ReportingService
│   │   ├── audit_service.py           # AuditService
│   │   └── exceptions.py              # Custom exceptions
│   │
│   ├── infrastructure/                # DB, persistence, external I/O
│   │   ├── __init__.py
│   │   ├── database.py                # SQLite connection, migrations
│   │   ├── repositories.py            # OrderRepository, ItemRepository, etc.
│   │   ├── logging_handler.py         # File & DB logging
│   │   ├── config.py                  # App config (paths, DB location)
│   │   └── printer_stub.py            # Printer service stub
│   │
│   ├── api/                           # FastAPI endpoints
│   │   ├── __init__.py
│   │   ├── app.py                     # FastAPI app setup
│   │   ├── sales_routes.py            # POST /api/sales/orders, etc.
│   │   ├── inventory_routes.py        # GET /api/inventory/items, etc.
│   │   ├── auth_routes.py             # POST /api/auth/login, etc.
│   │   ├── reports_routes.py          # GET /api/reports/daily-sales, etc.
│   │   └── dependencies.py            # Dependency injection, auth guards
│   │
│   ├── ui/                            # Flet UI
│   │   ├── __init__.py
│   │   ├── app.py                     # Main Flet app initialization
│   │   ├── screens/
│   │   │   ├── __init__.py
│   │   │   ├── auth_screen.py         # Login screen
│   │   │   ├── pos_screen.py          # POS order entry screen
│   │   │   ├── products_screen.py     # Product catalog CRUD
│   │   │   ├── reports_screen.py      # Daily reports view
│   │   │   └── receipt_screen.py      # Receipt display/print
│   │   ├── components/
│   │   │   ├── __init__.py
│   │   │   ├── order_summary.py       # Order total display widget
│   │   │   ├── item_picker.py         # Item selection widget
│   │   │   └── buttons.py             # Reusable button styles
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── ui_helpers.py          # Formatting, conversions
│   │
│   └── __main__.py                    # Run with: python -m src
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # pytest fixtures (test DB, mocks)
│   │
│   ├── unit/                          # Unit tests (domain logic)
│   │   ├── __init__.py
│   │   ├── test_business_rules.py     # test_calculate_tax(), etc.
│   │   └── test_value_objects.py      # test Money, OrderStatus
│   │
│   ├── integration/                   # Integration tests (service + repo + DB)
│   │   ├── __init__.py
│   │   ├── test_sales_flow.py         # test_create_order_finalize_receipt()
│   │   ├── test_inventory_flow.py     # test_stock_ledger()
│   │   └── test_auth_flow.py          # test_login_logout()
│   │
│   └── smoke/                         # Smoke tests (offline mode, end-to-end)
│       ├── __init__.py
│       └── test_offline_workflow.py   # test_full_order_without_network()
│
├── migrations/
│   ├── __init__.py
│   ├── 001_init_schema.sql            # Initial schema
│   └── runner.py                      # Migration executor
│
├── logs/                              # Log files (created at runtime)
│   └── .gitkeep
│
├── requirements.txt                   # Python dependencies
├── requirements-dev.txt               # Dev dependencies (pytest, black, mypy)
├── .env.example                       # Environment variables template
├── .gitignore                         # Exclude logs, .db, .env
├── setup.py                           # Package info (optional)
├── README.md                          # Quick start guide
├── TESTING.md                         # Test strategy & setup
└── Makefile                           # Common commands (run, test, lint)
```

---

## Required Dependencies & Setup

### 2.1 Core Dependencies

**requirements.txt**:
```
# Web framework (local backend)
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0

# UI framework (touch-first)
flet==0.21.2

# Database
sqlite3-python==1.0.0  # Bundled with Python; explicit version for clarity

# Type hints & validation
typing-extensions==4.8.0

# Async support
aiofiles==23.2.1

# Utilities
python-dateutil==2.8.2
uuid==1.30
```

**requirements-dev.txt**:
```
# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# Code quality
black==23.11.0
flake8==6.1.0
mypy==1.7.0
pylint==3.0.2

# Debugging
ipdb==0.13.13

# Documentation (optional, Phase 2)
mkdocs==1.5.3
```

### 2.2 Installation & Setup

```bash
# Clone repo
git clone <repo_url>
cd Hotel_management_agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development

# Run migrations (creates DB schema)
python -m migrations.runner

# Run backend + UI
python -m src

# Run tests
pytest tests/ -v --cov=src

# Lint & format
black src/ tests/
mypy src/ --strict
flake8 src/ tests/
```

### 2.3 Environment Variables (.env)

```bash
# .env
DATABASE_URL=sqlite:////tmp/hms.db  # Or user-specific location
LOG_LEVEL=INFO
LOG_DIR=./logs
API_HOST=127.0.0.1
API_PORT=8000
PRINTER_ENABLED=false  # Stub only in Phase 1
OFFLINE_MODE=true  # Default offline, sync later
```

---

## Epics, Stories & Tasks

---

## EPIC 1: Project Setup & Infrastructure

### Epic Goal
Set up development environment, version control, CI/CD basics, and project structure.

---

### STORY 1.1: Repository & Development Environment

**Objective**: Initialize repo, virtual environment, dependencies, and basic CI.

#### Task 1.1.1: Initialize Git Repository & .gitignore

**Description**: Set up Git repo with proper .gitignore (exclude logs, .db, .env, venv).

**Acceptance Criteria**:
- [ ] `.git` initialized
- [ ] `.gitignore` excludes: `*.db`, `*.log`, `logs/`, `venv/`, `.env`, `__pycache__/`, `.pytest_cache/`, `*.egg-info/`
- [ ] `README.md` with quick-start instructions
- [ ] Initial commit: "Project initialization"

**File Targets**:
- `.gitignore`
- `README.md`

**Dependencies**: None

**Tests**: None (manual verification)

**Definition of Done**:
- [ ] Git repo initialized
- [ ] .gitignore created and tested (untracked files verified)
- [ ] README with setup instructions
- [ ] First commit pushed to main branch

---

#### Task 1.1.2: Set Up Python Virtual Environment & Dependencies

**Description**: Create venv, install core and dev dependencies, pin versions.

**Acceptance Criteria**:
- [ ] `venv/` created and activated
- [ ] `requirements.txt` contains all core deps (FastAPI, Flet, sqlite3)
- [ ] `requirements-dev.txt` contains dev deps (pytest, black, mypy, flake8)
- [ ] `pip install -r requirements.txt` succeeds without errors
- [ ] `pip install -r requirements-dev.txt` succeeds without errors
- [ ] Python version ≥3.9

**File Targets**:
- `requirements.txt`
- `requirements-dev.txt`
- `.env.example`

**Dependencies**: Task 1.1.1

**Tests**: Manual (venv activation, pip list verification)

**Definition of Done**:
- [ ] Virtual environment working
- [ ] All packages installed and importable
- [ ] Requirements files committed to git
- [ ] .env.example created (no secrets committed)

---

#### Task 1.1.3: Create Project Folder Structure

**Description**: Create all folders from "Recommended Folder Structure" section.

**Acceptance Criteria**:
- [ ] All folders created: `src/domain/`, `src/application/`, `src/infrastructure/`, `src/api/`, `src/ui/`, `tests/`, `migrations/`, `logs/`
- [ ] `__init__.py` files in all Python packages
- [ ] `.gitkeep` in `logs/` (so it gets tracked)
- [ ] Folder structure matches architecture (no god folders)

**File Targets**:
- All folders listed in folder structure

**Dependencies**: Task 1.1.1

**Tests**: Manual (folder structure validation)

**Definition of Done**:
- [ ] All folders created
- [ ] __init__.py files present
- [ ] No orphaned folders
- [ ] Matches ARCHITECTURE.md

---

---

## EPIC 2: Database Schema & Migrations

### Epic Goal
Design SQLite schema, implement migrations, ensure ACID compliance and auditability.

---

### STORY 2.1: Core Schema Design

**Objective**: Define SQLite tables with proper constraints, indexes, and audit fields.

#### Task 2.1.1: Define Core Tables (Orders, Items, Payments)

**Description**: Design and implement Orders, OrderLineItems, Items, Payments, Payment Methods tables.

**Acceptance Criteria**:
- [ ] `orders` table: id, table_id, status (draft/finalized/voided), subtotal_cents, discount_cents, tax_cents, total_cents, created_at, updated_at, created_by, finalized_at, finalized_by, receipt_number (UNIQUE)
- [ ] `order_line_items` table: id, order_id (FK), item_id (FK), quantity, unit_price_cents, discount_cents, tax_cents, total_cents, created_at, created_by (FK users)
- [ ] `items` table: id, name, category, unit_price_cents, reorder_level, created_at, updated_at, created_by, updated_by
- [ ] `payments` table: id, order_id (FK), amount_cents, method (CASH/CARD/VOUCHER), reference, finalized_at, finalized_by (FK users)
- [ ] `tables` table: id, table_number, capacity, status
- [ ] All tables include: id (PRIMARY KEY), created_at, updated_at, created_by, updated_by (where applicable)
- [ ] Foreign keys enforced at DB level
- [ ] Money stored as INTEGER (cents, no floats)

**File Targets**:
- `migrations/001_init_schema.sql` (or split into separate files)

**Dependencies**: Task 1.1.3

**Tests**: 
- Integration test: schema creation, table validation

**Definition of Done**:
- [ ] Schema created and validated
- [ ] Foreign keys enforced
- [ ] No float columns for money
- [ ] SQL file documented with comments

---

#### Task 2.1.2: Define Audit & Logging Tables

**Description**: Design AuditLog, SystemLog, VoidRecords tables.

**Acceptance Criteria**:
- [ ] `audit_log` table: id, entity_type, entity_id, operation (CREATE/UPDATE/VOID/FINALIZE), user_id (FK), timestamp, old_state (JSON), new_state (JSON), reason
- [ ] `system_log` table: id, level (DEBUG/INFO/WARN/ERROR), category, user_id, action, entity_id, entity_type, timestamp, message, details (JSON)
- [ ] `void_records` table: id, original_order_id (FK), void_reason, voided_at, voided_by (FK), approved_by (FK)
- [ ] Indexes on: audit_log(entity_type, entity_id, timestamp), system_log(timestamp, category), audit_log(user_id, timestamp)
- [ ] audit_log cannot be hard-deleted (enforce in code)

**File Targets**:
- `migrations/001_init_schema.sql` (add to existing or separate)

**Dependencies**: Task 2.1.1

**Tests**: 
- Integration test: audit log insertion, query by entity/timestamp

**Definition of Done**:
- [ ] Audit tables created
- [ ] Indexes present
- [ ] Timestamps in UTC
- [ ] JSON columns support old_state/new_state

---

#### Task 2.1.3: Define User & Auth Tables

**Description**: Design users, sessions tables for authentication.

**Acceptance Criteria**:
- [ ] `users` table: id, username (UNIQUE), pin_hash (bcrypt), role (WAITER/CASHIER/MANAGER/CLERK/ADMIN), created_at, updated_at, created_by, updated_by
- [ ] `sessions` table: id, user_id (FK), login_at, logout_at, device_id (optional), expires_at
- [ ] PIN stored as bcrypt hash (never plaintext)
- [ ] Role column restricted to enum values (check constraint)

**File Targets**:
- `migrations/001_init_schema.sql`

**Dependencies**: Task 2.1.1

**Tests**: 
- Unit test: bcrypt hashing (not integration)

**Definition of Done**:
- [ ] User table created with hashed PIN
- [ ] Role enum enforced
- [ ] Sessions table tracks login/logout

---

#### Task 2.1.4: Define Stock Ledger Table

**Description**: Design append-only stock ledger (no direct stock_on_hand updates).

**Acceptance Criteria**:
- [ ] `stock_ledger` table: id, item_id (FK), transaction_type (PURCHASE/SALE/ADJUSTMENT/WASTAGE), quantity_change (signed integer), reason, reference_id (order_id or PO_id), created_at, created_by (FK users)
- [ ] Append-only (no updates/deletes to existing entries)
- [ ] quantity_change can be negative (for sales/wastage)
- [ ] Index on item_id for stock queries

**File Targets**:
- `migrations/001_init_schema.sql`

**Dependencies**: Task 2.1.2 (after audit/log tables)

**Tests**: 
- Integration test: append ledger entries, compute stock_on_hand

**Definition of Done**:
- [ ] Stock ledger table created
- [ ] Append-only constraint enforced (via code, not DB trigger in Phase 1)
- [ ] No direct updates to stock_on_hand

---

### STORY 2.2: Migration Infrastructure

**Objective**: Implement migration runner, version control, rollback support.

#### Task 2.2.1: Implement Migration Runner

**Description**: Create Python script to apply migrations in order, track applied versions.

**Acceptance Criteria**:
- [ ] `migrations/runner.py` implements: `apply_migrations()`, `get_applied_migrations()`, `rollback_last()`
- [ ] Migrations applied in alphanumeric order (001_*, 002_*, etc.)
- [ ] `migrations_applied` table tracks: migration_name, applied_at, rolled_back_at
- [ ] Idempotent (applying same migration twice is safe)
- [ ] Error handling: if migration fails, no partial state
- [ ] CLI: `python -m migrations.runner apply` or `rollback`

**File Targets**:
- `migrations/runner.py`

**Dependencies**: Task 2.1.4 (all schema defined)

**Tests**: 
- Integration test: apply migration, verify table creation, check migrations_applied table

**Definition of Done**:
- [ ] Migration runner implemented
- [ ] Can apply migrations in order
- [ ] Rollback supported (optional in Phase 1, but structure ready)
- [ ] migrations_applied table created automatically

---

#### Task 2.2.2: Initialize Database on App Start

**Description**: Create database initialization logic that runs if DB doesn't exist.

**Acceptance Criteria**:
- [ ] `infrastructure/database.py` implements `init_db()` function
- [ ] Checks if database file exists; if not, creates and runs all migrations
- [ ] If database exists, checks schema version (optional in Phase 1)
- [ ] Returns SQLite connection object (thread-safe)
- [ ] Configurable DB path via .env (DATABASE_URL)

**File Targets**:
- `src/infrastructure/database.py`

**Dependencies**: Task 2.2.1

**Tests**: 
- Unit test: init_db() with fresh DB path

**Definition of Done**:
- [ ] Database initializes on first run
- [ ] Connection object returned
- [ ] Thread-safe (or clearly noted single-threaded)
- [ ] Error handling for missing migrations

---

---

## EPIC 3: Backend Services (FastAPI + Core Services)

### Epic Goal
Implement business logic services, database repositories, and API endpoints.

---

### STORY 3.1: Domain Layer (Pure Business Logic)

**Objective**: Implement entities, value objects, and deterministic business rules.

#### Task 3.1.1: Define Domain Entities & Value Objects

**Description**: Create Python dataclasses for Order, OrderLineItem, Item, Payment, User, Money, OrderStatus.

**Acceptance Criteria**:
- [ ] `domain/value_objects.py` defines: `Money` (immutable, cents-based), `OrderStatus` (enum: draft/finalized/voided), `TransactionType` (enum: PURCHASE/SALE/ADJUSTMENT/WASTAGE), `Role` (enum: WAITER/CASHIER/MANAGER/CLERK/ADMIN)
- [ ] `domain/entities.py` defines: `Order`, `OrderLineItem`, `Item`, `Payment`, `User`, `StockLedgerEntry` (all as dataclasses or Pydantic BaseModel)
- [ ] Immutable fields (no setters; use frozen=True)
- [ ] Type hints on all fields
- [ ] Docstrings explaining each field

**File Targets**:
- `src/domain/value_objects.py`
- `src/domain/entities.py`

**Dependencies**: Task 1.1.3

**Tests**: 
- Unit test: create instances, verify immutability, Money arithmetic

**Definition of Done**:
- [ ] Entities defined with type hints
- [ ] Immutable (frozen dataclasses)
- [ ] Docstrings present
- [ ] Unit tests pass

---

#### Task 3.1.2: Implement Business Rules (Tax, Discount, Stock)

**Description**: Create pure functions for tax calculation, discount validation, stock deduction.

**Acceptance Criteria**:
- [ ] `domain/business_rules.py` implements:
  - `calculate_tax(subtotal: Money, tax_rate: float) -> Money` (deterministic)
  - `apply_discount(price: Money, discount_type: str, amount: float) -> Money` (max 50%, validation)
  - `validate_stock_deduction(current_stock: int, qty_to_deduct: int) -> bool` (check sufficiency)
  - `compute_stock_on_hand(ledger_entries: List[StockLedgerEntry]) -> int` (sum ledger)
  - `round_money(value: float) -> Money` (consistent rounding)
- [ ] All functions are pure (no DB calls, no side effects)
- [ ] All functions deterministic (same input → same output)
- [ ] Parameter validation (raise ValueError if invalid)

**File Targets**:
- `src/domain/business_rules.py`

**Dependencies**: Task 3.1.1

**Tests**: 
- Unit test: ≥10 tests per function (edge cases: zero values, max values, rounding)

**Definition of Done**:
- [ ] All business rules implemented
- [ ] Unit tests pass (≥80% coverage)
- [ ] No dependencies on DB/services
- [ ] Deterministic (testable without mocks)

---

### STORY 3.2: Application Services (Orchestration)

**Objective**: Implement high-level services that orchestrate domain logic and repositories.

#### Task 3.2.1: Implement Sales Service

**Description**: Create `SalesService` for order lifecycle: create, add item, apply discount, finalize, void.

**Acceptance Criteria**:
- [ ] `application/sales_service.py` implements:
  - `createOrder(table_id: str) -> Order` (new draft order)
  - `addItem(order_id: str, item_id: str, qty: int) -> Order` (add to draft, recalculate totals)
  - `applyDiscount(order_id: str, discount_type: str, amount: float) -> Order` (validate permission)
  - `finalizeOrder(order_id: str, payment: PaymentInput) -> FinalizedBill` (all-or-nothing transaction)
  - `voidOrder(order_id: str, reason: str, approver_id: str) -> None` (requires manager role)
  - `getOrder(order_id: str) -> Order` (fetch by ID)
- [ ] All methods are async
- [ ] Transactions: use DB context manager (begin/commit/rollback)
- [ ] Call domain functions for validation (no business logic in service)
- [ ] Call AuditService.logOperation() for all state changes
- [ ] Call InventoryService.deductStock() when finalizing

**File Targets**:
- `src/application/sales_service.py`
- `src/application/exceptions.py` (custom exceptions)

**Dependencies**: Task 3.1.2, Task 2.1.4 (schema defined)

**Tests**: 
- Integration test: create order, add items, finalize with payment, verify receipt number

**Definition of Done**:
- [ ] SalesService implemented with all methods
- [ ] Transactions working (rollback on error)
- [ ] AuditService called
- [ ] Integration test passes
- [ ] Docstrings on public methods

---

#### Task 3.2.2: Implement Inventory Service

**Description**: Create `InventoryService` for stock tracking: record stock-in, adjustments, deduct on sale.

**Acceptance Criteria**:
- [ ] `application/inventory_service.py` implements:
  - `recordStockIn(item_id: str, qty: int, reference: str) -> StockLedgerEntry` (add stock, append ledger)
  - `recordAdjustment(item_id: str, qty_change: int, reason: str, approver: User) -> StockLedgerEntry` (negative/positive, requires approval for negative)
  - `deductStock(item_id: str, qty: int, reason: str, reference_id: str) -> StockLedgerEntry` (sale deduction, validate sufficiency)
  - `getStockOnHand(item_id: str) -> int` (compute from ledger)
  - `getLowStockItems() -> List[Item]` (where stock < reorder_level)
- [ ] All methods async
- [ ] Validation: check stock sufficiency before deduction (fail early)
- [ ] Ledger append-only (never update existing entries)

**File Targets**:
- `src/application/inventory_service.py`

**Dependencies**: Task 3.2.1, Task 2.1.4

**Tests**: 
- Integration test: add stock, sell (deduct), verify ledger + stock_on_hand, test low-stock alerts

**Definition of Done**:
- [ ] InventoryService implemented
- [ ] Ledger append-only verified
- [ ] Stock computation correct (sum ledger)
- [ ] Integration tests pass

---

#### Task 3.2.3: Implement Auth Service

**Description**: Create `AuthService` for user authentication, role validation, permission checks.

**Acceptance Criteria**:
- [ ] `application/auth_service.py` implements:
  - `login(username: str, pin: str) -> User` (hash pin, validate, create session)
  - `logout(user_id: str) -> None` (end session)
  - `getCurrentUser() -> Optional[User]` (from session context)
  - `validatePermission(user: User, action: str) -> bool` (check role against action)
  - `getUserRole(user_id: str) -> Role` (fetch from DB)
- [ ] PIN validated via bcrypt.compare()
- [ ] Session created in sessions table on successful login
- [ ] Session expires after 30 min inactivity (or on logout)
- [ ] Permission matrix: waiter, cashier, manager, clerk, admin (roles defined in ARCHITECTURE.md)

**File Targets**:
- `src/application/auth_service.py`

**Dependencies**: Task 3.1.1

**Tests**: 
- Unit test: bcrypt hashing, PIN validation
- Integration test: login/logout flow, session tracking

**Definition of Done**:
- [ ] AuthService implemented
- [ ] PIN hashed with bcrypt
- [ ] Sessions tracked
- [ ] Permission matrix enforced
- [ ] Tests pass

---

#### Task 3.2.4: Implement Audit Service

**Description**: Create `AuditService` for logging all state changes.

**Acceptance Criteria**:
- [ ] `application/audit_service.py` implements:
  - `logOperation(entity_type: str, entity_id: str, operation: str, user_id: str, old_state: dict, new_state: dict, reason: str) -> None` (insert audit_log)
  - `queryAuditLog(entity_type: str, entity_id: str, start_date: datetime, end_date: datetime) -> List[AuditLogEntry]` (search with filters)
  - Automatic logging: created_at, updated_at, created_by, updated_by on all entities
- [ ] Audit log JSON serialization (old_state, new_state)
- [ ] Never delete audit logs (soft-delete only)
- [ ] Index audit_log table for efficient queries

**File Targets**:
- `src/application/audit_service.py`

**Dependencies**: Task 3.1.1, Task 2.1.2

**Tests**: 
- Integration test: log operation, query by entity/date, verify immutability

**Definition of Done**:
- [ ] AuditService implemented
- [ ] Audit logs queryable by entity, timestamp, user
- [ ] Integration test passes
- [ ] Soft-delete enforced (no hard-deletes)

---

#### Task 3.2.5: Implement Reporting Service

**Description**: Create `ReportingService` for daily sales summary and inventory snapshot.

**Acceptance Criteria**:
- [ ] `application/reporting_service.py` implements:
  - `dailySalesSummary(date: datetime) -> DailySalesReport` (total revenue, count, top items, payment methods breakdown)
  - `inventorySnapshot() -> InventorySnapshot` (all items with stock_on_hand, low-stock alerts)
  - `searchTransactions(filters: SearchFilters) -> List[TransactionRecord]` (by date, user, item, payment method)
- [ ] All queries read-only (no state changes)
- [ ] Performance target: ≤5s for daily summary with 1000 transactions
- [ ] Results include: totals, item-wise breakdown, payment method split

**File Targets**:
- `src/application/reporting_service.py`

**Dependencies**: Task 3.2.1, Task 3.2.2

**Tests**: 
- Integration test: generate daily report, verify totals, test search filters

**Definition of Done**:
- [ ] ReportingService implemented
- [ ] Daily summary generates correct totals
- [ ] Search/filters work
- [ ] Performance acceptable
- [ ] Tests pass

---

### STORY 3.3: Repository Layer (Data Access)

**Objective**: Implement data access abstraction over SQLite.

#### Task 3.3.1: Implement Repository Base & Order Repository

**Description**: Create base repository class and OrderRepository for CRUD + queries.

**Acceptance Criteria**:
- [ ] `infrastructure/repositories.py` implements:
  - `BaseRepository` (abstract base with create, get, list, update methods)
  - `OrderRepository` (subclass): create_order(), get_order(), finalize_order(), get_orders_by_date(), search_orders()
  - All methods return domain entities (Order, OrderLineItem, etc.)
  - Use parameterized queries (prevent SQL injection)
- [ ] Transactions: use context managers or explicit begin/commit/rollback
- [ ] Connection pooling (sqlite3.connect with check_same_thread=False for Flet)

**File Targets**:
- `src/infrastructure/repositories.py`

**Dependencies**: Task 2.2.2, Task 3.1.1

**Tests**: 
- Integration test: insert order, fetch by ID, verify fields

**Definition of Done**:
- [ ] BaseRepository implemented
- [ ] OrderRepository CRUD working
- [ ] Parameterized queries used
- [ ] Tests pass

---

#### Task 3.3.2: Implement Other Repositories (Item, User, Audit, Stock)

**Description**: Implement ItemRepository, UserRepository, AuditLogRepository, StockLedgerRepository.

**Acceptance Criteria**:
- [ ] ItemRepository: create_item(), get_item(), list_items(), update_item_price()
- [ ] UserRepository: create_user(), get_user(), list_users(), validate_pin()
- [ ] AuditLogRepository: create_log(), query_logs_by_entity(), query_logs_by_user()
- [ ] StockLedgerRepository: append_entry(), get_ledger_by_item(), compute_stock_on_hand()
- [ ] All return domain entities

**File Targets**:
- `src/infrastructure/repositories.py` (extend from Task 3.3.1)

**Dependencies**: Task 3.3.1

**Tests**: 
- Integration test: CRUD operations on each repository

**Definition of Done**:
- [ ] All repositories implemented
- [ ] CRUD operations work
- [ ] Queries return correct entities
- [ ] Tests pass

---

### STORY 3.4: FastAPI Endpoints

**Objective**: Create REST API endpoints for UI to call.

#### Task 3.4.1: Implement Auth Endpoints

**Description**: Create POST /api/auth/login, POST /api/auth/logout, GET /api/auth/me.

**Acceptance Criteria**:
- [ ] `api/auth_routes.py` implements:
  - `POST /api/auth/login` (body: {username, pin}) → {user_id, role, token}
  - `POST /api/auth/logout` (clears session)
  - `GET /api/auth/me` (returns current user from session)
- [ ] Auth guard on all endpoints (decorator: @require_auth)
- [ ] Validate PIN via AuthService
- [ ] Return structured error responses (e.g., {"error": "Invalid PIN", "code": "AUTH_001"})

**File Targets**:
- `src/api/auth_routes.py`
- `src/api/dependencies.py` (auth guard decorator)

**Dependencies**: Task 3.2.3

**Tests**: 
- Integration test: login with valid PIN, invalid PIN, logout, check me endpoint

**Definition of Done**:
- [ ] Auth endpoints implemented
- [ ] Auth guard working on protected routes
- [ ] Error responses structured
- [ ] Tests pass

---

#### Task 3.4.2: Implement Sales Endpoints

**Description**: Create POST /api/sales/orders, POST /api/sales/orders/{id}/items, POST /api/sales/orders/{id}/finalize.

**Acceptance Criteria**:
- [ ] `api/sales_routes.py` implements:
  - `POST /api/sales/orders` (body: {table_id}) → Order
  - `POST /api/sales/orders/{id}/items` (body: {item_id, qty}) → Order
  - `PATCH /api/sales/orders/{id}/discount` (body: {discount_type, amount}) → Order
  - `POST /api/sales/orders/{id}/finalize` (body: {payment_method, amount}) → FinalizedBill
  - `POST /api/sales/orders/{id}/void` (body: {reason, approver_id}) → void confirmation
  - `GET /api/sales/orders/{id}` → Order details
- [ ] All endpoints use @require_auth decorator
- [ ] Call SalesService methods
- [ ] Return serialized domain entities (Pydantic models)

**File Targets**:
- `src/api/sales_routes.py`

**Dependencies**: Task 3.2.1, Task 3.4.1

**Tests**: 
- Integration test: full order flow (create → add items → finalize)

**Definition of Done**:
- [ ] Sales endpoints implemented
- [ ] Full order flow works end-to-end
- [ ] Error responses for invalid operations
- [ ] Tests pass

---

#### Task 3.4.3: Implement Inventory & Reporting Endpoints

**Description**: Create GET /api/inventory/items, POST /api/inventory/stock-in, GET /api/reports/daily-sales.

**Acceptance Criteria**:
- [ ] `api/inventory_routes.py` implements:
  - `GET /api/inventory/items` → list all items with stock_on_hand
  - `GET /api/inventory/items/{id}` → item details + stock ledger
  - `POST /api/inventory/stock-in` (body: {item_id, qty, reference}) → StockLedgerEntry
  - `POST /api/inventory/adjustments` (body: {item_id, qty_change, reason}) → StockLedgerEntry (manager only)
- [ ] `api/reports_routes.py` implements:
  - `GET /api/reports/daily-sales?date=2026-02-09` → DailySalesReport
  - `GET /api/reports/inventory-snapshot` → InventorySnapshot
  - `GET /api/reports/transactions?start_date=...&end_date=...` → search results

**File Targets**:
- `src/api/inventory_routes.py`
- `src/api/reports_routes.py`

**Dependencies**: Task 3.2.2, Task 3.2.5, Task 3.4.1

**Tests**: 
- Integration test: stock-in, query stock, generate report

**Definition of Done**:
- [ ] Inventory endpoints working
- [ ] Reporting endpoints working
- [ ] Permission checks enforced
- [ ] Tests pass

---

#### Task 3.4.4: Create FastAPI App & Dependency Injection

**Description**: Set up FastAPI app, register all routes, configure dependency injection.

**Acceptance Criteria**:
- [ ] `api/app.py` initializes FastAPI app with:
  - All route blueprints (auth, sales, inventory, reports)
  - Global error handlers (validation errors, auth errors, business logic errors)
  - CORS enabled (for Flet to localhost:8000)
  - Documentation at /docs (OpenAPI)
- [ ] `api/dependencies.py` implements:
  - `get_current_user()` (dependency: extract from session)
  - `require_auth()` (decorator for protected routes)
  - `require_role(role)` (decorator for role-specific routes)
  - `get_db()` (dependency: SQLite connection)
  - Service injection (SalesService, InventoryService, etc.)

**File Targets**:
- `src/api/app.py`
- `src/api/dependencies.py`

**Dependencies**: Task 3.4.1, Task 3.4.2, Task 3.4.3

**Tests**: 
- Unit test: dependency injection works
- Integration test: start server, hit endpoint, verify response

**Definition of Done**:
- [ ] FastAPI app configured
- [ ] All routes registered
- [ ] Dependencies injectable
- [ ] Error handling working
- [ ] Tests pass

---

---

## EPIC 4: Flet UI Layer

### Epic Goal
Create touch-first, low-literacy-friendly POS UI screens.

---

### STORY 4.1: UI Infrastructure & Auth Screen

**Objective**: Set up Flet app, navigation, auth screen.

#### Task 4.1.1: Create Flet App Structure & Navigation

**Description**: Set up main Flet app, page routing, screen navigation.

**Acceptance Criteria**:
- [ ] `ui/app.py` initializes Flet app with:
  - Window size (full screen recommended, min 1024x768)
  - Theme (light, dark, or system)
  - Font sizes for accessibility (base 16px, header 24px+)
  - Icon pack (Material Design icons)
- [ ] Navigation system: ability to switch between screens (auth, POS, products, reports)
- [ ] State management: current_user, current_order, current_screen (use simple dict or class)
- [ ] Error overlay: display errors globally (top banner)
- [ ] Startup: check if user logged in; if yes, go to POS; else go to auth

**File Targets**:
- `src/ui/app.py`
- `src/ui/utils/ui_helpers.py` (helper functions: format_money, responsive_size, etc.)

**Dependencies**: Task 1.1.3

**Tests**: 
- Manual UI testing (start app, navigate between screens)

**Definition of Done**:
- [ ] App starts without errors
- [ ] Navigation working
- [ ] Theme applied
- [ ] Responsive layout

---

#### Task 4.1.2: Implement Auth (Login) Screen

**Description**: Create login screen with username field, PIN keypad, login button.

**Acceptance Criteria**:
- [ ] `ui/screens/auth_screen.py` implements:
  - Username text input field (large, 20px font)
  - PIN numeric keypad (0-9, clear, backspace)
  - Large Login button (80px+ height, contrasting color)
  - Error message display (red text, if invalid PIN)
  - Loading state (disable button, show spinner during login)
- [ ] Call `POST /api/auth/login` via FastAPI client (httpx or aiohttp)
- [ ] On success: navigate to POS screen, store user_id + role in app state
- [ ] On error: show error message, clear PIN field
- [ ] Accessibility: high contrast, large fonts, clear labels

**File Targets**:
- `src/ui/screens/auth_screen.py`

**Dependencies**: Task 3.4.1, Task 4.1.1

**Tests**: 
- Manual UI testing: login with valid/invalid credentials

**Definition of Done**:
- [ ] Auth screen renders
- [ ] Login flow works
- [ ] Error handling visible
- [ ] Large touch-friendly buttons

---

### STORY 4.2: POS (Order Entry) Screen

**Objective**: Create main POS screen for fast order entry, item selection, payment.

#### Task 4.2.1: Implement POS Screen Layout & Components

**Description**: Create POS screen with order summary, item picker, discount, payment buttons.

**Acceptance Criteria**:
- [ ] `ui/screens/pos_screen.py` implements main layout:
  - **Left panel** (60% width): order summary (table #, item list, running total, tax, total)
  - **Right panel** (40% width): item picker (search/scroll, select item, qty spinner, add button)
  - **Bottom bar** (100% width): discount button, payment button, void button, print button
- [ ] **Order Summary Component** (`ui/components/order_summary.py`):
  - Display order ID, table #, date/time
  - List items with qty, unit price, line total
  - Show subtotal, tax (18% hardcoded for Phase 1), discount, total
  - Auto-update when items added/removed
  - Large, clear font (20px+ for totals)
- [ ] **Item Picker Component** (`ui/components/item_picker.py`):
  - Fetch items from `GET /api/inventory/items`
  - Search filter (by name, category)
  - Display item name, price, stock status (green/yellow/red)
  - Qty spinner (+ / - buttons, numeric input)
  - Large Add Item button

**File Targets**:
- `src/ui/screens/pos_screen.py`
- `src/ui/components/order_summary.py`
- `src/ui/components/item_picker.py`
- `src/ui/components/buttons.py` (reusable button styles)

**Dependencies**: Task 4.1.1, Task 3.4.2

**Tests**: 
- Manual UI testing: render screen, verify layout, add items

**Definition of Done**:
- [ ] POS screen renders without errors
- [ ] Layout responsive (left/right panels)
- [ ] Components responsive
- [ ] Large, accessible fonts/buttons

---

#### Task 4.2.2: Implement Order Entry Workflow (Create, Add Items, Calculate Totals)

**Description**: Implement Flet logic to call FastAPI endpoints and update UI state.

**Acceptance Criteria**:
- [ ] On screen load: call `POST /api/sales/orders` (with table_id from dropdown/input) → create draft order
- [ ] On "Add Item" button: call `POST /api/sales/orders/{id}/items` (with item_id, qty) → update order, recalculate totals
- [ ] Auto-calculate totals (subtotal, tax @ 18%, discount, total) in UI (or fetch from API)
- [ ] On qty change: update line item without re-fetching entire order (optimistic UI update)
- [ ] Display running total prominently (36px+ font, bold)
- [ ] Show item list with remove button (trash icon) for each item

**File Targets**:
- `src/ui/screens/pos_screen.py` (extend from Task 4.2.1)

**Dependencies**: Task 4.2.1, Task 3.4.2

**Tests**: 
- Integration test: create order, add 3 items, verify totals

**Definition of Done**:
- [ ] Order creation working
- [ ] Items added successfully
- [ ] Totals calculated correctly
- [ ] UI updates smoothly

---

#### Task 4.2.3: Implement Discount & Payment Flow

**Description**: Implement discount application and payment finalization screens.

**Acceptance Criteria**:
- [ ] **Discount UI**:
  - Button opens discount dialog (percent vs. amount)
  - Input field for discount value
  - Validate: max 50% or max amount = order subtotal
  - Call `PATCH /api/sales/orders/{id}/discount`
  - Update order summary
- [ ] **Payment UI** (modal/dialog):
  - Payment method selector (Cash, Card, Voucher)
  - Amount input (pre-filled with order total)
  - Confirm button (large, green)
  - Call `POST /api/sales/orders/{id}/finalize`
  - On success: show receipt screen (Task 4.2.4)
- [ ] **Void/Cancel UI**:
  - Void button (red, requires confirmation)
  - Confirmation dialog: "Void order? This cannot be undone."
  - Call `POST /api/sales/orders/{id}/void`
  - Return to new order screen after void

**File Targets**:
- `src/ui/screens/pos_screen.py` (add dialogs)

**Dependencies**: Task 4.2.2, Task 3.4.2

**Tests**: 
- Integration test: apply discount, process payment, verify receipt

**Definition of Done**:
- [ ] Discount flow working
- [ ] Payment finalization working
- [ ] Receipt generated and displayed
- [ ] Void confirmed and logged

---

#### Task 4.2.4: Implement Receipt Screen & Printing

**Description**: Create receipt display screen and printer integration stub.

**Acceptance Criteria**:
- [ ] `ui/screens/receipt_screen.py` displays:
  - Receipt header (HMS, branch name, date/time)
  - Items with qty, unit price, line total (formatted)
  - Subtotal, tax, discount, total (large, bold)
  - Payment method, reference
  - Receipt number (REC-YYYY-MMDD-######)
  - Thank you message
  - Buttons: Print, Email, New Order
- [ ] **Printing**:
  - Call `infrastructure/printer_stub.py` (stub for Phase 1, no actual printer)
  - Log print action to audit_log
  - Show "Print sent" message (not guaranteed to print)
- [ ] **UI Layout**:
  - Simulate receipt paper width (80mm = ~300px)
  - Centered, monospace font for receipt
  - Clear section separation

**File Targets**:
- `src/ui/screens/receipt_screen.py`
- `src/infrastructure/printer_stub.py`

**Dependencies**: Task 4.2.3

**Tests**: 
- Manual UI testing: finalize order, view receipt, trigger print

**Definition of Done**:
- [ ] Receipt displays correctly
- [ ] All details visible
- [ ] Print stub working
- [ ] Receipt format clear

---

### STORY 4.3: Inventory & Products Screen

**Objective**: Create product management screen (view, add, update items).

#### Task 4.3.1: Implement Products Screen (List & CRUD)

**Description**: Create screen to view all products, add new, update prices, manage stock.

**Acceptance Criteria**:
- [ ] `ui/screens/products_screen.py` implements:
  - **Product List**: table/grid with columns (Item Name, Category, Unit Price, Stock On Hand, Reorder Level)
  - **Search/Filter**: by name, category, low-stock alert
  - **Add Product Button**: opens dialog with name, category, price, reorder level inputs
  - **Edit Item**: click item → edit dialog (update price, reorder level)
  - **Stock-In Button**: record stock-in (item selector, qty, reference)
  - **Stock Adjustment Button** (manager only): qty change, reason, approval
- [ ] Calls:
  - `GET /api/inventory/items` (fetch all)
  - `POST /api/inventory/items` (create, if endpoint exists; or manage locally in Phase 1)
  - `POST /api/inventory/stock-in` (record stock-in)
  - `POST /api/inventory/adjustments` (record adjustment)
- [ ] Low-stock highlighting (yellow if < reorder level, red if out of stock)

**File Targets**:
- `src/ui/screens/products_screen.py`

**Dependencies**: Task 4.1.1, Task 3.4.3

**Tests**: 
- Manual UI testing: list products, add new product, stock-in, low-stock alert

**Definition of Done**:
- [ ] Products screen renders
- [ ] CRUD operations working
- [ ] Stock levels accurate
- [ ] Low-stock alerts visible

---

### STORY 4.4: Reports Screen

**Objective**: Create daily sales and inventory reporting screen.

#### Task 4.4.1: Implement Daily Reports Screen

**Description**: Create screen showing daily sales summary, top items, payment methods breakdown.

**Acceptance Criteria**:
- [ ] `ui/screens/reports_screen.py` implements:
  - **Daily Sales Summary** (selected date or today):
    - Total revenue (large, bold)
    - Transaction count
    - Payment method breakdown (Cash %, Card %, Voucher %)
    - Top 5 items (by quantity or revenue)
    - Average order value
  - **Inventory Snapshot**:
    - All items with stock_on_hand
    - Low-stock alerts (red)
    - Items needing reorder
  - **Search/Filter**:
    - Date range picker (today, this week, this month)
    - Payment method filter
    - Item category filter
  - **Export**: button to export to CSV (Phase 2 nice-to-have)
- [ ] Calls:
  - `GET /api/reports/daily-sales?date=...` (fetch report)
  - `GET /api/reports/inventory-snapshot`
  - `GET /api/reports/transactions?filters=...` (search)

**File Targets**:
- `src/ui/screens/reports_screen.py`

**Dependencies**: Task 4.1.1, Task 3.4.3

**Tests**: 
- Manual UI testing: view daily report, check totals, search by date

**Definition of Done**:
- [ ] Reports screen renders
- [ ] Daily summary correct
- [ ] Inventory snapshot accurate
- [ ] Date filters working

---

### STORY 4.5: UI Polish & Accessibility

**Objective**: Ensure touch-friendly, low-literacy-friendly UX across all screens.

#### Task 4.5.1: Implement Responsive Layout & Touch Optimization

**Description**: Ensure all buttons, inputs, and layouts are touch-friendly (min 44px, optimal 56px).

**Acceptance Criteria**:
- [ ] All clickable elements: min 56px height, 40px width
- [ ] Touch target spacing: ≥8px between targets
- [ ] No hover states required (use color change for active state)
- [ ] Landscape orientation supported (most POS devices are landscape)
- [ ] Text: min 16px, headers 24px+
- [ ] High contrast: WCAG AA minimum (Phase 1; Phase 2 can improve to AAA)
- [ ] Color-blind friendly: not relying on red/green alone (use icons + text)

**File Targets**:
- `src/ui/components/buttons.py` (enforce min sizes)
- `src/ui/utils/ui_helpers.py` (responsive size function)

**Dependencies**: Task 4.2.4 (all screens created)

**Tests**: 
- Manual UI testing: test on 10" tablet, verify touch targets

**Definition of Done**:
- [ ] All buttons 56px+ height
- [ ] Text sizes enforced
- [ ] Layout responsive
- [ ] High contrast verified

---

#### Task 4.5.2: Implement Error & Loading States

**Description**: Ensure all API calls show loading spinners and errors are user-friendly.

**Acceptance Criteria**:
- [ ] Loading states:
  - Disable buttons during API call
  - Show spinner (rotating icon) while waiting
  - Display "Processing..." message
- [ ] Error handling:
  - Catch API errors (network, validation, server)
  - Show error message in user-friendly language (e.g., "Item out of stock" instead of "400: INSUFFICIENT_STOCK")
  - Provide recovery action (Retry, Cancel, Back)
- [ ] Success feedback:
  - Toast/snackbar for successful operations ("Order finalized ✓")
  - Play subtle sound (optional, Phase 2+)

**File Targets**:
- `src/ui/utils/ui_helpers.py` (error formatting)
- `src/ui/screens/*.py` (add loading/error states)

**Dependencies**: Task 4.5.1

**Tests**: 
- Manual UI testing: trigger errors (network offline, invalid input), verify feedback

**Definition of Done**:
- [ ] Loading spinners visible
- [ ] Error messages clear
- [ ] Recovery options available
- [ ] Success feedback visible

---

---

## EPIC 5: Logging & Audit

### Epic Goal
Implement structured logging to database and file system.

---

### STORY 5.1: Logging Infrastructure

#### Task 5.1.1: Implement Structured Logging (DB + File)

**Description**: Create logging handler that writes to both SQLite and rotating file logs.

**Acceptance Criteria**:
- [ ] `infrastructure/logging_handler.py` implements:
  - Structured JSON logging (timestamp, level, category, user_id, action, entity_id, message, details)
  - Write to SQLite `system_log` table
  - Write to rotating file logs (`logs/hms-YYYY-MM-DD.log`, max 100MB)
  - Log levels: DEBUG, INFO, WARN, ERROR
  - Configurable via .env (LOG_LEVEL, LOG_DIR)
- [ ] Categories: sales.billing, inventory.stock, auth.login, system.error, etc.
- [ ] No logging of secrets (PIN, full payment details)
- [ ] Queryable logs: `queryLogs(category, user_id, start_date, end_date)` function

**File Targets**:
- `src/infrastructure/logging_handler.py`

**Dependencies**: Task 2.2.2

**Tests**: 
- Unit test: log message, verify DB + file entries
- Integration test: query logs by category/date

**Definition of Done**:
- [ ] Logging to DB working
- [ ] Logging to file working
- [ ] Rotating file logs working
- [ ] Tests pass

---

#### Task 5.1.2: Audit Logging for State Changes

**Description**: Automatically log all state-changing operations (Create, Update, Void, Finalize).

**Acceptance Criteria**:
- [ ] AuditService (Task 3.2.4) calls:
  - logOperation() for every state change (order, payment, inventory, user)
  - Log includes: entity_type, entity_id, operation, user_id, old_state (JSON), new_state (JSON), reason
- [ ] Middleware/decorator to auto-log FastAPI endpoint responses:
  - Wrap each service method call
  - Capture input params, output result, execution time
- [ ] Example entries:
  - Order finalized: {entity_type: "Order", entity_id: "ORD-123", operation: "FINALIZE", old_state: {status: "draft"}, new_state: {status: "finalized", receipt_number: "REC-..."}}
  - Stock deducted: {entity_type: "StockLedger", operation: "ADD", transaction_type: "SALE", qty_change: -2, reference_id: "ORD-123"}

**File Targets**:
- `src/application/audit_service.py` (Task 3.2.4)

**Dependencies**: Task 5.1.1

**Tests**: 
- Integration test: execute state-changing operation, verify audit log entry

**Definition of Done**:
- [ ] All state changes logged
- [ ] Audit entries queryable
- [ ] Tests pass

---

---

## EPIC 6: Testing & Deployment

### Epic Goal
Implement test suite, CI/CD basics, and deployment package.

---

### STORY 6.1: Unit Tests (Domain Logic)

#### Task 6.1.1: Write Unit Tests for Business Rules

**Description**: Test all pure functions in domain/business_rules.py.

**Acceptance Criteria**:
- [ ] `tests/unit/test_business_rules.py` includes:
  - `test_calculate_tax()` (various rates, rounding edge cases)
  - `test_apply_discount_percentage()` (0%, 10%, 50%, >50% should fail)
  - `test_apply_discount_absolute()` (valid, exceeds price should fail)
  - `test_validate_stock_deduction()` (sufficient, insufficient)
  - `test_compute_stock_on_hand()` (sum ledger entries, mix of +/-)
  - `test_round_money()` (banker's rounding, edge cases)
- [ ] Coverage: ≥80% of domain/business_rules.py
- [ ] Edge cases: 0, negative, max values, rounding boundaries

**File Targets**:
- `tests/unit/test_business_rules.py`

**Dependencies**: Task 3.1.2

**Tests**: Pytest with ≥10 cases per function

**Definition of Done**:
- [ ] All tests pass
- [ ] ≥80% coverage
- [ ] Edge cases covered

---

#### Task 6.1.2: Write Unit Tests for Entities & Value Objects

**Description**: Test domain entities and value objects.

**Acceptance Criteria**:
- [ ] `tests/unit/test_value_objects.py` tests:
  - Money creation, arithmetic, immutability
  - OrderStatus enum values, transitions
  - TransactionType enum
  - Role enum
- [ ] `tests/unit/test_entities.py` tests:
  - Entity creation, field validation
  - Immutability (frozen dataclasses)

**File Targets**:
- `tests/unit/test_value_objects.py`
- `tests/unit/test_entities.py`

**Dependencies**: Task 3.1.1

**Tests**: Pytest

**Definition of Done**:
- [ ] All entity tests pass
- [ ] Immutability verified

---

### STORY 6.2: Integration Tests (Service + Repository + DB)

#### Task 6.2.1: Set Up Test Database & Fixtures

**Description**: Create pytest fixtures for test DB, sample data, and mocks.

**Acceptance Criteria**:
- [ ] `tests/conftest.py` implements:
  - `test_db` fixture (in-memory SQLite or temp file)
  - `sample_user` fixture (manager user)
  - `sample_item` fixture (biryani, ₹300)
  - `sample_order` fixture (draft order)
  - Database cleanup after each test (rollback or in-memory fresh)
- [ ] All fixtures return domain entities (not raw DB rows)

**File Targets**:
- `tests/conftest.py`

**Dependencies**: Task 3.3.2, Task 2.2.2

**Tests**: Pytest fixtures

**Definition of Done**:
- [ ] Fixtures work
- [ ] Test DB isolated per test

---

#### Task 6.2.2: Write Integration Test for Order Finalization Flow

**Description**: Test complete order lifecycle: create → add items → apply discount → finalize → audit log.

**Acceptance Criteria**:
- [ ] `tests/integration/test_sales_flow.py` tests:
  - `test_create_order_finalize_payment()`: create order, add item, finalize with payment, verify receipt number and audit log
  - `test_finalize_updates_stock()`: finalize order with 2 items, verify stock_on_hand updated
  - `test_void_order()`: void finalized order, verify status and audit log
  - `test_discount_validation()`: apply invalid discount (>50%), verify error
- [ ] Coverage: All SalesService methods
- [ ] Verify: order state, audit log entries, stock changes, payment recorded

**File Targets**:
- `tests/integration/test_sales_flow.py`

**Dependencies**: Task 6.2.1, Task 3.2.1

**Tests**: Pytest async

**Definition of Done**:
- [ ] All integration tests pass
- [ ] Order flow complete and verified

---

#### Task 6.2.3: Write Integration Tests for Inventory & Auth

**Description**: Test InventoryService and AuthService.

**Acceptance Criteria**:
- [ ] `tests/integration/test_inventory_flow.py`:
  - `test_stock_in_updates_ledger()`: record stock-in, verify ledger entry and stock_on_hand
  - `test_sale_deduction()`: finalize order, verify stock deducted and ledger appended
  - `test_low_stock_alert()`: trigger low-stock condition, verify list
- [ ] `tests/integration/test_auth_flow.py`:
  - `test_login_valid_pin()`: login with correct PIN, verify user and session
  - `test_login_invalid_pin()`: login with wrong PIN, verify error
  - `test_permission_check()`: waiter cannot void order (manager only), verify denied
  - `test_logout()`: logout, verify session cleared

**File Targets**:
- `tests/integration/test_inventory_flow.py`
- `tests/integration/test_auth_flow.py`

**Dependencies**: Task 6.2.2

**Tests**: Pytest async

**Definition of Done**:
- [ ] Inventory tests pass
- [ ] Auth tests pass
- [ ] Permission enforcement verified

---

### STORY 6.3: Smoke Tests (Offline Mode)

#### Task 6.3.1: Write Offline Workflow Smoke Tests

**Description**: Test complete POS workflow without network.

**Acceptance Criteria**:
- [ ] `tests/smoke/test_offline_workflow.py`:
  - `test_create_order_offline()`: create order, verify state persisted locally
  - `test_finalize_offline()`: finalize order, verify receipt number and audit
  - `test_inventory_query_offline()`: query stock without network
  - `test_report_offline()`: generate daily report without network
- [ ] Mock network (disable requests), verify all operations succeed
- [ ] Performance: each operation ≤ 1s (local only)

**File Targets**:
- `tests/smoke/test_offline_workflow.py`

**Dependencies**: All integration tests (6.2.3)

**Tests**: Pytest (mock network unavailable)

**Definition of Done**:
- [ ] All offline operations work
- [ ] No network calls made
- [ ] Performance acceptable

---

### STORY 6.4: API Tests (FastAPI Endpoints)

#### Task 6.4.1: Write API Integration Tests

**Description**: Test FastAPI endpoints via HTTP (use TestClient).

**Acceptance Criteria**:
- [ ] `tests/integration/test_api.py` (or separate per endpoint):
  - `test_api_create_order()`: POST /api/sales/orders → 200, order returned
  - `test_api_add_item()`: POST /api/sales/orders/{id}/items → 200, order updated
  - `test_api_finalize()`: POST /api/sales/orders/{id}/finalize → 200, receipt_number assigned
  - `test_api_auth_login()`: POST /api/auth/login → 200, user + token returned
  - `test_api_get_daily_report()`: GET /api/reports/daily-sales → 200, totals correct
  - `test_api_permission_denied()`: waiter tries to void → 403 Forbidden
- [ ] Use TestClient from FastAPI testing utils

**File Targets**:
- `tests/integration/test_api.py`

**Dependencies**: Task 3.4.4

**Tests**: Pytest with TestClient

**Definition of Done**:
- [ ] All endpoint tests pass
- [ ] Permission enforcement verified via API
- [ ] Error responses correct

---

### STORY 6.5: Deployment Packaging

#### Task 6.5.1: Create Executable Installer

**Description**: Package app as single executable (Windows .exe, or Python wheel).

**Acceptance Criteria**:
- [ ] Options:
  - **PyInstaller**: `pyinstaller --onefile src/__main__.py` → single .exe
  - **Python wheel**: `python setup.py bdist_wheel` → installable package
- [ ] Installer includes:
  - Flet framework
  - FastAPI + Uvicorn
  - SQLite
  - All dependencies
- [ ] Installer sets up:
  - User home directory: `~/.hms/` (database, logs, config)
  - Desktop shortcut (Windows)
  - Config file: `~/.hms/.env` (with defaults)
- [ ] Installer size: ≤200MB (compressed)
- [ ] First run initializes DB schema

**File Targets**:
- `setup.py` (or pyproject.toml)
- `build_installer.sh` or `build_installer.bat` (build script)

**Dependencies**: All code complete (Epics 1–5)

**Tests**: 
- Manual: install on clean Windows machine, verify app runs

**Definition of Done**:
- [ ] Installer created
- [ ] App runs from installer
- [ ] DB initialized on first run
- [ ] Desktop shortcut works

---

#### Task 6.5.2: Create Setup Documentation & Release Notes

**Description**: Write README, installation guide, release notes.

**Acceptance Criteria**:
- [ ] `README.md`:
  - Quick start (download, install, run)
  - System requirements (Windows 10+, 2GB RAM, 500MB disk)
  - Screenshots (POS screen, report screen)
  - Support email/contact
- [ ] `DEPLOYMENT.md` or `INSTALLATION.md`:
  - Step-by-step installation
  - Troubleshooting (common errors)
  - Uninstall procedure
- [ ] `RELEASE_NOTES_v1.0.md`:
  - Features included in Phase 1
  - Known limitations
  - Future roadmap (Phase 2/3)

**File Targets**:
- `README.md` (update from Task 1.1.1)
- `DEPLOYMENT.md`
- `RELEASE_NOTES_v1.0.md`

**Dependencies**: Task 6.5.1

**Tests**: Manual (user reads and follows guide)

**Definition of Done**:
- [ ] Docs written and reviewed
- [ ] Installation guide clear
- [ ] Known issues documented

---

---

## Task Dependencies Graph

```
1.1.1 (Git init)
  ├─→ 1.1.2 (venv + deps)
  ├─→ 1.1.3 (folder structure)
  │    ├─→ 3.1.1 (domain entities)
  │    │    ├─→ 3.1.2 (business rules)
  │    │    │    ├─→ 3.2.1 (sales service)
  │    │    │    ├─→ 3.2.2 (inventory service)
  │    │    │    ├─→ 3.2.3 (auth service)
  │    │    │    ├─→ 6.1.1 (unit tests)
  │    │    │    └─→ 6.1.2 (entity tests)
  │    └─→ 2.1.1–2.1.4 (schema design)
  │         ├─→ 2.2.1 (migration runner)
  │         ├─→ 2.2.2 (DB init)
  │         │    ├─→ 3.3.1 (order repo)
  │         │    ├─→ 3.3.2 (other repos)
  │         │    │    ├─→ 3.4.1–3.4.4 (API endpoints)
  │         │    │    │    ├─→ 4.1.1–4.1.2 (Flet app + auth screen)
  │         │    │    │    ├─→ 4.2.1–4.2.4 (POS screen)
  │         │    │    │    ├─→ 4.3.1 (products screen)
  │         │    │    │    ├─→ 4.4.1 (reports screen)
  │         │    │    │    ├─→ 4.5.1–4.5.2 (UI polish)
  │         │    │    │    └─→ 6.2.1–6.2.3 (integration tests)
  │         │    └─→ 3.2.4–3.2.5 (audit + reporting)
  │         │         └─→ 5.1.1–5.1.2 (logging)
  │         │              └─→ 6.3.1 (smoke tests)
  └─→ 6.4.1 (API tests)
       └─→ 6.5.1–6.5.2 (deployment)
```

---

## Definition of Done

Every task must meet these criteria before marked "Done":

### Code Quality
- [ ] Code written in typed Python (type hints on all functions)
- [ ] Linting passes: `black`, `flake8`, `mypy --strict`
- [ ] No hardcoded values (use .env or constants file)
- [ ] Docstrings on all public functions/classes (Google style)

### Testing
- [ ] Unit tests written (if domain/logic function)
- [ ] Integration tests written (if service/repo)
- [ ] All tests pass locally: `pytest tests/ -v`
- [ ] Coverage report generated: `pytest tests/ --cov=src`
- [ ] Relevant tests added to CI/CD (if set up)

### Documentation
- [ ] Code comments for non-obvious logic (why, not what)
- [ ] Module README updated (if new module)
- [ ] Architecture doc updated (if structure changed)
- [ ] Task description updated in roadmap if scope changed

### Version Control
- [ ] Code committed to git: `git add . && git commit -m "feat(module): description"`
- [ ] Branch naming: `feature/task-name` or `fix/issue-name`
- [ ] No secrets committed (.env excluded via .gitignore)
- [ ] Rebase before merge (clean commit history)

### Performance & Logging
- [ ] Performance target met (or documented if not possible)
- [ ] Audit logging added (if state-changing operation)
- [ ] Error messages are user-friendly (logged, not exposed)
- [ ] No sensitive data logged (PIN, full payment details)

### Accessibility & UX
- [ ] Touch-friendly UI (56px+ buttons, if applicable)
- [ ] High contrast (WCAG AA, if UI task)
- [ ] Responsive layout (if Flet screen)
- [ ] Error states handled (loading, error messages)

---

## Timeline Estimate

| Epic | Stories | Tasks | Effort (Days) | Timeline |
|---|---|---|---|---|
| 1 (Setup) | 1 | 3 | 2–3 | Week 1 |
| 2 (DB) | 2 | 6 | 4–5 | Weeks 1–2 |
| 3 (Backend) | 4 | 15 | 12–15 | Weeks 2–4 |
| 4 (UI) | 5 | 12 | 10–12 | Weeks 3–5 |
| 5 (Logging) | 2 | 2 | 2–3 | Week 5 |
| 6 (Testing + Deploy) | 5 | 10 | 8–10 | Weeks 5–6 |
| **Total** | **19** | **48** | **38–48 days** | **8–10 weeks** |

**Assumptions**:
- 1 developer working full-time
- 8-hour workdays, 5 days/week
- Parallelizable tasks (e.g., multiple repos) can be combined

**Risks & Mitigations**:
- **Risk**: Flet learning curve → *Mitigation*: Prototype early (Task 4.1.1), allocate extra time
- **Risk**: FastAPI + SQLite async issues → *Mitigation*: Use sync SQLite, wrap in `asyncio.to_thread()`
- **Risk**: UI complexity (POS screen has many components) → *Mitigation*: Break into smaller screens, iterate

---

## How to Use This Roadmap

### For Sprint Planning
1. Select 1–2 epics per sprint (2-week sprint)
2. Assign stories to team members (parallel work)
3. Daily standups: report blockers, dependencies

### For Code Reviews
1. Verify task acceptance criteria met
2. Check Definition of Done items
3. Validate tests pass
4. Approve and merge to main

### For Progress Tracking
1. Update task status: Not Started → In Progress → Done
2. Note blockers in each task
3. Adjust timeline if risks materialize

### For Onboarding
- New team member: Start with Task 1.1.1–1.1.3 (setup)
- Then pick a small task from Epic 3 (e.g., 3.1.1)
- Pair with experienced dev on first integration test

---

**Status**: ✅ **Ready for Implementation** | **Last Updated**: 2026-02-09

