# Agent Architecture — Technical Documentation

**Project**: Hotel Management System (HMS)  
**Version**: 2.0 (Agent-Based Architecture)  
**Last Updated**: 2026-02-15

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [System Architecture Diagram](#2-system-architecture-diagram)
3. [Core Infrastructure](#3-core-infrastructure)
   - 3.1 Event Model
   - 3.2 EventBus
   - 3.3 EventStore
   - 3.4 Middleware Pipeline
   - 3.5 AgentRegistry
   - 3.6 Dead Letter Queue
4. [Agent Catalog](#4-agent-catalog)
   - 4.1 BaseAgent (Abstract)
   - 4.2 OrderAgent
   - 4.3 InventoryAgent
   - 4.4 PaymentAgent
   - 4.5 OrchestratorAgent
   - 4.6 InsightAgent
   - 4.7 AuditAgent
   - 4.8 AuthAgent
   - 4.9 PrintAgent
   - 4.10 NotificationAgent
   - 4.11 ReportingAgent
5. [LLM Integration](#5-llm-integration)
   - 5.1 LLMClient
   - 5.2 IntentParser (Two-Tier Parsing)
6. [Event Flow Diagrams](#6-event-flow-diagrams)
   - 6.1 Order Creation Workflow
   - 6.2 Order Finalization (Auto Re-dispatch Chain)
   - 6.3 Insight Query Flow
   - 6.4 Natural Language Command Flow
7. [Agent Subscription Map](#7-agent-subscription-map)
8. [Configuration](#8-configuration)
9. [Design Principles](#9-design-principles)
10. [File Structure](#10-file-structure)

---

## 1. Architecture Overview

The HMS uses an **in-process, event-driven agent architecture** built on top of existing domain services. This is a **Strangler Fig** migration: agents wrap services and communicate via events, but the existing service layer remains the source of truth for all business logic.

### Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **In-process EventBus** (not Kafka/RabbitMQ) | Offline-first hotel environment; no external broker dependency |
| **Rule-based transaction agents** | Core operations (orders, payments, inventory) must be deterministic |
| **LLM is advisory only** | InsightAgent is `degradable=True`; system works 100% without LLM |
| **Agents wrap services** | Agents delegate to `SalesService`, `InventoryService`, etc. — they never bypass the domain layer |
| **Append-only event log** | Every event is persisted to SQLite `event_log` table for auditing and replay |
| **Synchronous dispatch** | `publish_sync()` returns `EventResult` with the primary handler's response — essential for request-reply patterns (e.g., orchestrator workflows) |

### Technology Stack

- **Runtime**: Python 3.11+
- **Event Bus**: Custom in-process (`src/events/bus.py`)
- **Persistence**: SQLite (event_log table, append-only)
- **LLM Providers**: Groq, OpenAI, Ollama (all optional)
- **UI**: Flet 0.80.5 (desktop/web)
- **API**: FastAPI

---

## 2. System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              FLET UI LAYER                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │POS Screen│  │ Products │  │ Reports  │  │  Orders  │  │   Chat   │      │
│  │          │  │  Screen  │  │  Screen  │  │  History │  │  Screen  │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       └──────────────┴──────────────┴──────────────┴──────────────┘           │
│                              HTTP (httpx)                                     │
└──────────────────────────────────────────┬───────────────────────────────────┘
                                           │
┌──────────────────────────────────────────▼───────────────────────────────────┐
│                           FASTAPI REST API                                   │
│                                                                              │
│  /api/orders  /api/inventory  /api/insights  /api/voice/text-command        │
│  /api/agents/health  /api/agents/send  /api/agents/retry-dead-letters       │
└──────────────────────────────────────────┬───────────────────────────────────┘
                                           │
┌──────────────────────────────────────────▼───────────────────────────────────┐
│                         EVENT BUS + MIDDLEWARE                                │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                    MIDDLEWARE PIPELINE                                  │  │
│  │   TimingMiddleware ──► ErrorCatchMiddleware ──► Agent.handle()         │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────────┐                     │
│  │  EventBus   │──►│  EventStore  │──►│  event_log    │  (SQLite)           │
│  │             │   │  (append)    │   │  table        │                     │
│  └──────┬──────┘   └──────────────┘   └───────────────┘                     │
│         │                                                                    │
│  ┌──────▼──────┐   ┌──────────────┐                                         │
│  │  AgentReg   │   │ Dead Letter  │  (failed events with retry)             │
│  │  (registry) │   │ Queue        │                                         │
│  └─────────────┘   └──────────────┘                                         │
└──────────────────────────────────────────┬───────────────────────────────────┘
                                           │
┌──────────────────────────────────────────▼───────────────────────────────────┐
│                            AGENT LAYER                                       │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                    RULE-BASED AGENTS (deterministic)                 │     │
│  │                                                                     │     │
│  │  ┌────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │     │
│  │  │OrderAgent  │ │InventoryAgent│ │ PaymentAgent │ │  AuthAgent  │ │     │
│  │  │writes: yes │ │writes: yes   │ │writes: no    │ │writes: yes  │ │     │
│  │  │llm: no     │ │llm: no       │ │llm: no       │ │llm: no      │ │     │
│  │  └────────────┘ └──────────────┘ └──────────────┘ └─────────────┘ │     │
│  │                                                                     │     │
│  │  ┌────────────┐ ┌──────────────┐ ┌──────────────┐                  │     │
│  │  │ReportAgent │ │ PrintAgent   │ │  AuditAgent  │                  │     │
│  │  │writes: no  │ │writes: no    │ │writes: yes   │                  │     │
│  │  │llm: no     │ │degradable    │ │sub: wildcard │                  │     │
│  │  └────────────┘ └──────────────┘ └──────────────┘                  │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                   ORCHESTRATION + LLM AGENTS                        │     │
│  │                                                                     │     │
│  │  ┌────────────────────┐  ┌──────────────────┐  ┌──────────────┐   │     │
│  │  │ OrchestratorAgent  │  │  InsightAgent     │  │ Notification │   │     │
│  │  │ multi-step workflow│  │  LLM advisory     │  │ Agent        │   │     │
│  │  │ rollback on fail   │  │  degradable=True  │  │ (sink)       │   │     │
│  │  │ uses EventBus      │  │  rule fallback    │  │              │   │     │
│  │  └────────────────────┘  └──────────────────┘  └──────────────┘   │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────┬───────────────────────────────────┘
                                           │
┌──────────────────────────────────────────▼───────────────────────────────────┐
│                        APPLICATION SERVICES LAYER                            │
│                                                                              │
│  ┌────────────────┐ ┌──────────────────┐ ┌──────────────────────┐           │
│  │  SalesService  │ │ InventoryService │ │  ReportingService    │           │
│  │  (orders, tax) │ │ (stock, items)   │ │  (reports, exports)  │           │
│  └────────────────┘ └──────────────────┘ └──────────────────────┘           │
│  ┌────────────────┐                                                          │
│  │  AuthService   │                                                          │
│  │  (login, RBAC) │                                                          │
│  └────────────────┘                                                          │
└──────────────────────────────────────────┬───────────────────────────────────┘
                                           │
┌──────────────────────────────────────────▼───────────────────────────────────┐
│                        DOMAIN + INFRASTRUCTURE                               │
│                                                                              │
│  Entities: Order, LineItem, Item, User, AuditLogEntry, InventoryTransaction  │
│  Value Objects: Money, PaymentMethod, OrderStatus, UserRole                  │
│  Repositories: OrderRepository, ItemRepository, UserRepository, etc.         │
│  Database: SQLite (singleton connection, migrations)                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Infrastructure

### 3.1 Event Model

Every communication between agents goes through an **immutable Event** dataclass. Events are persisted to the `event_log` table for auditing and replay.

**File**: `src/events/event.py`

```python
@dataclass(frozen=True)
class Event:
    id: str                              # UUID v4
    type: str                            # Dot-notated: "domain.action" (e.g., "order.create")
    timestamp: str                       # ISO 8601 UTC
    source: str                          # Agent name or "API"
    correlation_id: str                  # Groups related events in a workflow
    payload: Dict[str, Any]              # Event-specific data
    user_id: Optional[str] = None        # Who triggered this
    metadata: Dict[str, Any] = {}        # Extra metadata
    reply_to: Optional[str] = None       # Event ID this is replying to
    parent_event_id: Optional[str] = None  # Causation chain
    target_agent: Optional[str] = None   # Direct addressing (None = broadcast)
```

**Key fields explained**:

| Field | Purpose |
|-------|---------|
| `correlation_id` | All events in a single workflow share the same correlation_id. Enables tracing "create order → add items → finalize → payment" as one logical unit. |
| `reply_to` | For request-reply: the response event sets `reply_to` to the request event's `id`. |
| `parent_event_id` | Causation tracking: "this payment.completed was caused by this order.finalized". |
| `target_agent` | Direct agent addressing. If set, EventBus routes ONLY to the named agent (bypasses broadcast). |

**EventResult** is the return value of `publish_sync()`:

```python
@dataclass
class EventResult:
    success: bool                          # Did at least one handler succeed?
    event: Optional[Event] = None          # Primary response (first non-None)
    error: Optional[str] = None            # Error message if all failed
    elapsed_ms: float = 0.0               # Processing time
    all_responses: list = field(default_factory=list)  # ALL handler responses
```

### 3.2 EventBus

The EventBus is the heart of the agent system. It routes events to subscribed handlers, runs middleware, and handles auto re-dispatch of downstream events.

**File**: `src/events/bus.py`

```
EventBus
├── subscribe(event_type, handler, name)    # Register handler
├── publish_sync(event) → EventResult       # Synchronous dispatch
├── publish(event) → None                   # Async fire-and-forget
├── publish_and_wait(event) → EventResult   # Async request-reply
├── add_middleware(mw)                       # Add to pipeline
├── set_registry(registry)                  # Connect AgentRegistry
├── retry_dead_letters() → dict             # Retry failed events
└── _get_handlers(event) → [handlers]       # Routing logic
```

**Subscription matching** supports three patterns:

```
Exact match:     "order.create"     → matches only "order.create"
Prefix wildcard: "order.*"          → matches "order.create", "order.finalize", etc.
Global wildcard: "*"                → matches ALL event types (used by AuditAgent)
```

**Handler routing with target_agent**:

```python
def _get_handlers(self, event: Event) -> List[Callable]:
    # If event targets a specific agent, route directly via registry
    if event.target_agent and self._registry:
        agent = self._registry.get_agent(event.target_agent)
        if agent and agent.can_handle(event_type):
            return [agent.handle]  # Only this agent handles it

    # Otherwise: exact match + prefix wildcard + global wildcard
    handlers = []
    if event_type in self._subscribers:          # Exact
        handlers.extend(...)
    if "order.*" in self._subscribers:           # Prefix wildcard
        handlers.extend(...)
    if "*" in self._subscribers:                 # Global wildcard (AuditAgent)
        handlers.extend(...)
    return handlers
```

**Auto re-dispatch**: When a handler returns a result event (e.g., `order.finalized`), the EventBus automatically re-dispatches it so that downstream agents (InventoryAgent, PaymentAgent) can react:

```python
AUTO_REDISPATCH_TYPES = {
    "order.finalized",      # → PaymentAgent, InventoryAgent
    "order.voided",         # → InventoryAgent
    "payment.completed",    # → (future consumers)
    "payment.failed",       # → (future consumers)
    "inventory.low_stock",  # → NotificationAgent
    "inventory.out_of_stock",  # → NotificationAgent
}
```

**Re-dispatch flow** (depth-limited to 3 to prevent infinite loops):

```
order.create (user)
  └─► OrderAgent → returns order.created
        (NOT re-dispatched — not in AUTO_REDISPATCH_TYPES)

order.finalize (user)
  └─► OrderAgent → returns order.finalized
        └─► AUTO RE-DISPATCH (depth=1):
              ├─► PaymentAgent → returns payment.completed
              │     └─► AUTO RE-DISPATCH (depth=2):
              │           └─► (no handlers for payment.completed)
              ├─► InventoryAgent → checks stock levels
              └─► AuditAgent → logs to audit_log
```

### 3.3 EventStore

**File**: `src/events/store.py`

Append-only persistence of all events to the SQLite `event_log` table.

```python
class EventStore:
    def append(self, event) -> None     # INSERT OR IGNORE into event_log
    def query(type, correlation_id, since, limit) -> [Event]
    def replay(correlation_id) -> [Event]  # Replay a full workflow
    def count(event_type) -> int
```

**SQLite schema** (`event_log` table):

```sql
CREATE TABLE event_log (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    source TEXT,
    correlation_id TEXT,
    user_id TEXT,
    payload TEXT,        -- JSON
    metadata TEXT,       -- JSON
    created_at TEXT
);
```

### 3.4 Middleware Pipeline

**File**: `src/events/middleware.py`

Middleware wraps every handler call. The pipeline is built as a chain:

```
TimingMiddleware → ErrorCatchMiddleware → Agent.handle()
```

| Middleware | Purpose |
|-----------|---------|
| `TimingMiddleware` | Logs handler execution time in milliseconds |
| `ErrorCatchMiddleware` | Catches exceptions and converts them to `{domain}.error` events instead of crashing the bus |
| `LoggingMiddleware` | Logs event type, source, correlation_id (used for debugging) |

**ErrorCatchMiddleware** is critical for resilience:

```python
class ErrorCatchMiddleware:
    def __call__(self, event, handler):
        try:
            return handler(event)
        except Exception as e:
            # Convert exception to an error event (doesn't crash the bus)
            return Event.create(
                type=f"{event.type.split('.')[0]}.error",  # e.g., "order.error"
                source="ErrorCatchMiddleware",
                payload={"original_type": event.type, "error": str(e)},
            )
```

**Middleware chain construction** (innermost = actual handler):

```python
def _run_middleware(self, event, handler):
    def build_chain(mw_list, final_handler):
        if not mw_list:
            return final_handler
        current_mw = mw_list[0]
        rest = build_chain(mw_list[1:], final_handler)
        return lambda evt: current_mw(evt, rest)

    chain = build_chain(self._middleware, handler)
    return chain(event)
```

### 3.5 AgentRegistry

**File**: `src/agents/registry.py`

Centralized registry of all agents. Supports name-based lookup for direct addressing.

```python
class AgentRegistry:
    def register(agent: BaseAgent) -> None     # Register by agent.name
    def get_agent(name: str) -> BaseAgent      # Lookup by name
    def get_subscribers(event_type) -> [Agent]  # All agents for an event type
    def list_agents() -> [Agent]                # All registered agents
```

**Registration at startup** (`src/api/app.py`):

```python
registry = AgentRegistry()
all_agents = [
    OrderAgent(), AuditAgent(), InventoryAgent(event_bus=event_bus),
    PaymentAgent(), AuthAgent(), PrintAgent(),
    NotificationAgent(), ReportingAgent(),
    InsightAgent(), OrchestratorAgent(event_bus=event_bus),
]
for agent in all_agents:
    registry.register(agent)
    for event_type in agent.subscribes_to:
        event_bus.subscribe(event_type, agent.handle, name=agent.name)

event_bus.set_registry(registry)
```

### 3.6 Dead Letter Queue

Failed events (handler exceptions that escape the ErrorCatchMiddleware) go to the dead letter queue with exponential backoff retry:

```python
class DeadLetterEntry:
    event: Event          # The failed event
    error: str            # Error message
    handler_name: str     # Which handler failed
    attempts: int         # Retry count
    max_retries: int = 3  # Maximum attempts

    def backoff_seconds(self) -> float:
        return 2 ** (self.attempts - 1)   # 1s, 2s, 4s
```

**API endpoints** for monitoring:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/agents/health` | GET | Agent status, subscription count, dead letter count |
| `/api/agents/retry-dead-letters` | POST | Trigger retry of dead letter queue |
| `/api/agents/send` | POST | Manually publish an event (debugging) |

---

## 4. Agent Catalog

### 4.1 BaseAgent (Abstract)

**File**: `src/agents/base.py`

Every agent inherits from `BaseAgent` and declares its contract:

```python
class BaseAgent(ABC):
    name: str = "BaseAgent"              # Unique identifier
    subscribes_to: List[str] = []        # Event types this agent handles
    publishes: List[str] = []            # Event types this agent may emit
    writes_to_db: bool = False           # Does it modify database state?
    uses_llm: bool = False               # Does it call an LLM?
    degradable: bool = False             # Can the system work without it?

    @abstractmethod
    def handle(self, event: Event) -> Optional[Event]:
        """Process event. Return response Event or None."""
        pass

    def can_handle(self, event_type: str) -> bool:
        """Check if this agent handles the event type (supports wildcards)."""
        ...
```

### 4.2 OrderAgent

**File**: `src/agents/order_agent.py`  
**Role**: Handles all order lifecycle events. Delegates to `SalesService`.

| Property | Value |
|----------|-------|
| Subscribes to | `order.create`, `order.add_item`, `order.remove_item`, `order.edit_qty`, `order.discount`, `order.finalize`, `order.void`, `order.hold`, `order.resume` |
| Publishes | `order.created`, `order.updated`, `order.finalized`, `order.voided`, `order.held`, `order.resumed`, `order.error` |
| Writes to DB | Yes (via SalesService) |
| Uses LLM | No |

**Internal routing**:

```python
def handle(self, event: Event) -> Optional[Event]:
    handlers = {
        "order.create":      self._handle_create,
        "order.add_item":    self._handle_add_item,
        "order.remove_item": self._handle_remove_item,
        "order.edit_qty":    self._handle_edit_qty,
        "order.discount":    self._handle_discount,
        "order.finalize":    self._handle_finalize,
        "order.void":        self._handle_void,
        "order.hold":        self._handle_hold,
        "order.resume":      self._handle_resume,
    }
    handler = handlers.get(event.type)
    if handler:
        try:
            return handler(event)
        except Exception as e:
            return Event.create(type="order.error", ...)
    return None
```

**Key handler example** — `_handle_create`:

```python
def _handle_create(self, event: Event) -> Event:
    table_id = event.payload.get("table_id", "1")
    user_id = event.user_id or event.payload.get("user_id", "")
    order = self.sales_service.create_order(
        table_id=table_id,
        created_by=UUID(user_id) if user_id else UUID(int=0),
    )
    return Event.create(
        type="order.created",
        source=self.name,
        correlation_id=event.correlation_id,
        payload=self._order_to_payload(order),
        user_id=event.user_id,
    )
```

### 4.3 InventoryAgent

**File**: `src/agents/inventory_agent.py`  
**Role**: Inventory operations AND reactive stock-level checking after order events.

| Property | Value |
|----------|-------|
| Subscribes to | `inventory.stock_in`, `inventory.adjust`, `inventory.archive`, `inventory.update`, `order.finalized`, `order.voided` |
| Publishes | `inventory.stocked_in`, `inventory.adjusted`, `inventory.archived`, `inventory.updated`, `inventory.low_stock`, `inventory.out_of_stock`, `inventory.error` |
| Writes to DB | Yes (via InventoryService) |
| Uses LLM | No |

**Unique characteristic**: InventoryAgent holds a reference to `EventBus` so it can **publish stock alerts** when levels drop below reorder thresholds:

```python
def _check_stock_alerts(self, item_id, correlation_id, user_id):
    stock = self.inventory_service.get_stock_on_hand(item_id)
    if stock <= 0:
        alert = Event.create(type="inventory.out_of_stock", ...)
        self._event_bus.publish_sync(alert)
    elif stock < item.reorder_level:
        alert = Event.create(type="inventory.low_stock", ...)
        self._event_bus.publish_sync(alert)
```

### 4.4 PaymentAgent

**File**: `src/agents/payment_agent.py`  
**Role**: Payment confirmation agent. Reacts to `order.finalized` (via auto re-dispatch) and explicit `payment.process` requests.

| Property | Value |
|----------|-------|
| Subscribes to | `payment.process`, `order.finalized` |
| Publishes | `payment.completed`, `payment.failed`, `payment.error` |
| Writes to DB | No (SalesService already recorded the payment) |

**Important**: PaymentAgent does NOT process payments — `SalesService.finalize_order()` does. PaymentAgent is a **confirmation/event-chaining agent** that emits `payment.completed` for downstream consumers (e.g., future loyalty programs, analytics).

### 4.5 OrchestratorAgent

**File**: `src/agents/orchestrator_agent.py`  
**Role**: Multi-step workflow orchestration with automatic rollback.

| Property | Value |
|----------|-------|
| Subscribes to | `workflow.multi_step` |
| Publishes | `workflow.completed`, `workflow.failed`, `workflow.step_completed` |
| Writes to DB | No (delegates to other agents) |
| Uses LLM | No |

**How it works**: The OrchestratorAgent decomposes a high-level intent into ordered sub-events and executes them sequentially via the EventBus:

```python
def _decompose_intent(self, intent):
    action = intent.get("action", "")
    steps = []

    if action == "create_order":
        # Step 1: Create the order
        steps.append({"type": "order.create", "payload": {"table_id": ...}})
        # Step 2+: Add each item
        for item in intent.get("items", []):
            steps.append({"type": "order.add_item", "payload": {"item_id": ..., "quantity": ...}})
        # Step 3 (optional): Finalize with payment
        if intent.get("payment_method"):
            steps.append({"type": "order.finalize", "payload": {"payment_method": ...}})
    ...
    return steps
```

**Rollback mechanism**: If any step fails, the orchestrator voids the order:

```python
def _execute_steps(self, steps, original_event):
    order_id = None
    for i, step in enumerate(steps):
        payload = dict(step["payload"])
        if order_id and "order_id" not in payload:
            payload["order_id"] = order_id  # Chain order_id forward

        sub_event = Event.create(type=step["type"], payload=payload, ...)
        result = self.event_bus.publish_sync(sub_event)

        if not result.success or result.event.type.endswith(".error"):
            # ROLLBACK: void the order if one was created
            if order_id:
                self.event_bus.publish_sync(
                    Event.create(type="order.void", payload={"order_id": order_id, "reason": "..."})
                )
            return Event.create(type="workflow.failed", ...)

        # Extract order_id from first step
        if step["type"] == "order.create":
            order_id = result.event.payload.get("order_id")

    return Event.create(type="workflow.completed", payload={"steps_completed": len(steps)})
```

### 4.6 InsightAgent

**File**: `src/agents/insight_agent.py`  
**Role**: LLM-powered advisory agent. Read-only. Degradable (system works without it).

| Property | Value |
|----------|-------|
| Subscribes to | `insight.suggest_upsell`, `insight.analyze_trends`, `insight.natural_query` |
| Publishes | `insight.suggestion`, `insight.analysis`, `insight.query_result`, `insight.error` |
| Writes to DB | No (read-only) |
| Uses LLM | Yes |
| Degradable | Yes |

**Two-tier response strategy**: LLM first, rule-based data summary fallback:

```python
def _handle_query(self, event):
    question = event.payload.get("question")

    # Gather real data context
    summary = self.reporting.daily_sales_summary(None)
    inventory = self.reporting.inventory_snapshot()
    transactions = self.reporting.search_transactions()

    # Try LLM
    result = self.llm.query(f"Question: {question}\nContext: {context}")
    if result is not None:
        return Event.create(type="insight.query_result",
                            payload={"answer": result, "source": "llm"})

    # Rule-based fallback (always returns something useful)
    answer = self._rule_based_answer(question, summary, inventory, transactions)
    return Event.create(type="insight.query_result",
                        payload={"answer": answer, "source": "rules"})
```

**Rule-based fallback** handles common question patterns:

| Question keywords | Response |
|-------------------|----------|
| "sales", "revenue", "total" | Today's sales total, order count, top items |
| "inventory", "stock", "low stock" | Total items, low stock count, low stock item names |
| "order", "recent", "last" | Transaction count, most recent receipt |
| (fallback) | Quick summary of sales + inventory |

### 4.7 AuditAgent

**File**: `src/agents/audit_agent.py`  
**Role**: Universal event sink. Subscribes to ALL events and logs them to the audit_log table.

| Property | Value |
|----------|-------|
| Subscribes to | `*` (all events) |
| Publishes | (none — terminal sink) |
| Writes to DB | Yes (append-only to audit_log) |

```python
class AuditAgent(BaseAgent):
    subscribes_to = ["*"]  # Global wildcard — receives EVERY event

    def handle(self, event):
        entry = AuditLogEntry(
            id=UUID(event.id),
            entity_type=event.type.split(".")[0].title(),
            operation=event.type,
            user_id=UUID(event.user_id) if event.user_id else UUID(int=0),
            new_state=json.dumps(event.payload),
        )
        self.audit_repo.create(entry)
        return None  # Terminal sink — no response
```

### 4.8 AuthAgent

**File**: `src/agents/auth_agent.py`  
**Role**: Authentication — login, logout, session validation.

| Property | Value |
|----------|-------|
| Subscribes to | `auth.login`, `auth.logout`, `auth.validate` |
| Publishes | `auth.logged_in`, `auth.logged_out`, `auth.validated`, `auth.error` |

### 4.9 PrintAgent

**File**: `src/agents/print_agent.py`  
**Role**: Receipt printing and emailing. Degradable — if printer is offline, orders still work.

| Property | Value |
|----------|-------|
| Subscribes to | `receipt.print`, `receipt.email`, `receipt.reprint` |
| Publishes | `receipt.printed`, `receipt.emailed`, `receipt.error` |
| Degradable | Yes |

### 4.10 NotificationAgent

**File**: `src/agents/notification_agent.py`  
**Role**: In-memory notification sink for UI polling. Stores last 100 notifications in a deque.

| Property | Value |
|----------|-------|
| Subscribes to | `notification.toast`, `notification.error`, `inventory.low_stock`, `inventory.out_of_stock` |
| Publishes | (none — terminal sink) |

```python
class NotificationAgent(BaseAgent):
    def __init__(self):
        self._store = deque(maxlen=100)  # Ring buffer

    def get_recent_notifications(self, limit=10):
        return list(self._store)[-limit:]
```

### 4.11 ReportingAgent

**File**: `src/agents/reporting_agent.py`  
**Role**: Report generation and CSV export. Delegates to `ReportingService`.

| Property | Value |
|----------|-------|
| Subscribes to | `report.daily_sales`, `report.inventory`, `report.transactions`, `report.export_csv` |
| Publishes | `report.generated`, `report.exported`, `report.error` |

---

## 5. LLM Integration

### 5.1 LLMClient

**File**: `src/agents/llm_client.py`

Configurable client supporting three providers:

| Provider | Base URL | Model Default | Auth |
|----------|----------|---------------|------|
| `ollama` | `http://localhost:11434` | `llama3.2` | None |
| `groq` | `https://api.groq.com/openai` | `llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| `openai` | `https://api.openai.com` | `gpt-4o-mini` | `LLM_API_KEY` |

```python
class LLMClient:
    def __init__(self, provider=None, model=None, timeout=8.0, api_key=None):
        self.provider = os.environ.get("LLM_PROVIDER", "ollama")
        self.model = os.environ.get("LLM_MODEL", DEFAULT_MODELS[self.provider])
        ...

    @property
    def is_available(self) -> bool:
        """Cloud providers need an API key; Ollama doesn't."""
        if self.provider in ("groq", "openai"):
            return bool(self.api_key)
        return True

    def query(self, prompt, system_prompt="") -> Optional[str]:
        """Returns None on timeout/error (graceful degradation)."""
        ...
```

### 5.2 IntentParser (Two-Tier Parsing)

**File**: `src/voice/intent_parser.py`

The IntentParser converts natural language into structured intent JSON. It uses a two-tier strategy:

```
User text ──► LLM Parser (if configured) ──► Structured Intent JSON
                    │ fails/unavailable
                    ▼
              Rule-based Parser ──► Structured Intent JSON
```

**LLM System Prompt** (abridged):

```
You are an intent parser for a hotel/restaurant management system.
Parse the user's command into a structured JSON intent.
Return ONLY valid JSON.

Available actions: create_order, add_item, finalize_order,
                   void_order, hold_order, create_product,
                   stock_in, report

Example:
Input: "order 3 biryani and 2 coke for table 5 pay cash"
Output: {"action": "create_order", "table_id": "5",
         "items": [{"name": "biryani", "quantity": 3}, ...],
         "payment_method": "CASH"}
```

**Item ID enrichment**: The LLM returns item names (not IDs). After parsing, `_enrich_item_ids()` matches names against the inventory database:

```python
def _enrich_item_ids(self, intent):
    """Fill in item_ids from inventory for items matched by name."""
    all_items = self.item_repo.list()
    name_to_id = {item.name.lower(): str(item.id) for item in all_items}

    for item in intent.get("items", []):
        if not item.get("item_id") or item["item_id"] == "":
            name_lower = item.get("name", "").lower()
            if name_lower in name_to_id:
                item["item_id"] = name_to_id[name_lower]
```

**Rule-based fallback** uses keyword priority:

```
Priority Order:
1. Specific compound phrases: void, hold, create-product, stock-in, report
2. Item-name matching: if text mentions known products → create_order
3. Finalize keywords (standalone): "pay cash", "finalize", "checkout"
4. Generic order keywords: "order", "want", "table"
5. Fallback finalize: standalone "bill", "payment"
6. Unknown
```

Every response includes a `_parsed_by` marker (`"llm"` or `"rules"`) so the UI can show `[AI]` or `[Data]` indicators.

---

## 6. Event Flow Diagrams

### 6.1 Order Creation Workflow (via Orchestrator)

```
User: "order 3 biryani for table 5 pay cash"
  │
  ▼
ChatScreen ──HTTP POST──► /api/voice/text-command
  │
  ▼
IntentParser.parse(text)
  ├── LLM: {"action": "create_order", "table_id": "5",
  │          "items": [{"name": "biryani", "quantity": 3}],
  │          "payment_method": "CASH"}
  │
  ├── _enrich_item_ids() → fills item_id from inventory DB
  │
  ▼
Event: workflow.multi_step
  │    payload: {"intent": {...}}
  │    source: "TextCommand"
  │
  ▼
EventBus.publish_sync()
  │
  ▼
OrchestratorAgent.handle()
  │
  ├── Step 0: order.create ──► OrderAgent ──► order.created (order_id=abc)
  │
  ├── Step 1: order.add_item ──► OrderAgent ──► order.updated
  │            payload: {order_id: "abc", item_id: "xyz", quantity: 3}
  │
  ├── Step 2: order.finalize ──► OrderAgent ──► order.finalized
  │            payload: {order_id: "abc", payment_method: "CASH"}
  │            │
  │            └── AUTO RE-DISPATCH: order.finalized
  │                  ├── PaymentAgent ──► payment.completed
  │                  ├── InventoryAgent ──► _check_stock_alerts()
  │                  └── AuditAgent ──► (logs to audit_log)
  │
  └── workflow.completed
        payload: {steps_completed: 3, order_id: "abc"}
  │
  ▼
Response: {"status": "success",
           "message": "Order created for table 5 with Biryani x3!"}
```

### 6.2 Order Finalization (Auto Re-dispatch Chain)

```
order.finalize (from API or Orchestrator)
  │
  ▼
OrderAgent._handle_finalize()
  │  Calls: SalesService.finalize_order()
  │  Returns: order.finalized event
  │
  ▼ (AUTO RE-DISPATCH by EventBus)
  │
  ├──► PaymentAgent._handle_order_finalized()
  │      Returns: payment.completed
  │        │
  │        ▼ (AUTO RE-DISPATCH depth=2)
  │        └── (no further handlers)
  │
  ├──► InventoryAgent._handle_order_finalized()
  │      Checks stock levels for each line item
  │      May publish: inventory.low_stock or inventory.out_of_stock
  │        │
  │        ▼ (if published)
  │        └──► NotificationAgent stores alert in deque
  │
  └──► AuditAgent.handle()
         Logs order.finalized to audit_log table
```

### 6.3 Insight Query Flow

```
User (Ask/Insights mode): "what are today's sales?"
  │
  ▼
ChatScreen ──HTTP POST──► /api/insights/query
  │                        {"question": "what are today's sales?"}
  │
  ▼
Event: insight.natural_query
  │    payload: {"question": "what are today's sales?"}
  │
  ▼
InsightAgent._handle_query()
  │
  ├── Gather context: daily_sales_summary(), inventory_snapshot(), search_transactions()
  │
  ├── Try LLM: self.llm.query(prompt_with_context, system_prompt)
  │     │
  │     ├── LLM available → return insight.query_result {answer: "...", source: "llm"}
  │     │
  │     └── LLM unavailable (returns None)
  │           │
  │           ▼
  │     Rule-based: _rule_based_answer()
  │       → "Today's sales: Rs.5,400.00 from 12 orders. Top items: Biryani (8), Coke (15)"
  │       → return insight.query_result {answer: "...", source: "rules"}
  │
  ▼
ChatScreen displays: "Today's sales: Rs.5,400.00... [Data]"
                                                      ^^^^^ source indicator
```

### 6.4 Natural Language Command Flow (Complete)

```
User input
  │
  ▼
IntentParser.parse(text)
  │
  ├── LLM available?
  │     ├── YES: _parse_with_llm(text)
  │     │        ├── Send to Groq/OpenAI with system prompt + menu catalog
  │     │        ├── Parse JSON response
  │     │        ├── _enrich_item_ids() (match names to inventory)
  │     │        └── Return intent with _parsed_by="llm"
  │     │
  │     └── NO: _parse_rule_based(text)
  │              ├── Check compound phrases (void, hold, product, stock, report)
  │              ├── Check item names in inventory
  │              ├── Keyword matching (finalize, order, etc.)
  │              └── Return intent with _parsed_by="rules"
  │
  ▼
Check missing required fields
  │
  ├── Fields missing → Return "followup" status with prompt
  │   (UI stores pending_intent, shows: "Which table number?")
  │   (Next user message merges via parse_followup())
  │
  └── All fields present → Execute command
        │
        ├── create_order → OrchestratorAgent (via EventBus)
        ├── finalize_order → SalesService directly
        ├── add_item → SalesService directly
        ├── void_order → SalesService directly
        ├── create_product → InventoryService directly
        ├── stock_in → InventoryService directly
        └── report → ReportingService directly
```

---

## 7. Agent Subscription Map

Complete mapping of which agent handles which event types:

```
EVENT TYPE              │ HANDLER AGENT(S)
────────────────────────┼──────────────────────────────────────
order.create            │ OrderAgent, AuditAgent(*)
order.add_item          │ OrderAgent, AuditAgent(*)
order.remove_item       │ OrderAgent, AuditAgent(*)
order.edit_qty          │ OrderAgent, AuditAgent(*)
order.discount          │ OrderAgent, AuditAgent(*)
order.finalize          │ OrderAgent, AuditAgent(*)
order.void              │ OrderAgent, AuditAgent(*)
order.hold              │ OrderAgent, AuditAgent(*)
order.resume            │ OrderAgent, AuditAgent(*)
order.finalized  (auto) │ PaymentAgent, InventoryAgent, AuditAgent(*)
order.voided     (auto) │ InventoryAgent, AuditAgent(*)
                        │
payment.process         │ PaymentAgent, AuditAgent(*)
payment.completed(auto) │ AuditAgent(*)
                        │
inventory.stock_in      │ InventoryAgent, AuditAgent(*)
inventory.adjust        │ InventoryAgent, AuditAgent(*)
inventory.archive       │ InventoryAgent, AuditAgent(*)
inventory.update        │ InventoryAgent, AuditAgent(*)
inventory.low_stock     │ NotificationAgent, AuditAgent(*)
inventory.out_of_stock  │ NotificationAgent, AuditAgent(*)
                        │
auth.login              │ AuthAgent, AuditAgent(*)
auth.logout             │ AuthAgent, AuditAgent(*)
auth.validate           │ AuthAgent, AuditAgent(*)
                        │
receipt.print           │ PrintAgent, AuditAgent(*)
receipt.email           │ PrintAgent, AuditAgent(*)
receipt.reprint         │ PrintAgent, AuditAgent(*)
                        │
report.daily_sales      │ ReportingAgent, AuditAgent(*)
report.inventory        │ ReportingAgent, AuditAgent(*)
report.transactions     │ ReportingAgent, AuditAgent(*)
report.export_csv       │ ReportingAgent, AuditAgent(*)
                        │
insight.suggest_upsell  │ InsightAgent, AuditAgent(*)
insight.analyze_trends  │ InsightAgent, AuditAgent(*)
insight.natural_query   │ InsightAgent, AuditAgent(*)
                        │
notification.toast      │ NotificationAgent, AuditAgent(*)
notification.error      │ NotificationAgent, AuditAgent(*)
                        │
workflow.multi_step     │ OrchestratorAgent, AuditAgent(*)
────────────────────────┴──────────────────────────────────────
(*) AuditAgent subscribes to wildcard "*" — receives ALL events
(auto) = auto re-dispatched by EventBus
```

---

## 8. Configuration

### Environment Variables

```env
# LLM Provider (optional — system works 100% without it)
LLM_PROVIDER=groq                        # groq | openai | ollama
LLM_MODEL=llama-3.3-70b-versatile        # Provider-specific model
LLM_TIMEOUT=8                             # Seconds (prevents blocking)

# API Keys (provider-specific)
GROQ_API_KEY=gsk_...                      # For Groq
LLM_API_KEY=sk-...                        # For OpenAI
# Ollama needs no API key

# Base URLs (defaults set per provider)
LLM_BASE_URL=https://api.groq.com/openai  # Override if needed
```

### Startup Sequence

```
1. Database migrations run automatically
2. EventStore created (SQLite event_log table)
3. EventBus created with EventStore
4. Middleware pipeline wired: TimingMiddleware → ErrorCatchMiddleware
5. AgentRegistry created
6. All 10 agents instantiated
7. Agents registered with AgentRegistry
8. Agent handlers subscribed to EventBus
9. Registry connected to EventBus (for direct addressing)
10. FastAPI app starts accepting requests
```

---

## 9. Design Principles

### Constitution Rules

| Rule | Enforcement |
|------|-------------|
| **Rule-based transaction path** | Only rule-based agents (OrderAgent, InventoryAgent, etc.) write to DB |
| **LLM never blocks core flow** | InsightAgent has `degradable=True`, 8s timeout, read-only |
| **Offline-first** | In-process EventBus, local SQLite, no external broker |
| **Data correctness** | Agents delegate to validated SalesService/InventoryService (domain layer) |
| **Auditability** | AuditAgent subscribes to ALL events (wildcard `*`); EventStore persists every event |
| **Structured logging** | Event middleware logs every dispatch with timing |
| **Graceful degradation** | ErrorCatchMiddleware converts exceptions to error events; dead letter queue retries |

### Strangler Fig Pattern

Agents don't replace existing services — they wrap them:

```
BEFORE (direct):   API → SalesService → Database
AFTER  (agent):    API → EventBus → OrderAgent → SalesService → Database
```

The existing service layer is untouched. Agents add event-driven communication, audit logging, and cross-cutting concerns on top.

---

## 10. File Structure

```
src/
├── agents/                          # Agent implementations
│   ├── __init__.py                  # Package exports
│   ├── base.py                      # BaseAgent abstract class
│   ├── registry.py                  # AgentRegistry
│   ├── llm_client.py                # LLMClient (Groq/OpenAI/Ollama)
│   ├── order_agent.py               # OrderAgent
│   ├── inventory_agent.py           # InventoryAgent
│   ├── payment_agent.py             # PaymentAgent
│   ├── orchestrator_agent.py        # OrchestratorAgent
│   ├── insight_agent.py             # InsightAgent
│   ├── audit_agent.py               # AuditAgent
│   ├── auth_agent.py                # AuthAgent
│   ├── print_agent.py               # PrintAgent
│   ├── notification_agent.py        # NotificationAgent
│   └── reporting_agent.py           # ReportingAgent
│
├── events/                          # Event infrastructure
│   ├── __init__.py
│   ├── event.py                     # Event + EventResult dataclasses
│   ├── bus.py                       # EventBus + DeadLetterQueue
│   ├── store.py                     # EventStore (SQLite persistence)
│   └── middleware.py                # Timing, ErrorCatch, Logging middleware
│
├── voice/                           # Natural language processing
│   ├── intent_parser.py             # IntentParser (LLM + rule-based)
│   ├── stt.py                       # Speech-to-Text (Whisper)
│   └── tts.py                       # Text-to-Speech (pyttsx3)
│
├── api/
│   └── app.py                       # FastAPI app (agent wiring at startup)
│
├── application/                     # Application services
│   └── services.py                  # SalesService, InventoryService, etc.
│
├── domain/                          # Domain entities + value objects
├── infrastructure/                  # Repositories, database, printer
└── ui/                              # Flet UI screens
```
