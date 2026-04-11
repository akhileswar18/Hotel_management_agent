# Data Model: Chat Order Real-Time Sync

## Overview

This feature does not introduce database entities. It adds a small in-memory UI coordination model so already-open screens can react to successful order changes.

## Entities

### Order Change Event

**Purpose**: Represents a successful order workflow outcome that other active screens should reflect immediately.

**Fields**:

- `event_type`: High-level event category such as create, finalize, void, hold, resume, or update.
- `order_id`: The affected order identifier when available.
- `table_id`: Service location or takeaway indicator when available.
- `status`: The resulting business status when provided by the originating workflow.
- `source_screen`: The UI surface that emitted the event, such as chat command, chat confirmation, or POS.
- `payload`: Raw workflow response data forwarded for listeners that need additional context.
- `occurred_at`: Local event emission time if the registry chooses to stamp it for debugging.

**Validation Rules**:

- Events are emitted only after a successful order action.
- Missing optional fields are allowed; listeners must tolerate partial payloads and refresh from the authoritative API.
- `event_type` must map to a known order-changing action.

### Order Change Listener

**Purpose**: Represents a registered callback owned by an active screen.

**Fields**:

- `listener_id`: Stable registry key for deduplication and unregister behavior.
- `screen_name`: Human-readable owner such as `kitchen` or `billing`.
- `callback`: Callable invoked with the current order change event payload.
- `active`: Whether the listener is currently registered.

**Validation Rules**:

- Registration must be idempotent for the same screen instance.
- Unregister must be safe even if the listener is already absent.
- Listener exceptions must be swallowed by the registry so other listeners still run.

### Kitchen Ticket View

**Purpose**: Read model for the KDS grid.

**Key Inputs**:

- Active finalized kitchen orders from the existing API.
- Optional order change event payload used only as a trigger.

**State Transitions**:

- `idle` -> `refreshing` when auto-refresh, manual refresh, or external notification fires.
- `refreshing` -> `rendered` after reload-and-render completes.
- `refreshing` -> `rendered` with prior/empty state if the refresh call fails.

### Billing Draft View

**Purpose**: Read model for the billing draft selector and invoice preview.

**Key Inputs**:

- Draft orders from the existing API.
- Recent invoices from the existing API.
- Optional order change event payload used only as a trigger.

**State Transitions**:

- `idle` -> `refreshing` when manual load or external notification fires.
- `refreshing` -> `rendered` after draft orders and dependent UI state are refreshed.
- `refreshing` -> `rendered` with fallback state if the refresh call fails.

## Relationships

- One **Order Change Event** can notify many **Order Change Listeners**.
- A **Kitchen Ticket View** owns one listener registration while the screen instance is active.
- A **Billing Draft View** owns one listener registration while the screen instance is active.
- Multiple **Ordering Surfaces** can emit the same **Order Change Event** shape.
