# Hotel Management System (HMS) - Phase 1 MVP

**Offline-first, voice-enabled sales, inventory, and reporting system for hotels and restaurants.**

![Status](https://img.shields.io/badge/Status-Phase%201%20MVP-blue)
![Version](https://img.shields.io/badge/Version-0.1.0-green)

---

## 📌 Overview

HMS is a lightweight, deterministic point-of-sale (POS) and inventory management system designed for small-to-medium hospitality businesses. It works seamlessly offline with local SQLite storage, requires minimal staff training, and provides complete audit trails for compliance.

### Key Features (Phase 1)
- ✅ **Offline-First**: Works without internet; sync later (Phase 2+)
- ✅ **Fast POS**: Create & finalize orders in seconds
- ✅ **Inventory Tracking**: Append-only ledger prevents data loss
- ✅ **User Roles**: Waiter, Cashier, Manager, Clerk, Admin
- ✅ **Audit Logs**: Every transaction immutably recorded
- ✅ **Daily Reports**: Sales summary & inventory snapshot
- ✅ **Touch-Friendly UI**: Built with Flet, optimized for tablets

### Non-Features (Phase 1)
- ❌ Cloud sync (Phase 2+)
- ❌ Voice/AI assistant (Phase 2+)
- ❌ Multi-branch management (Phase 3+)
- ❌ Advanced analytics (Phase 3+)

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+** (3.11+ recommended)
- **Windows 10+**, macOS, or Linux
- **2GB RAM**, **500MB disk space**

### Installation & Setup

#### 1. Clone Repository
```bash
git clone <repository_url>
cd Hotel_management_agent
```

#### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
# Core dependencies
pip install -r requirements.txt

# Development dependencies (optional)
pip install -r requirements-dev.txt
```

#### 4. Configure Environment
```bash
# Copy example config
cp .env.example .env

# Edit .env if needed (defaults work for Phase 1)
# DATABASE_URL=sqlite:///./hms.db
# LOG_LEVEL=INFO
# API_PORT=8000
```

#### 5. Initialize Database
```bash
python -m migrations.runner apply
```

#### 6. Run Application
```bash
# Option A: Start API server only (for testing)
python -m src

# Option B: Run specific parts
# python -c "from src.infrastructure import Database; Database()"  # Test DB
# pytest tests/ -v --cov=src  # Run tests
```

The API server starts on: **http://127.0.0.1:8000**

API documentation available at: **http://127.0.0.1:8000/docs** (Swagger UI)

---

## 📁 Project Structure

```
src/
├── domain/              # Pure business logic (no dependencies)
│   ├── value_objects.py   # Money, OrderStatus, enums
│   ├── entities.py        # Order, User, Item, etc.
│   └── business_rules.py  # calculate_tax(), validate_stock(), etc.
├── application/         # Services and orchestration
│   └── services.py        # SalesService, InventoryService, AuthService
├── infrastructure/      # Database, repositories, I/O
│   ├── database.py        # SQLite connection & init
│   ├── repositories.py    # OrderRepository, ItemRepository, etc.
│   └── logging_handler.py # Structured logging
├── api/                 # FastAPI endpoints
│   └── app.py           # REST API (FastAPI app)
└── ui/                  # Flet UI (Phase 1 stub)
    └── screens/         # Login, POS, Products, Reports screens

tests/
├── unit/                # Domain & business logic tests
├── integration/         # Service & repository tests
└── smoke/              # End-to-end offline tests

migrations/
└── 001_init_schema.sql  # SQLite schema
```

---

## 🔧 Development

### Code Quality

Run linting and formatting:
```bash
# Format code
black src/ tests/

# Check types
mypy src/ --strict

# Lint
flake8 src/ tests/

# All-in-one (if Makefile available)
make lint
```

### Testing

Run test suite:
```bash
# All tests
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=src

# Specific test file
pytest tests/unit/test_business_rules.py -v

# Run only unit tests
pytest tests/unit/ -v
```

### Architecture Principles

This codebase strictly follows the **HMS Constitution**:

1. **Offline-First**: All critical workflows operate without internet
2. **Deterministic**: Business logic is pure, testable, and reproducible
3. **Auditability**: Every state change is logged immutably
4. **Correctness > Reliability > Usability > Performance > Features**

Read [constitution.md](constitution.md) for complete principles.

---

## 📝 API Endpoints (Phase 1)

### Health Check
```bash
GET /health
```

### Authentication
```bash
POST /api/auth/login
  { "username": "john", "pin": "1234" }

POST /api/auth/logout

GET /api/auth/me
```

### Sales/Orders
```bash
POST /api/sales/orders
  { "table_id": "1" }

POST /api/sales/orders/{order_id}/items
  { "item_id": "...", "quantity": 2 }

POST /api/sales/orders/{order_id}/finalize
  { "payment_method": "CASH", "paid_amount": 500.00 }

GET /api/sales/orders/{order_id}
```

### Inventory
```bash
GET /api/inventory/items

GET /api/inventory/items/{item_id}
```

### Reports
```bash
GET /api/reports/daily-sales?date=2026-02-09

GET /api/reports/inventory-snapshot
```

---

## 🗄️ Database

### SQLite Schema (Phase 1)

Core tables:
- `users` - Staff members with roles
- `orders` - Bills/invoices (immutable, finalized only)
- `order_line_items` - Items in each order
- `items` - Menu/products
- `payments` - Payment records
- `stock_ledger` - Append-only inventory log
- `audit_log` - Immutable audit trail
- `system_log` - Queryable application logs

All monetary values stored as **INTEGER cents** (no floats):
- ₹100.50 = 10050 cents
- ₹1.00 = 100 cents

All timestamps in **UTC** (ISO 8601):
- Example: `2026-02-09T14:30:00Z`

---

## 🔐 Security (Phase 1)

- **Authentication**: PIN + username (4-6 digits, bcrypt hashed)
- **Authorization**: Role-based access control (WAITER, CASHIER, MANAGER, CLERK, ADMIN)
- **Audit**: Every action logged with user, timestamp, before/after state
- **Data**: Sensitive fields never logged (PIN, full payment details)

**Not included in Phase 1:**
- HTTPS (add in Phase 2+)
- 2FA (nice-to-have Phase 2+)
- Session expiration (add Phase 2+)

---

## 📊 Logging

Logs written to both **SQLite database** and **rotating files**:

```
logs/
├── hms-2026-02-09.log  # JSON lines, one per line
├── hms-2026-02-10.log
└── ...
```

Query logs from database:
```sql
SELECT * FROM system_log
WHERE category = 'sales.billing' AND DATE(timestamp) = DATE('now')
ORDER BY timestamp DESC;
```

---

## 🐛 Troubleshooting

### Database Locked Error
```bash
# SQLite is logging to database. Wait or:
# Close all connections and restart
rm *.db-shm *.db-wal
python -m src
```

### Port 8000 Already in Use
```bash
# Change port in .env
API_PORT=8001
python -m src
```

### Missing Migrations
```bash
# Re-run migrations
python -m migrations.runner apply
python -m migrations.runner status
```

### Tests Failing
```bash
# Ensure database is clean
python -m pytest tests/ --tb=short -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html  # View coverage
```

---

## 📚 Documentation

- **[constitution.md](constitution.md)** - Non-negotiable principles
- **[specification.md](specification.md)** - Full feature specification
- **[PHASE_1_ROADMAP.md](PHASE_1_ROADMAP.md)** - Detailed implementation roadmap
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture (TBD)
- **[TESTING.md](TESTING.md)** - Test strategies and setup (in progress)

---

## 🚧 Roadmap

### Phase 1 (Current) - MVP
- ✅ Core POS & Inventory
- ✅ User roles & audit
- ✅ Offline operation
- 🏗️ Flet UI (partially stubbed)
- 🏗️ Logging infrastructure

### Phase 2 - EnhancementS
- Voice/STT assistant
- Stock-in workflow
- Purchase orders
- Sync infrastructure
- Advanced discounts

### Phase 3 - Scale
- Multi-branch sync
- Finance/GL module
- Loyalty program
- Mobile app
- Cloud dashboards

---

## 👥 Support & Contribution

**Questions?** Create an issue on GitHub.

**Want to contribute?** Follow the [constitution.md](constitution.md) principles:
1. Deterministic business logic only
2. Pure functions in domain layer
3. Audit every state change
4. ≥80% test coverage
5. Meaningful commit messages

---

## 📄 License

[TBD - Add appropriate license]

---

## ✨ Acknowledgments

Built on principles of:
- Domain-Driven Design (DDD)
- Clean Architecture
- Offline-first software
- Deterministic systems

---

**Status**: Phase 1 MVP (Foundation) | **Last Updated**: 2026-02-10
