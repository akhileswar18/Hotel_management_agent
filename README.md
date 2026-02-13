# Hotel Management System (HMS) - Complete v3.0

**Offline-first, voice-enabled sales, inventory, and reporting system for hotels and restaurants.**

![Status](https://img.shields.io/badge/Status-Complete%20v3.0-brightgreen)
![Version](https://img.shields.io/badge/Version-3.0.0-green)

---

## 📌 Overview

HMS is a lightweight, deterministic point-of-sale (POS) and inventory management system designed for small-to-medium hospitality businesses. It works seamlessly offline with local SQLite storage, requires minimal staff training, and provides complete audit trails for compliance.

### Features (All Phases Complete)

**Agent-Based Architecture**
- Event-driven EventBus with persisted event log
- 11 agents: OrderAgent, AuditAgent, InventoryAgent, PaymentAgent, AuthAgent, PrintAgent, NotificationAgent, ReportingAgent, InsightAgent, OrchestratorAgent
- AgentRegistry subscription model; events published from API/services, agents react asynchronously
- Full system works without voice or LLM (optional enhancements)

**Voice/Chat Interface**
- Voice input (Whisper STT) and text chat via WebSocket
- OrchestratorAgent parses intent and calls tools (create order, add item, query stock, etc.)
- Optional TTS (pyttsx3) for spoken responses
- Chat screen in Flet UI for assistant-style interaction

**LLM-Powered Insights**
- InsightAgent for upsell suggestions, trends, and natural-language queries
- Configurable LLM (Ollama local or OpenAI cloud); degradable when unavailable
- Optional; core POS and reporting work without LLM

**Core POS**
- Offline-first order creation and management
- Add items, edit quantities, remove line items
- Hold and resume orders
- Apply discounts (percentage or absolute, up to 50%)
- Finalize with Cash, Card, or Voucher
- Void orders with reason and audit trail
- Stock validation prevents overselling
- Keyboard shortcuts (F2 New Order, F5 Finalize, F8 Hold, F9 Resume)

**Inventory Management**
- Product catalog with categories
- Record stock-in with references
- Append-only stock ledger (audit-safe)
- Low-stock alerts and reorder levels
- Edit product details (price, reorder level)
- Archive/soft-delete products
- Category filtering

**Reporting & Analytics**
- Daily sales summary with revenue, transaction count, avg order value
- Payment method breakdown
- Top-selling items
- Inventory snapshot with low-stock count
- Date range filtering
- Transaction search by date and payment method
- CSV export for sales and inventory

**Authentication & Security**
- PIN-based login (bcrypt-hashed)
- Role-based access: Waiter, Cashier, Manager, Clerk, Admin
- Server-side sessions with 30-minute auto-expiry
- User management (create, edit roles, reset PINs) for managers
- Rate limiting (100 req/min per IP)
- Security headers (X-Frame-Options, XSS protection)
- Input length validation

**Receipt & Printing**
- ESC/POS thermal printer integration
- Text file receipt backup (receipts/ folder)
- Email receipts via SMTP (HTML + plain text)
- Reprint from order history
- Digital receipt URL with copy-to-clipboard

**UI & Accessibility**
- Touch-friendly interface (Flet, runs in browser)
- Dark mode toggle
- WCAG AAA color contrast
- Toast notifications (non-blocking)
- Global error banner
- Navigation rail with role-based visibility

**Data & DevOps**
- SQLite database with WAL mode
- Database backup/restore with CLI
- DB vacuum for space reclamation
- PyInstaller standalone executable
- Docker containerization
- GitHub Actions CI/CD
- i18n framework (English + Hindi)
- Performance benchmarks (1000+ txn/day)

**Audit & Compliance**
- Immutable audit log for every state change
- Structured logging to DB + rotating files
- Append-only stock ledger
- Complete order lifecycle tracking

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

# Edit .env if needed (defaults work out of the box)
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
# Option A: Unified Launcher (Recommended)
python -m src.launcher
# Opens API on port 8000 and UI on port 8080 automatically.

# Option B: Start API server only (for testing)
python -m src

# Option C: Run specific parts
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
│   ├── repositories.py   # OrderRepository, ItemRepository, etc.
│   └── logging_handler.py # Structured logging
├── events/              # EventBus and event persistence
│   ├── event.py           # Event model
│   ├── store.py           # EventStore (event_log table)
│   ├── bus.py             # EventBus pub/sub
│   └── middleware.py     # Publish events from API
├── agents/               # Event-driven agents
│   ├── base.py            # BaseAgent
│   ├── registry.py        # AgentRegistry
│   ├── order_agent.py     # Order lifecycle
│   ├── audit_agent.py     # Audit logging
│   ├── inventory_agent.py # Low/out-of-stock
│   ├── payment_agent.py   # Payment events
│   ├── auth_agent.py      # Auth events
│   ├── print_agent.py     # Receipt printing
│   ├── notification_agent.py
│   ├── reporting_agent.py
│   ├── insight_agent.py   # LLM upsell/trends/query
│   ├── orchestrator_agent.py # Voice/chat orchestration
│   └── llm_client.py      # LLM client (Ollama/OpenAI)
├── voice/                # Voice pipeline (optional)
│   ├── stt.py             # Whisper STT
│   ├── tts.py             # pyttsx3 TTS
│   └── intent_parser.py   # Intent parsing
├── api/                  # FastAPI endpoints
│   └── app.py            # REST API + WebSocket
└── ui/                   # Flet UI (browser/touch-friendly)
    └── screens/          # Login, POS, Products, Reports, Chat screens

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

## 📝 API Endpoints

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

### SQLite Schema

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

## 🔐 Security

- **Authentication**: PIN + username (4-6 digits, bcrypt hashed)
- **Authorization**: Role-based access control (WAITER, CASHIER, MANAGER, CLERK, ADMIN)
- **Audit**: Every action logged with user, timestamp, before/after state
- **Data**: Sensitive fields never logged (PIN, full payment details)
- **Sessions**: 30-minute auto-expiry server-side

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

All 10 phases complete; v3.0 adds agent-based architecture, voice/chat, and LLM insights. Future enhancements may include:
- Multi-branch sync
- Finance/GL module
- Loyalty program
- Mobile app

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

**Status**: Complete v3.0 (Agent-Based Architecture) | **Last Updated**: 2026-02-12
