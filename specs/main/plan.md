# Hotel Management System — Implementation Plan

**Feature**: HMS MVP (Phase 1 Complete → Phase 2 In Progress)
**Updated**: 2026-02-11

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **UI** | Flet (Python) | 0.21+ |
| **API** | FastAPI + Uvicorn | 0.104+ |
| **Database** | SQLite (local-first) | Bundled |
| **Auth** | bcrypt PIN hashing | — |
| **Testing** | Pytest | 7.4+ |
| **Language** | Python | 3.11+ |

## Architecture

```
src/
├── domain/           # Pure business logic (no DB/UI deps)
│   ├── value_objects.py   # Money, OrderStatus, Role, TransactionType, PaymentMethod
│   ├── entities.py        # Order, OrderLineItem, Item, Payment, User, StockLedgerEntry, VoidRecord, AuditLogEntry
│   └── business_rules.py  # calculate_tax, apply_discount, validate_stock_deduction, compute_stock_on_hand, validate_permission
│
├── application/      # Service orchestration
│   └── services.py        # AuthService, SalesService, InventoryService, ReportingService
│
├── infrastructure/   # DB, I/O, external
│   ├── database.py        # Database singleton, init_db
│   ├── repositories.py    # OrderRepo, ItemRepo, UserRepo, StockLedgerRepo, AuditLogRepo, PaymentRepo, VoidRecordRepo
│   └── logging_handler.py # Structured logging to DB + file
│
├── api/              # FastAPI REST endpoints
│   └── app.py             # All routes: auth, sales, inventory, reports
│
└── ui/               # Flet desktop UI
    ├── app.py              # Main app, navigation, FastAPI startup
    ├── screens/
    │   ├── auth_screen.py      # PIN login
    │   ├── pos_screen.py       # Order entry, discount, finalize, void
    │   ├── products_screen.py  # Product CRUD, stock-in
    │   ├── reports_screen.py   # Daily sales, inventory snapshot
    │   └── receipt_screen.py   # Receipt display
    └── components/
        └── ui_helpers.py       # HMSButton, ItemPickerWidget, OrderSummaryWidget
```

## Key Design Decisions

1. **Offline-First**: All operations use local SQLite; no network required
2. **Money as Cents**: All monetary values stored as INTEGER (cents) to avoid float errors
3. **Append-Only Ledger**: Stock computed by summing ledger entries (never direct updates)
4. **Immutable Audit Log**: Every state change recorded, never deleted
5. **Frozen Dataclasses**: Domain entities are immutable (frozen=True)
6. **Single-File Services**: All services in one `services.py` for Phase 1 simplicity

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/login | Username + PIN login |
| POST | /api/auth/logout | End session |
| GET | /api/auth/me | Current user info |
| POST | /api/sales/orders | Create draft order |
| POST | /api/sales/orders/{id}/items | Add item to order |
| PATCH | /api/sales/orders/{id}/discount | Apply discount |
| POST | /api/sales/orders/{id}/finalize | Finalize + payment |
| POST | /api/sales/orders/{id}/void | Void order |
| GET | /api/sales/orders/{id} | Get order details |
| GET | /api/inventory/items | List items + stock |
| GET | /api/inventory/items/{id} | Item details |
| POST | /api/inventory/items | Create new item |
| POST | /api/inventory/stock-in | Record stock arrival |
| POST | /api/inventory/adjustments | Stock adjustment |
| GET | /api/reports/daily-sales | Daily sales summary |
| GET | /api/reports/inventory-snapshot | Inventory snapshot |

## Database Schema (13 tables)

users, sessions, items, tables_seating, orders, order_line_items, payments, stock_ledger, void_records, audit_log, system_log
