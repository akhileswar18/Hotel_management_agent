# Contract: Order Change Notification Registry

## Purpose

Define the in-process contract between the app shell and active order-related screens so successful order actions can trigger immediate refreshes on already-open views.

## Registry Surface

The app shell exposes three functions:

- `register_order_listener(listener_id, callback)`
- `unregister_order_listener(listener_id)`
- `notify_order_change(event_type, payload=None, source_screen=None)`

## Listener Contract

### Inputs

- `listener_id`: Unique key for the owning screen instance.
- `callback(event)`: Best-effort function invoked when an order change occurs.

### Behavioral Rules

- Registration is idempotent for a given `listener_id`.
- Unregister is safe to call multiple times.
- Listener failures are caught and ignored so remaining listeners still run.
- Missing listeners are treated as normal; notification never fails because a screen is not open.

## Event Contract

### Event Shape

```python
{
    "event_type": "created|updated|finalized|voided|held|resumed",
    "source_screen": "chat_command|chat_confirmation|pos",
    "payload": {...}
}
```

### Event Semantics

- Events are emitted only after a successful order-changing workflow.
- `payload` may be partial; listeners must prefer reloading authoritative data rather than trusting the payload alone.
- Event delivery is synchronous best-effort inside the process, but callers must not wait on listener completion for user-visible success.

## Listener Responsibilities

### Kitchen Listener

- Respond by reloading active kitchen orders and re-rendering the grid.
- Tolerate redundant calls due to overlap with timer-based refresh.

### Billing Listener

- Respond by reloading draft orders and dependent selection state needed for the billing list.
- Preserve current user context where practical.

## Out of Scope

- Cross-process messaging
- Queued or persisted events
- Backend API changes
- Database schema changes
