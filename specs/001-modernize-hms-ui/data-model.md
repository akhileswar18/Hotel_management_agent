# Data Model: Modernized HMS UI

## Overview

This feature does not introduce new business entities. It adds view-oriented models for the redesigned UI and one additive persisted field, `kitchen_status`, on existing orders.

## Entities

### StaffSessionView

**Purpose**: Captures the logged-in user's display context for headers, role gating, and navigation.

**Fields**:

- `user_id`: stable identifier for the logged-in user
- `username`: display name shown in header and greeting
- `role`: current role label used for action visibility
- `offline_ready`: always-visible operational badge state

**Validation Rules**:

- `role` must map to an existing system role
- `username` must always be displayable in header chip form

### NavigationState

**Purpose**: Tracks which screen is active and which quick actions or badges should be emphasized.

**Fields**:

- `active_screen`: dashboard, pos, inventory, billing, reports, kitchen, ai, or login
- `low_stock_count`: badge count used by navigation
- `current_user_role`: used for visibility and navigation defaults

**Validation Rules**:

- `active_screen` must be one of the supported route targets
- `low_stock_count` must not be negative

### DashboardSnapshot

**Purpose**: Supplies at-a-glance operational summary after login.

**Fields**:

- `display_date`
- `greeting_name`
- `today_revenue`
- `orders_today`
- `low_stock_alerts`
- `average_order_value`
- `active_orders`: collection of `OrderTicketView`
- `recent_activity`: collection of `AuditActivityView`
- `payment_breakdown`: collection of `PaymentBreakdownEntry`

**Validation Rules**:

- Missing or unavailable metrics must degrade to safe placeholder values rather than blank UI
- `payment_breakdown` percentages must sum to 100% or degrade gracefully when incomplete

### OrderTicketView

**Purpose**: Shared order representation for dashboard, POS, billing, and kitchen display.

**Fields**:

- `order_id`
- `table_id`
- `status`: existing order lifecycle value
- `kitchen_status`: additive kitchen lifecycle value
- `line_items`
- `subtotal`
- `discount_total`
- `tax_total`
- `grand_total`
- `receipt_number`
- `created_at`
- `updated_at`

**Validation Rules**:

- `kitchen_status` must be one of `PENDING`, `COOKING`, `READY`, or `SERVED`
- Out-of-stock items must never appear as newly addable selections in POS, even if they exist in historical finalized orders

**State Transitions**:

- `kitchen_status`: `PENDING -> COOKING -> READY -> SERVED`
- Existing order `status` remains unchanged by this feature and continues to represent the business lifecycle independently

### MenuItemCard

**Purpose**: View model for POS card-grid presentation.

**Fields**:

- `item_id`
- `name`
- `category`
- `price`
- `stock_quantity`
- `reorder_level`
- `availability_state`: available, low, or out

**Validation Rules**:

- `availability_state` is derived from stock quantity relative to reorder threshold
- Out-of-stock items must be visually disabled and non-actionable

### InventoryRecordView

**Purpose**: View model for inventory table and alert sidebar.

**Fields**:

- `item_id`
- `name`
- `category`
- `unit_price`
- `in_stock`
- `reorder_at`
- `status`: in stock, low, critical, out
- `max_reference_stock`: display-only value for bar scaling

**Validation Rules**:

- `status` must be consistent with current quantity and reorder level
- `max_reference_stock` must be non-zero before rendering a proportional stock bar; otherwise render an empty track safely

### StockLedgerEntryView

**Purpose**: Shows accountability history for stock changes.

**Fields**:

- `timestamp`
- `item_name`
- `change_type`
- `quantity_delta`
- `balance_after`
- `performed_by`

**Validation Rules**:

- Quantity deltas must preserve sign for gains vs reductions
- `performed_by` must fall back to a readable identifier when a display name is unavailable

### InvoicePreview

**Purpose**: Represents the cashier's real-time bill verification model.

**Fields**:

- `receipt_number`
- `hotel_name`
- `table_id`
- `cashier_name`
- `line_items`
- `subtotal`
- `discount_total`
- `tax_total`
- `grand_total`
- `payment_method`
- `amount_received`
- `change_due`

**Validation Rules**:

- `change_due` must never display as a negative amount
- Tax and total values must match existing backend calculations exactly

### RecentInvoiceView

**Purpose**: Displays recent billing history for reprint access.

**Fields**:

- `receipt_number`
- `table_id`
- `item_count`
- `total_amount`
- `payment_method`
- `issued_at`
- `status`

**Validation Rules**:

- Finalized invoices must remain reprintable from the UI
- Void invoices must be visually distinguished from paid invoices

### AuditActivityView

**Purpose**: Normalized activity item for dashboard activity feed and AI event log.

**Fields**:

- `id`
- `event_type`
- `description`
- `user_id`
- `created_at`
- `metadata`
- `display_color`

**Validation Rules**:

- `description` must be human-readable
- `display_color` must derive consistently from event type family

### AIAgentStatusView

**Purpose**: Shows visible health and role of each agent on the AI screen.

**Fields**:

- `agent_name`
- `status`: active, standby, offline
- `capability_group`: core, llm, ready, standby
- `last_triggered_at`

**Validation Rules**:

- Every displayed agent must have a status, even if inferred as standby

### AITraceStep

**Purpose**: Represents one visible step in an AI command execution trace.

**Fields**:

- `step_name`
- `step_type`
- `execution_mode`: rules or llm
- `detail`
- `outcome`: pending, success, failed

**Validation Rules**:

- Trace steps must be ordered chronologically
- Failed steps must remain visible for auditability

## Relationships

- One `StaffSessionView` drives one `NavigationState`
- One `DashboardSnapshot` contains many `OrderTicketView` and many `AuditActivityView`
- One `OrderTicketView` contains many line items and may produce one `InvoicePreview`
- One `InventoryRecordView` may have many `StockLedgerEntryView`
- One AI command may produce many `AITraceStep` and many `AuditActivityView`
