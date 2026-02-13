# Implementation Plan: Agent-Based Architecture Upgrade

**Branch**: `main` | **Date**: 2026-02-13 | **Spec**: User-defined upgrade request
**Input**: Existing HMS v2.0 (70/70 tasks complete) → Agent-based event-driven architecture

## Summary

Upgrade the monolithic HMS service layer into a multi-agent, event-driven architecture with:
- **Central Event Bus** for decoupled communication between agents
- **Rule-based agents** for all critical operations (POS, inventory, reporting, auth)
- **LLM Insight Agent** only for non-critical reasoning (upsell suggestions, anomaly detection, natural language queries)
- **Zero degradation** to runtime performance; offline-first preserved; existing UI unchanged

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, Flet 0.80.x, SQLite, bcrypt, httpx (existing) + new: `asyncio` (event bus), no external message brokers
**Storage**: SQLite (local, WAL mode) — unchanged
**Testing**: pytest (73 tests existing) + new agent/event contract tests
**Target Platform**: Windows 10+ desktop (primary), Docker (secondary)
**Project Type**: Single-device desktop application with embedded backend
**Performance Goals**: <100ms per event cycle, <500ms order finalization, 1000+ txn/day
**Constraints**: Offline-first (no network for core ops), <200MB memory, existing UI untouched
**Scale/Scope**: Single device, ~30 concurrent orders, 10 agents

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| 1.1 Offline-First | PASS | Event bus is in-process (no network), SQLite unchanged |
| 1.2 Data Correctness | PASS | Rule agents validate before commit; LLM never writes to DB |
| 1.3 Auditability | PASS | All events logged to event_log table; agent actions audited |
| 1.4 Safety (Destructive) | PASS | Confirmation agents gate destructive operations |
| 1.5 Security | PASS | Auth agent validates sessions; LLM has read-only access |
| Performance | PASS | In-process bus (<1ms dispatch); no network hops; async I/O |

---

## 1. Agent Inventory & Responsibilities

### 1.1 Agent Registry

| # | Agent Name | Type | Responsibility | Writes to DB? | LLM? |
|---|-----------|------|---------------|--------------|------|
| 1 | **OrderAgent** | Rule-based | Create, modify, hold, resume, finalize, void orders | YES | NO |
| 2 | **InventoryAgent** | Rule-based | Stock-in, stock-out, deductions, alerts, archive | YES | NO |
| 3 | **PaymentAgent** | Rule-based | Process payments, validate amounts, record receipts | YES | NO |
| 4 | **AuthAgent** | Rule-based | Login, logout, session validation, user CRUD | YES | NO |
| 5 | **ReportingAgent** | Rule-based | Generate sales/inventory summaries, CSV exports | READ-ONLY | NO |
| 6 | **AuditAgent** | Rule-based | Log all state changes, immutable event recording | APPEND-ONLY | NO |
| 7 | **PrintAgent** | Rule-based | ESC/POS printing, email receipts, file output | FILE I/O | NO |
| 8 | **NotificationAgent** | Rule-based | Toast messages, error banners, alerts to UI | NO (UI only) | NO |
| 9 | **InsightAgent** | LLM-powered | Upsell suggestions, anomaly detection, NL queries | READ-ONLY | YES |
| 10 | **OrchestratorAgent** | Hybrid | Routes complex multi-step workflows, resolves ambiguity | NO | Optional |

### 1.2 Agent Design Principles

```
┌─────────────────────────────────────────────────────┐
│                  CRITICAL RULE                        │
│                                                       │
│  LLM agents NEVER write to the database.             │
│  Only rule-based agents commit state changes.         │
│  LLM output is always validated by a rule agent       │
│  before any side effect occurs.                       │
│                                                       │
│  Rule agents are deterministic and testable.          │
│  LLM agents are advisory and degradable.              │
│  System works 100% without LLM agents running.        │
└─────────────────────────────────────────────────────┘
```

### 1.3 Agent Detail Cards

#### OrderAgent
- **Subscribes to**: `order.create`, `order.add_item`, `order.remove_item`, `order.edit_qty`, `order.discount`, `order.finalize`, `order.void`, `order.hold`, `order.resume`
- **Publishes**: `order.created`, `order.updated`, `order.finalized`, `order.voided`, `order.held`, `order.resumed`, `order.error`
- **Wraps**: Current `SalesService` methods
- **Validation**: Stock check before add_item, permission check before void/discount

#### InventoryAgent
- **Subscribes to**: `inventory.stock_in`, `inventory.adjust`, `inventory.deduct`, `inventory.archive`, `order.finalized` (for auto-deduction)
- **Publishes**: `inventory.updated`, `inventory.low_stock`, `inventory.out_of_stock`, `inventory.error`
- **Wraps**: Current `InventoryService` methods
- **Side effect on `order.finalized`**: Deducts stock for all line items

#### PaymentAgent
- **Subscribes to**: `payment.process`
- **Publishes**: `payment.completed`, `payment.failed`
- **Wraps**: Current payment logic in `SalesService.finalize_order`

#### AuthAgent
- **Subscribes to**: `auth.login`, `auth.logout`, `auth.validate`, `auth.user_create`, `auth.user_update`
- **Publishes**: `auth.logged_in`, `auth.logged_out`, `auth.session_expired`, `auth.error`
- **Wraps**: Current `AuthService`

#### ReportingAgent
- **Subscribes to**: `report.daily_sales`, `report.inventory`, `report.transactions`, `report.export_csv`
- **Publishes**: `report.generated`, `report.exported`
- **Read-only**: Never modifies data

#### AuditAgent
- **Subscribes to**: ALL events (wildcard `*`)
- **Publishes**: None (terminal sink)
- **Append-only**: Writes to `event_log` and `audit_log` tables

#### PrintAgent
- **Subscribes to**: `receipt.print`, `receipt.email`, `receipt.reprint`
- **Publishes**: `receipt.printed`, `receipt.emailed`, `receipt.error`

#### NotificationAgent
- **Subscribes to**: `notification.toast`, `notification.error`, `notification.banner`, `inventory.low_stock`
- **Publishes**: None (UI side effect only)
- **Delivers**: Flet SnackBar/Banner updates to the page

#### InsightAgent (LLM)
- **Subscribes to**: `insight.suggest_upsell`, `insight.analyze_trends`, `insight.natural_query`
- **Publishes**: `insight.suggestion`, `insight.analysis`, `insight.query_result`
- **READ-ONLY**: Can query DB but never write
- **Degradable**: System works without this agent; timeout after 5s → skip
- **LLM**: Local Ollama/llama.cpp or OpenAI API (configurable)

#### OrchestratorAgent
- **Subscribes to**: `workflow.multi_step`
- **Publishes**: Individual step events (e.g., `order.create` → `order.add_item` → `order.finalize`)
- **Purpose**: Coordinate complex multi-event workflows (e.g., "Quick order table 5: 2 biryani, 1 coke, pay cash")

---

## 2. Events & Message Schema

### 2.1 Base Event Schema

```python
@dataclass(frozen=True)
class Event:
    """Immutable event — the fundamental unit of communication."""
    id: str                    # UUID
    type: str                  # e.g., "order.create"
    timestamp: str             # ISO 8601 UTC
    source: str                # Agent name that published
    correlation_id: str        # Links related events (same workflow)
    user_id: Optional[str]     # Who triggered it
    payload: dict              # Event-specific data
    metadata: dict             # Optional context (session, device, etc.)
```

### 2.2 Event Catalog

#### Order Events

| Event Type | Payload | Published By | Consumed By |
|-----------|---------|-------------|-------------|
| `order.create` | `{table_id, user_id}` | UI/API | OrderAgent |
| `order.created` | `{order_id, table_id, status}` | OrderAgent | AuditAgent, NotificationAgent |
| `order.add_item` | `{order_id, item_id, quantity}` | UI/API | OrderAgent |
| `order.remove_item` | `{order_id, line_item_id}` | UI/API | OrderAgent |
| `order.edit_qty` | `{order_id, line_item_id, new_qty}` | UI/API | OrderAgent |
| `order.updated` | `{order_id, subtotal, tax, total, line_items}` | OrderAgent | AuditAgent, UI |
| `order.discount` | `{order_id, discount_type, discount_value}` | UI/API | OrderAgent |
| `order.finalize` | `{order_id, payment_method, amount_tendered}` | UI/API | OrderAgent |
| `order.finalized` | `{order_id, receipt_number, total, payment}` | OrderAgent | PaymentAgent, InventoryAgent, PrintAgent, AuditAgent |
| `order.void` | `{order_id, reason, approved_by}` | UI/API | OrderAgent |
| `order.voided` | `{order_id, reason}` | OrderAgent | InventoryAgent (reverse stock), AuditAgent |
| `order.hold` | `{order_id}` | UI/API | OrderAgent |
| `order.held` | `{order_id}` | OrderAgent | AuditAgent |
| `order.resume` | `{order_id}` | UI/API | OrderAgent |
| `order.resumed` | `{order_id}` | OrderAgent | AuditAgent |
| `order.error` | `{order_id, error, message}` | OrderAgent | NotificationAgent |

#### Inventory Events

| Event Type | Payload | Published By | Consumed By |
|-----------|---------|-------------|-------------|
| `inventory.stock_in` | `{item_id, quantity, reference}` | UI/API | InventoryAgent |
| `inventory.updated` | `{item_id, new_stock, operation}` | InventoryAgent | AuditAgent, UI |
| `inventory.low_stock` | `{item_id, item_name, current_stock, reorder_level}` | InventoryAgent | NotificationAgent, InsightAgent |
| `inventory.out_of_stock` | `{item_id, item_name}` | InventoryAgent | NotificationAgent |

#### Payment Events

| Event Type | Payload | Published By | Consumed By |
|-----------|---------|-------------|-------------|
| `payment.process` | `{order_id, method, amount}` | OrderAgent | PaymentAgent |
| `payment.completed` | `{payment_id, order_id, method, amount}` | PaymentAgent | AuditAgent |
| `payment.failed` | `{order_id, reason}` | PaymentAgent | NotificationAgent |

#### Auth Events

| Event Type | Payload | Published By | Consumed By |
|-----------|---------|-------------|-------------|
| `auth.login` | `{username, pin}` | UI | AuthAgent |
| `auth.logged_in` | `{user_id, username, role, session_token}` | AuthAgent | AuditAgent |
| `auth.logout` | `{session_token}` | UI | AuthAgent |
| `auth.session_expired` | `{user_id, session_id}` | AuthAgent | NotificationAgent |

#### Receipt Events

| Event Type | Payload | Published By | Consumed By |
|-----------|---------|-------------|-------------|
| `receipt.print` | `{order_data}` | UI | PrintAgent |
| `receipt.email` | `{order_data, to_email}` | UI | PrintAgent |
| `receipt.printed` | `{filepath}` | PrintAgent | NotificationAgent |
| `receipt.emailed` | `{to_email}` | PrintAgent | NotificationAgent |

#### Insight Events (LLM — advisory only)

| Event Type | Payload | Published By | Consumed By |
|-----------|---------|-------------|-------------|
| `insight.suggest_upsell` | `{order_id, items}` | OrchestratorAgent | InsightAgent |
| `insight.suggestion` | `{order_id, suggestions: [...]}` | InsightAgent | UI (optional) |
| `insight.analyze_trends` | `{date_range}` | UI | InsightAgent |
| `insight.analysis` | `{summary, trends, anomalies}` | InsightAgent | UI |

---

## 3. Folder & File Structure

```text
src/
├── __init__.py
├── __main__.py                          # FastAPI entry point (UNCHANGED)
├── launcher.py                          # Unified launcher (UNCHANGED)
│
├── domain/                              # Pure business rules (UNCHANGED)
│   ├── __init__.py
│   ├── entities.py                      # Order, Item, User, etc.
│   ├── value_objects.py                 # Money, enums
│   └── business_rules.py               # Tax, discount, stock validation
│
├── agents/                              # NEW — Agent implementations
│   ├── __init__.py                      # Agent registry & factory
│   ├── base.py                          # BaseAgent abstract class
│   ├── order_agent.py                   # OrderAgent (wraps SalesService)
│   ├── inventory_agent.py              # InventoryAgent (wraps InventoryService)
│   ├── payment_agent.py                # PaymentAgent (payment processing)
│   ├── auth_agent.py                   # AuthAgent (wraps AuthService)
│   ├── reporting_agent.py             # ReportingAgent (read-only)
│   ├── audit_agent.py                 # AuditAgent (event sink)
│   ├── print_agent.py                 # PrintAgent (receipts)
│   ├── notification_agent.py          # NotificationAgent (UI feedback)
│   ├── insight_agent.py               # InsightAgent (LLM-powered, read-only)
│   └── orchestrator_agent.py          # OrchestratorAgent (workflow coordinator)
│
├── events/                              # NEW — Event bus infrastructure
│   ├── __init__.py                      # Exports EventBus, Event
│   ├── bus.py                           # Central EventBus (in-process, async)
│   ├── event.py                         # Event dataclass + serialization
│   ├── store.py                         # EventStore (SQLite event_log table)
│   └── middleware.py                    # Logging, timing, error-handling middleware
│
├── application/                         # Service layer (PRESERVED as agent internals)
│   ├── __init__.py
│   └── services.py                      # SalesService, InventoryService, etc.
│                                        # (agents delegate to these)
│
├── infrastructure/                      # Data access (UNCHANGED)
│   ├── __init__.py
│   ├── database.py
│   ├── repositories.py
│   ├── printer.py
│   ├── email_sender.py
│   └── logging_handler.py
│
├── api/                                 # FastAPI routes (THIN ADAPTER)
│   ├── __init__.py
│   └── app.py                           # Routes publish events instead of calling services directly
│
└── ui/                                  # Flet UI (UNCHANGED screens)
    ├── __init__.py
    ├── app.py                           # Main app (UNCHANGED)
    ├── i18n.py                          # Translations (UNCHANGED)
    ├── components/
    │   ├── __init__.py
    │   └── ui_helpers.py
    └── screens/                         # All screens UNCHANGED
        ├── auth_screen.py
        ├── pos_screen.py
        ├── products_screen.py
        ├── reports_screen.py
        ├── receipt_screen.py
        ├── order_history_screen.py
        └── user_mgmt_screen.py

migrations/
├── 001_init_schema.sql                  # UNCHANGED
├── 002_add_is_active.sql                # UNCHANGED
├── 003_add_event_log.sql                # NEW — event_log table
└── runner.py                            # UNCHANGED

tests/
├── unit/
│   ├── test_business_rules.py           # UNCHANGED
│   └── test_events.py                   # NEW — Event serialization tests
├── integration/
│   ├── test_phase_1_flows.py            # UNCHANGED
│   └── test_agent_flows.py              # NEW — Agent integration tests
├── contract/                            # NEW
│   ├── test_event_contracts.py          # Event schema validation
│   └── test_agent_contracts.py          # Agent subscribe/publish contracts
├── performance/
│   └── test_benchmarks.py              # UPDATED — add event bus benchmarks
└── smoke/
    └── test_offline_workflows.py        # UNCHANGED
```

---

## 4. Sequence Diagrams

### 4.1 Order Creation Flow

```
User (UI)          API Layer         EventBus        OrderAgent       AuditAgent    Notification
   │                  │                 │                │                │              │
   │ POST /orders     │                 │                │                │              │
   │─────────────────>│                 │                │                │              │
   │                  │ publish          │                │                │              │
   │                  │ order.create     │                │                │              │
   │                  │────────────────>│                │                │              │
   │                  │                 │  dispatch       │                │              │
   │                  │                 │───────────────>│                │              │
   │                  │                 │                │ SalesService   │              │
   │                  │                 │                │ .create_order()│              │
   │                  │                 │                │───────┐        │              │
   │                  │                 │                │<──────┘        │              │
   │                  │                 │                │                │              │
   │                  │                 │  order.created  │                │              │
   │                  │                 │<───────────────│                │              │
   │                  │                 │                                 │              │
   │                  │                 │──────────────────────────────>│              │
   │                  │                 │  (audit log)                   │              │
   │                  │                 │──────────────────────────────────────────────>│
   │                  │  response       │  (toast: "Order created")                     │
   │<─────────────────│                 │                                               │
```

### 4.2 Add Item to Order Flow

```
User (UI)       API          EventBus      OrderAgent     InventoryAgent   AuditAgent
   │              │              │              │                │              │
   │ POST item    │              │              │                │              │
   │─────────────>│              │              │                │              │
   │              │ order.add_item│             │                │              │
   │              │─────────────>│              │                │              │
   │              │              │─────────────>│                │              │
   │              │              │              │ check stock    │              │
   │              │              │              │───────────────>│              │
   │              │              │              │<───────────────│              │
   │              │              │              │                │              │
   │              │              │              │ SalesService   │              │
   │              │              │              │ .add_item()    │              │
   │              │              │              │                │              │
   │              │              │ order.updated│                │              │
   │              │              │<─────────────│                │              │
   │              │              │──────────────────────────────────────────────>│
   │<─────────────│              │                                              │
```

### 4.3 Order Finalization Flow (Multi-Agent)

```
User        API        EventBus    OrderAgent   PaymentAgent  InventoryAgent  PrintAgent  AuditAgent
  │          │            │            │              │              │             │           │
  │ finalize │            │            │              │              │             │           │
  │─────────>│            │            │              │              │             │           │
  │          │ order      │            │              │              │             │           │
  │          │ .finalize  │            │              │              │             │           │
  │          │───────────>│            │              │              │             │           │
  │          │            │───────────>│              │              │             │           │
  │          │            │            │              │              │             │           │
  │          │            │            │ validate     │              │             │           │
  │          │            │            │ order ok     │              │             │           │
  │          │            │            │              │              │             │           │
  │          │            │  order.finalized          │              │             │           │
  │          │            │<───────────│              │              │             │           │
  │          │            │            │              │              │             │           │
  │          │            │ ──────────────────────────> payment.process            │           │
  │          │            │            │              │              │             │           │
  │          │            │            │              │ record payment│            │           │
  │          │            │            │              │──────┐       │             │           │
  │          │            │            │              │<─────┘       │             │           │
  │          │            │  payment.completed        │              │             │           │
  │          │            │<──────────────────────────│              │             │           │
  │          │            │            │              │              │             │           │
  │          │            │ ──────────────────────────────────────> deduct stock   │           │
  │          │            │            │              │              │──────┐      │           │
  │          │            │            │              │              │<─────┘      │           │
  │          │            │  inventory.updated        │              │             │           │
  │          │            │<────────────────────────────────────────│             │           │
  │          │            │            │              │              │             │           │
  │          │            │ ──────────────────────────────────────────────────> receipt.print │
  │          │            │            │              │              │             │──────┐    │
  │          │            │            │              │              │             │<─────┘    │
  │          │            │            │              │              │             │           │
  │          │            │ ALL events ──────────────────────────────────────────────────────>│
  │          │            │                                                         (logged)  │
  │<─────────│            │                                                                   │
```

### 4.4 Insight (LLM) Flow — Advisory Only

```
User        API        EventBus     InsightAgent(LLM)    OrderAgent
  │          │            │              │                    │
  │ "suggest │            │              │                    │
  │  upsell" │            │              │                    │
  │─────────>│            │              │                    │
  │          │ insight    │              │                    │
  │          │ .suggest   │              │                    │
  │          │───────────>│              │                    │
  │          │            │─────────────>│                    │
  │          │            │              │ READ-ONLY          │
  │          │            │              │ query: recent      │
  │          │            │              │ orders, popular    │
  │          │            │              │ items              │
  │          │            │              │                    │
  │          │            │              │ LLM reasoning      │
  │          │            │              │ (local/API)        │
  │          │            │              │                    │
  │          │            │  insight     │                    │
  │          │            │  .suggestion │                    │
  │          │            │<─────────────│                    │
  │          │            │              │                    │
  │          │  response  │   (displayed as optional UI      │
  │<─────────│            │    suggestion — user can ignore)  │
  │          │            │                                   │
  │          │            │  NOTE: No DB write occurred.      │
  │          │            │  User must explicitly act on      │
  │          │            │  suggestion via normal order flow.│
```

---

## 5. Changes to Current Modules

### 5.1 Change Impact Matrix

| Module | Change Level | Description |
|--------|-------------|-------------|
| `src/domain/` | NONE | Pure business rules — completely untouched |
| `src/infrastructure/` | MINIMAL | Add `event_log` table support; repos unchanged |
| `src/application/services.py` | PRESERVED | Services stay as-is; agents wrap/delegate to them |
| `src/api/app.py` | MODERATE | Routes publish events instead of calling services directly |
| `src/ui/` | NONE | All screens unchanged; UI calls same API endpoints |
| `src/agents/` | NEW | All new agent classes |
| `src/events/` | NEW | Event bus, event store, middleware |
| `migrations/` | MINIMAL | Add `003_add_event_log.sql` |
| `tests/` | ADDITIVE | New test files; existing tests unchanged |

### 5.2 Detailed Changes

#### `src/api/app.py` — Route Adapter Pattern

**Before** (current):
```python
@app.post("/api/sales/orders")
async def create_order(request: CreateOrderRequest):
    svc = SalesService()
    order = svc.create_order(table_id=request.table_id, created_by=UUID(request.user_id))
    return _order_to_response(order)
```

**After** (agent-based):
```python
@app.post("/api/sales/orders")
async def create_order(request: CreateOrderRequest):
    event = Event(
        type="order.create",
        payload={"table_id": request.table_id, "user_id": request.user_id},
    )
    result = await bus.publish_and_wait(event, timeout=5.0)
    return result.payload
```

The API layer becomes a thin adapter: it converts HTTP requests to events, publishes them, and returns the result. This is the ONLY file that changes significantly.

#### `migrations/003_add_event_log.sql` — New Table

```sql
CREATE TABLE IF NOT EXISTS event_log (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    source TEXT NOT NULL,
    correlation_id TEXT,
    user_id TEXT,
    payload TEXT NOT NULL,          -- JSON
    metadata TEXT,                   -- JSON
    created_at TEXT NOT NULL,
    INDEX idx_event_type (type),
    INDEX idx_event_correlation (correlation_id),
    INDEX idx_event_created (created_at)
);
```

### 5.3 Migration Strategy

```
Phase A: Add event infrastructure (bus, store, base agent)
Phase B: Create agents that WRAP existing services (no behavior change)
Phase C: Update API routes to publish events (one route at a time)
Phase D: Add InsightAgent (LLM, optional, degradable)
Phase E: Add OrchestratorAgent for multi-step workflows
```

Each phase is independently deployable. At every step, the system works identically to today. This is a strangler-fig migration — new code wraps old code, never replaces it all at once.

---

## 6. Test Coverage Strategy

### 6.1 Test Pyramid

```
         ┌─────────┐
         │  E2E /  │   5 tests  — Full workflow (UI → API → Agent → DB)
         │  Smoke  │
        ┌┴─────────┴┐
        │ Integration│  20 tests — Agent → Service → Repository chains
        │            │
       ┌┴────────────┴┐
       │   Contract    │  15 tests — Event schema validation, agent pub/sub
       │               │
      ┌┴───────────────┴┐
      │     Unit         │  40 tests — Agent logic, event bus, serialization
      │                  │
      └──────────────────┘
```

### 6.2 Test Categories

#### Unit Tests (40+ new)
- **Event serialization**: Event → JSON → Event roundtrip
- **EventBus dispatch**: Subscribe, publish, wildcard matching
- **Agent handlers**: Each agent's `handle()` with mock services
- **Event validation**: Reject malformed events, missing fields

#### Contract Tests (15 new)
- **Event schema**: Every event type matches its schema definition
- **Agent contracts**: Each agent subscribes to exactly its declared events
- **Agent publish**: Each agent publishes only its declared output events
- **No DB writes from InsightAgent**: Verify LLM agent is truly read-only

#### Integration Tests (20 new)
- **Order lifecycle via events**: create → add_item → finalize → payment + stock deduction
- **Multi-agent cascade**: order.finalized triggers PaymentAgent + InventoryAgent + PrintAgent
- **Error propagation**: order.add_item with insufficient stock → order.error → notification
- **Session expiry flow**: auth.validate → auth.session_expired → notification
- **Audit completeness**: Every state change produces audit event

#### Performance Tests (5 new)
- **Event bus throughput**: 10,000 events/sec (in-process target)
- **Order finalization via events**: <500ms end-to-end
- **No regression**: Existing benchmark results unchanged
- **LLM timeout**: InsightAgent degrades gracefully at 5s timeout
- **Memory**: <200MB with 100 queued events

#### Smoke Tests (existing + 5 new)
- **Offline with agents**: All critical flows work without network
- **LLM unavailable**: System operates normally when InsightAgent fails
- **Event store persistence**: Events survive restart

### 6.3 Test Execution Strategy

```bash
# All tests (fast, no LLM)
pytest tests/ -m "not llm"

# With LLM tests (requires Ollama or API key)
pytest tests/ -m "llm"

# Contract tests only
pytest tests/contract/

# Performance benchmarks
pytest tests/performance/ -v --durations=0
```

---

## Project Structure Summary

### Documentation (this feature)

```text
specs/main/
├── plan.md              # This file (agent architecture plan)
├── research.md          # Phase 0: Technology decisions
├── data-model.md        # Phase 1: Event & agent data models
├── contracts/           # Phase 1: Event schema contracts (JSON)
│   ├── order-events.json
│   ├── inventory-events.json
│   ├── payment-events.json
│   ├── auth-events.json
│   └── insight-events.json
├── tasks.md             # Implementation task breakdown
└── checklists/          # Completion tracking
```

**Structure Decision**: Additive architecture — new `src/agents/` and `src/events/` directories alongside existing code. No existing file deleted. Services preserved as agent internals.

## Complexity Tracking

| Decision | Why Needed | Simpler Alternative Rejected Because |
|----------|-----------|-------------------------------------|
| In-process event bus (not Redis/Kafka) | Offline-first; no external deps | External broker adds network dep + complexity |
| 10 agents (not fewer) | Clean separation of concerns | Combining agents violates single-responsibility |
| LLM read-only enforcement | Constitution: data correctness | Allowing LLM writes risks non-deterministic state |
| Strangler-fig migration | Zero downtime, incremental | Big-bang rewrite risks breaking 70 working features |

---

**Next Steps**: Run `/speckit.tasks` to break this plan into implementable tasks.
