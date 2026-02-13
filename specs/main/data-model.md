# Data Model: Agent-Based Architecture

**Date**: 2026-02-13 | **Status**: Complete

---

## 1. Core Event Model

### Event (Immutable)

```python
@dataclass(frozen=True)
class Event:
    id: str                        # UUID4 string
    type: str                      # Dot-notated: "domain.action" (e.g., "order.create")
    timestamp: str                 # ISO 8601 UTC (e.g., "2026-02-13T10:30:00Z")
    source: str                    # Agent name (e.g., "OrderAgent")
    correlation_id: str            # Groups related events in a workflow
    user_id: Optional[str]         # User who triggered (None for system events)
    payload: dict                  # Event-specific data (JSON-serializable)
    metadata: dict                 # Optional context (session_token, device_id, etc.)
```

### EventResult (Response wrapper)

```python
@dataclass
class EventResult:
    success: bool
    event: Optional[Event]         # Response event (if publish_and_wait)
    error: Optional[str]           # Error message (if failed)
    elapsed_ms: float              # Processing time
```

---

## 2. Agent Model

### BaseAgent (Abstract)

```python
class BaseAgent(ABC):
    name: str                      # Unique agent identifier
    subscribes_to: List[str]       # Event types this agent handles
    publishes: List[str]           # Event types this agent may emit
    writes_to_db: bool             # Whether agent can modify database
    uses_llm: bool                 # Whether agent uses LLM reasoning
    
    @abstractmethod
    async def handle(self, event: Event) -> Optional[Event]:
        """Process an event. Return response event or None."""
    
    async def publish(self, event: Event) -> None:
        """Publish event to the bus."""
    
    def validate_event(self, event: Event) -> bool:
        """Validate event payload against expected schema."""
```

### AgentRegistry

```python
class AgentRegistry:
    agents: Dict[str, BaseAgent]   # name -> agent instance
    subscriptions: Dict[str, List[BaseAgent]]  # event_type -> subscribers
    
    def register(self, agent: BaseAgent) -> None
    def get_subscribers(self, event_type: str) -> List[BaseAgent]
    def get_agent(self, name: str) -> Optional[BaseAgent]
```

---

## 3. EventBus Model

### EventBus

```python
class EventBus:
    registry: AgentRegistry
    store: EventStore              # Persistence layer
    middleware: List[Middleware]    # Pre/post processing hooks
    dead_letter: List[Event]       # Failed events for inspection
    
    async def publish(self, event: Event) -> None:
        """Fire-and-forget: dispatch to all subscribers."""
    
    async def publish_and_wait(self, event: Event, timeout: float = 5.0) -> EventResult:
        """Request-reply: dispatch and wait for response event."""
    
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Register a handler for an event type."""
```

### EventStore (Persistence)

```python
class EventStore:
    """Append-only event log backed by SQLite."""
    
    def append(self, event: Event) -> None:
        """Persist event to event_log table."""
    
    def query(self, event_type: str = None, 
              correlation_id: str = None,
              since: str = None, limit: int = 100) -> List[Event]:
        """Query stored events."""
    
    def replay(self, correlation_id: str) -> List[Event]:
        """Replay all events for a workflow (debugging)."""
```

---

## 4. Event Payload Schemas

### Order Events

```python
# order.create
{"table_id": "5", "user_id": "uuid-..."}

# order.created (response)
{"order_id": "uuid-...", "table_id": "5", "status": "draft", "created_at": "2026-..."}

# order.add_item
{"order_id": "uuid-...", "item_id": "uuid-...", "quantity": 2}

# order.updated (response)
{
    "order_id": "uuid-...",
    "subtotal": 600.0,
    "discount_amount": 0.0,
    "tax_amount": 108.0,
    "total_amount": 708.0,
    "line_items": [
        {"id": "uuid-...", "item_name": "Biryani", "quantity": 2, "total_amount": 600.0}
    ]
}

# order.finalize
{"order_id": "uuid-...", "payment_method": "CASH", "amount_tendered": 800.0}

# order.finalized (response)
{
    "order_id": "uuid-...",
    "receipt_number": "REC-2026-0213-000001",
    "total_amount": 708.0,
    "payment_method": "CASH",
    "change_due": 92.0
}

# order.void
{"order_id": "uuid-...", "reason": "Customer changed mind", "approved_by": "uuid-..."}

# order.error
{"order_id": "uuid-...", "error_code": "INSUFFICIENT_STOCK", "message": "Only 5 Biryani in stock"}
```

### Inventory Events

```python
# inventory.stock_in
{"item_id": "uuid-...", "quantity": 50, "reference": "PO-2026-001"}

# inventory.updated
{"item_id": "uuid-...", "item_name": "Biryani", "new_stock": 95, "operation": "stock_in"}

# inventory.low_stock
{"item_id": "uuid-...", "item_name": "Coke", "current_stock": 8, "reorder_level": 50}

# inventory.out_of_stock
{"item_id": "uuid-...", "item_name": "Lassi"}
```

### Payment Events

```python
# payment.process
{"order_id": "uuid-...", "method": "CASH", "amount": 708.0, "tendered": 800.0}

# payment.completed
{"payment_id": "uuid-...", "order_id": "uuid-...", "method": "CASH", "amount": 708.0, "change": 92.0}

# payment.failed
{"order_id": "uuid-...", "reason": "Card declined"}
```

### Auth Events

```python
# auth.login
{"username": "cashier", "pin": "1234"}

# auth.logged_in
{"user_id": "uuid-...", "username": "cashier", "role": "CASHIER", "session_token": "uuid-..."}

# auth.session_expired
{"user_id": "uuid-...", "expired_at": "2026-02-13T11:00:00Z"}
```

### Insight Events (LLM)

```python
# insight.suggest_upsell
{"order_id": "uuid-...", "current_items": ["Biryani", "Coke"]}

# insight.suggestion (response)
{
    "order_id": "uuid-...",
    "suggestions": [
        {"item": "Raita", "reason": "Popular pairing with Biryani", "confidence": 0.85},
        {"item": "Gulab Jamun", "reason": "Dessert completes the meal", "confidence": 0.72}
    ],
    "model": "llama3:8b",
    "inference_ms": 450
}
```

---

## 5. Database Changes

### New Table: event_log

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | TEXT | PRIMARY KEY | UUID4 |
| type | TEXT | NOT NULL, INDEXED | Event type (e.g., "order.create") |
| source | TEXT | NOT NULL | Publishing agent name |
| correlation_id | TEXT | INDEXED | Groups related events |
| user_id | TEXT | NULLABLE | Triggering user |
| payload | TEXT | NOT NULL | JSON payload |
| metadata | TEXT | NULLABLE | JSON metadata |
| created_at | TEXT | NOT NULL, INDEXED | ISO 8601 UTC |

### Existing Tables: UNCHANGED

All 13 existing tables remain exactly as-is. The event_log is additive.

---

## 6. Relationships

```
                    ┌──────────────┐
                    │   EventBus    │
                    └──────┬───────┘
                           │ dispatches to
          ┌────────────────┼────────────────────┐
          │                │                    │
    ┌─────┴─────┐   ┌─────┴──────┐   ┌────────┴───────┐
    │ OrderAgent │   │InventoryAgent│  │  AuditAgent    │
    │            │   │             │   │  (subscribes   │
    │ wraps:     │   │ wraps:      │   │   to ALL)      │
    │ SalesService│   │ InventoryService│  │               │
    └─────┬─────┘   └─────┬──────┘   └────────┬───────┘
          │                │                    │
          │         delegates to                │
          │                │                    │
    ┌─────┴────────────────┴──────┐    ┌───────┴──────┐
    │     Application Services     │    │  EventStore   │
    │  (SalesService, InventoryService)│    │  (event_log)  │
    └─────────────┬────────────────┘    └──────────────┘
                  │
           uses repositories
                  │
    ┌─────────────┴────────────────┐
    │      Infrastructure          │
    │  (Repositories, Database)    │
    └──────────────────────────────┘
```
