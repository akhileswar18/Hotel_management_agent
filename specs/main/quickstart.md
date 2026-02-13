# Quickstart: Agent-Based Architecture

**Date**: 2026-02-13

---

## Integration Scenario: Order Creation via Event Bus

### Step 1: API receives HTTP request

```python
# src/api/app.py
@app.post("/api/sales/orders")
async def create_order(request: CreateOrderRequest):
    event = Event.create(
        type="order.create",
        payload={"table_id": request.table_id, "user_id": request.user_id},
        user_id=request.user_id,
    )
    result = await bus.publish_and_wait(event, timeout=5.0)
    if result.success:
        return result.event.payload
    raise HTTPException(status_code=400, detail=result.error)
```

### Step 2: EventBus dispatches to OrderAgent

```python
# src/events/bus.py
class EventBus:
    async def publish_and_wait(self, event: Event, timeout: float) -> EventResult:
        # 1. Store event (append to event_log)
        self.store.append(event)
        
        # 2. Find subscribers for "order.create"
        subscribers = self.registry.get_subscribers(event.type)
        
        # 3. Dispatch to each subscriber
        for agent in subscribers:
            result = await asyncio.wait_for(agent.handle(event), timeout)
            if result:
                self.store.append(result)  # Store response event too
                return EventResult(success=True, event=result)
        
        return EventResult(success=False, error="No handler responded")
```

### Step 3: OrderAgent processes the event

```python
# src/agents/order_agent.py
class OrderAgent(BaseAgent):
    name = "OrderAgent"
    subscribes_to = ["order.create", "order.add_item", "order.finalize", ...]
    
    async def handle(self, event: Event) -> Optional[Event]:
        if event.type == "order.create":
            return await self._create_order(event)
    
    async def _create_order(self, event: Event) -> Event:
        # Delegates to existing SalesService (UNCHANGED business logic)
        order = self.sales_service.create_order(
            table_id=event.payload["table_id"],
            created_by=UUID(event.payload["user_id"]),
        )
        
        # Return response event
        return Event.create(
            type="order.created",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={
                "order_id": str(order.id),
                "table_id": order.table_id,
                "status": order.status.value,
            },
        )
```

### Step 4: AuditAgent logs the event (fire-and-forget)

```python
# src/agents/audit_agent.py
class AuditAgent(BaseAgent):
    name = "AuditAgent"
    subscribes_to = ["*"]  # Subscribes to ALL events
    
    async def handle(self, event: Event) -> None:
        # Append to event_log (already done by bus)
        # Also write structured audit entry
        self.audit_repo.create(AuditLogEntry(
            entity_type=event.type.split(".")[0].title(),
            entity_id=event.payload.get("order_id", ""),
            operation=event.type,
            new_state=json.dumps(event.payload),
            performed_by=UUID(event.user_id) if event.user_id else None,
        ))
        return None  # Terminal sink — no response event
```

---

## Running the Agent-Based System

```bash
# Same as before — agents are wired internally
python -m src.launcher

# The launcher now also initializes:
# 1. EventBus singleton
# 2. All agents registered with bus
# 3. FastAPI routes publish events instead of calling services directly
```

---

## Key Principle: Strangler Fig Migration

```
Before:  API → SalesService → Repository → DB
After:   API → Event → OrderAgent → SalesService → Repository → DB
                                    ↑
                          (same code, just wrapped)
```

The agent layer wraps existing services. No business logic changes. The UI calls the same API endpoints. The only difference is internal: requests flow through the event bus.
