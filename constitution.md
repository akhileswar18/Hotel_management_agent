# HMS Constitution: Hotel/Fast-Food Management System

**Version 1.0** | **Date**: February 2026

---

## Executive Summary

This document is the **non-negotiable constitutional foundation** for the Hotel/Fast-Food Management System (HMS). Every specification, architecture decision, feature implementation, and code change MUST comply with this constitution. Deviations require explicit amendment to this document, not workarounds.

**Project Identity:**
- **Product**: Offline-first, voice-enabled Sales, Inventory, and Reporting system for small-to-medium restaurants/hotels (F&B first).
- **Target Users**: Low-tech hospitality staff + managers needing reliable, simple tools on limited hardware.
- **Deployment Model**: Single-branch initially (Phase 1); multi-branch sync capability later (Phase 3).
- **North Star Metric**: **Correctness > Reliability > Usability > Performance > Features**

---

## 1. Non-Negotiable Principles

These principles are sacred and shape every decision:

### 1.1 Offline-First Architecture
- **MUST** ensure all critical workflows operate reliably without internet:
  - Billing & payments (cash, card payments must finalize locally)
  - Inventory tracking (stock-in, stock-out, adjustments)
  - Basic reports (daily sales, inventory summary)
  - User authentication (login locally using cached credentials)
- **MUST** make offline-first testable: every test suite includes a "no network" scenario.
- **SHOULD** sync to cloud when available, but NEVER block critical operations on network availability.
- Consequence: Local SQLite database is the source of truth; cloud is optional backup/multi-branch hub (Phase 3+).

### 1.2 Data Correctness is Non-Negotiable
- **MUST** ensure money, inventory, and audit logs are always correct and reproducible.
- **MUST** never lose a financial transaction, payment, or inventory change due to crashes, sync, or network issues.
- **MUST** support deterministic replay: given the same sequence of inputs, system produces identical output.
- **MUST** validate all user input and LLM-suggested parameters against strict schema/rules *before* committing to database.
- Every business rule (tax, discount, stock deduction) **MUST** be testable in isolation.

### 1.3 Auditability & Traceability
- **MUST** log every state-changing operation:
  - Who performed it (user_id, role)
  - What changed (operation type, before/after state)
  - When (timestamp, UTC)
  - Why (reason code, comments)
- **MUST** prevent tampering with audit logs (soft-delete friendly; hard-delete forbidden for financial records).
- **MUST** support audit queries: "Show me all changes to table X for date Y by user Z."
- Consequence: Forensic analysis of any financial/inventory discrepancy is always possible.

### 1.4 Safety for Destructive Actions
- **MUST** require explicit confirmation (2-factor intent) for:
  - Voids/cancellations of finalized orders
  - Refunds or manual adjustments over threshold
  - Inventory write-offs, deletions, or corrections
  - Role/permission changes
  - System-wide configuration changes
- **MUST** enforce role-based authorization: a waiter cannot void a finalized bill without manager approval.
- **MUST** log the reason, approver, and timestamp for all destructive actions.
- **SHOULD** implement a "dry-run" mode for staff training: simulate action without committing.

### 1.5 Minimal Friction UX
- **MUST** optimize POS workflows for staff with low technical literacy:
  - Create an order in ≤ 2 taps/clicks
  - Add items in ≤ 1 action per item
  - Display running totals, tax, discount in real-time
  - Finalize checkout in ≤ 3 steps
- **MUST** support keyboard-first navigation (tab, enter, numeric shortcuts) and touch-friendly buttons (min 44px, optimal 56px).
- **MUST** provide two interaction modes simultaneously:
  - **Touch/Keyboard Mode**: traditional POS UI with buttons, forms, menus
  - **Voice/Chat Mode**: conversational assistant for order entry, queries, troubleshooting
- **MUST** show system state at all times: current order summary, table/guest info, totals breakdown, payment method.
- **SHOULD** provide undo/edit patterns: "cancel last item," "hold order," "reopen non-finalized bill."
- **SHOULD** use local language/currency; support multi-language UI (Phase 2+).

### 1.6 Deterministic Business Logic
- **MUST** keep all business rules (tax calculation, discount logic, stock deduction, pricing rules) **deterministic and free of randomness or external service calls**.
- **MUST** isolate business logic in pure functions; no side effects, no database calls, no timestamps generated inside pricing logic.
- **MUST** make business rules testable without database setup: "apply 10% discount to $100 item" always = $90.
- **MUST** version business rules: if tax rules change, old orders still compute with old rules; future orders use new rules.
- Consequence: pricing, inventory, and reports are always reproducible and auditable.

### 1.7 AI is Assistive, Not Authoritative
- **MUST** use LLM/voice assistance for:
  - Intent & entity extraction ("order 2 biryani for table 3")
  - Clarification prompts ("which beverage size?")
  - Suggestions ("this item is out of stock; suggest alternatives?")
  - Natural language parsing of unstructured voice
- **MUST NOT** allow LLM to:
  - Bypass permissions ("manager only" rules)
  - Skip validation (e.g., apply a discount larger than allowed)
  - Execute actions without explicit confirmation
  - Override system state without audit trail
- **MUST** validate all LLM outputs against domain schema *before* committing:
  ```
  parsed_intent = llm.extract_intent(voice_text)
  validated_intent = validate_against_schema(parsed_intent)  // Raises error if invalid
  execute_intent(validated_intent)  // Commits only after validation
  ```
- **MUST** log LLM outputs separately (transcript, parsed intent, validation result) for debugging and compliance.

### 1.8 Modular Architecture with Clear Boundaries
- **MUST** organize code into independent modules:
  - **Sales**: orders, billing, payments, voids, refunds
  - **Inventory**: stock tracking, ledger, adjustments, wastage
  - **Procurement**: purchase orders, stock-in, supplier management (Phase 2+)
  - **Reporting**: daily sales, inventory status, variance analysis (Phase 1+)
  - **Users/Roles**: authentication, authorization, permission enforcement
  - **Finance**: GL, P&L, cost allocation (Phase 3+)
  - **Sync**: conflict resolution, outbox, cloud replication (Phase 3+)
- **MUST** ensure modules communicate only through well-defined service interfaces (not direct DB access).
- **MUST** prevent circular dependencies: A→B→C is OK; A→B→A is forbidden.
- **MUST** publish module contracts (input/output types, validation rules, error handling) in module README.

### 1.9 Security by Default
- **MUST** require authentication for every user action:
  - Login with user_id + pin/password (support cached login for offline mode).
  - Sessions scoped to single device; logout on app close.
- **MUST** enforce role-based access control (RBAC):
  - Waiter: create order, take payment (no void, no discounts > 5%)
  - Manager: void, adjust, grant discounts > 5%, view reports
  - Admin: role management, system configuration, user management
- **MUST** never commit secrets (API keys, DB passwords, signing keys) to version control.
- **MUST** store sensitive data encrypted at rest (device-level encryption for SQLite).
- **MUST** use HTTPS for cloud communication (Phase 2+); validate SSL certificates.
- **SHOULD** implement rate-limiting for API endpoints to prevent brute-force attacks.

### 1.10 Maintainability by Design
- **MUST** keep modules small (≤500 lines per file, ≤20 lines per function for business logic).
- **MUST** prefer pure functions and immutable data structures for business logic.
- **MUST** use type safety: TypeScript, Python type hints, or similar (no dynamic typing for domain logic).
- **MUST** document every module's contracts, error cases, and integration points in code comments + README.
- **MUST** maintain a dependency graph diagram (keep circular dependencies at zero).
- **MUST** update documentation (specs, architecture, README) *with* code changes, not after.

---

## 2. Architecture Guardrails

### 2.1 Layered Architecture (Four Layers)

```
┌─────────────────────────────────────┐
│   Interface Layer (UI + API)        │  ← User-facing: web, mobile, voice
├─────────────────────────────────────┤
│  Application Layer (Services)       │  ← Orchestration, use-cases, auth
├─────────────────────────────────────┤
│  Domain Layer (Business Logic)      │  ← Pure rules, no DB/UI/network
├─────────────────────────────────────┤
│ Infrastructure Layer (DB, Sync, I/O)│  ← SQLite, cloud API, printer, voice
└─────────────────────────────────────┘
```

- **Domain Layer** (Innermost): Pure business logic, zero dependencies on DB, UI, network, or framework.
  - Examples: tax calculation, discount validation, stock deduction logic, billing rules.
  - **MUST** be testable in isolation; **MUST** be deterministic.
  
- **Application Layer**: Services orchestrating domain logic + repositories. No business rules here, only workflows.
  - Examples: `CreateOrderService`, `FinalizeOrderService`, `RecordInventoryAdjustmentService`.
  - **MUST** handle transactions, logging, and error propagation.
  
- **Infrastructure Layer**: Database, file I/O, external service calls (LLM, cloud sync, printer), voice/STT.
  - Examples: `OrderRepository`, `SyncManager`, `VoiceSTTClient`, `PrinterService`.
  - **MUST** abstract DB-specific logic; expose repository interface to application layer.
  
- **Interface Layer**: REST API, UI screens, voice/chat commands.
  - **MUST** validate input, format output, handle presentation concerns only.

### 2.2 Data Persistence

- **MUST** use **SQLite** as the local database (file-based, no server needed, good offline story).
- **MUST** design schema to be self-describing:
  - All tables have `id (uuid)`, `created_at`, `updated_at`, `created_by`, `updated_by`.
  - Foreign keys enforce referential integrity.
  - Indexes on high-query columns (order_id, transaction_date, item_id).
- **MUST** use migrations for schema changes; never auto-create tables.
- **MUST** support soft-delete (add `deleted_at` column) for financial/audit records; hard-delete only for non-sensitive data.
- **MUST** implement database-level constraints: NOT NULL, UNIQUE, CHECK, FOREIGN KEY.

### 2.3 Synchronization & Conflict Resolution

- **MUST** implement an **append-only outbox** pattern:
  - Every state-changing operation writes to an operation log (outbox table) in the same transaction.
  - Background sync worker reads from outbox, sends to cloud in order, marks as synced.
  - If sync fails, retry exponentially (max 10 retries over 24 hours).
  
- **MUST** ensure idempotency: syncing the same operation twice produces the same result.
  - Use operation_id (UUID) as idempotency key; cloud side deduplicates.
  
- **MUST** document conflict resolution rules:
  - "Last-write-wins" for non-critical fields (e.g., memo).
  - "Reject-on-conflict" for financial fields (e.g., if order edited on two branches, require manual reconciliation).
  - "Merge" for inventory (e.g., sum stock-in from two branches).
  
- **SHOULD** provide a conflict resolution UI (Phase 2+): staff can review and resolve conflicts.
- **MUST NOT** silently discard data during sync.

### 2.4 Module APIs & Repositories

- **MUST** expose a clean service interface for each module:
  ```typescript
  // Example: SalesService
  interface ISalesService {
    createOrder(input: CreateOrderInput): Promise<Order>;
    finalizeOrder(orderId: string, paymentInput: PaymentInput): Promise<FinalizedBill>;
    voidOrder(orderId: string, reason: string, approver: UserId): Promise<void>;
    getOrder(orderId: string): Promise<Order | null>;
  }
  ```
  
- **MUST** define clear input/output types (no `any` types; use strict interfaces).
- **MUST** enforce validation at the service boundary: if input is invalid, throw typed error.
- **MUST** prevent cross-module database access:
  - ❌ Inventory module directly queries `sales.orders` table.
  - ✅ Inventory module calls `SalesService.getOrder()` or uses well-defined queries.
  
- **MUST** keep repositories simple: CRUD + basic queries only. Complex logic belongs in services/domain.

---

## 3. Data & Consistency Rules

### 3.1 Universal Table Metadata

Every table **MUST** include:

| Column | Type | Rules |
|--------|------|-------|
| `id` | UUID | Primary key; auto-generated on insert |
| `created_at` | Timestamp UTC | Auto-set on insert; immutable |
| `updated_at` | Timestamp UTC | Auto-set on insert/update |
| `created_by` | FK to users | User who created record; immutable |
| `updated_by` | FK to users | User who last modified record |

### 3.2 Sales & Billing Rules

- **MUST** represent orders as immutable once finalized:
  - Order state: `draft` → `finalized` → `closed` (or `voided`).
  - Finalized orders cannot be edited; changes only via void/refund records.
  - Each finalized order receives an immutable **receipt number** (sequential, cannot be reused).
  
- **MUST** track every line item with explicit details:
  ```
  OrderLineItem {
    id: uuid
    order_id: uuid
    item_id: uuid
    quantity: number
    unit_price: money
    discount_amount: money
    discount_reason: string
    tax_amount: money
    total_amount: money
    created_by: user_id
  }
  ```
  
- **MUST** represent payments separately:
  ```
  Payment {
    id: uuid
    order_id: uuid
    amount: money
    method: enum (CASH, CARD, VOUCHER, etc.)
    reference: string (receipt number, card ref, voucher code)
    finalized_at: timestamp
    finalized_by: user_id
  }
  ```
  
- **MUST** record voids/refunds as separate transactions (never update original order):
  ```
  VoidRecord {
    id: uuid
    original_order_id: uuid
    void_reason: enum
    voided_by: user_id
    voided_at: timestamp
    approval_by: user_id (if required)
  }
  ```
  
- **MUST** round all money calculations using a single, tested rounding function (e.g., round to 2 decimals, banker's rounding).
- **MUST** make taxes and discounts explicit line items (never implicit in price).

### 3.3 Inventory Rules

- **MUST** track stock as a **ledger** (never update `stock_on_hand` directly):
  ```
  StockLedger {
    id: uuid
    item_id: uuid
    transaction_type: enum (PURCHASE, SALE, ADJUSTMENT, WASTAGE, RETURN, TRANSFER)
    quantity_change: number (positive or negative)
    reason: string
    reference_id: uuid (order_id, purchase_order_id, etc.)
    recorded_at: timestamp
    recorded_by: user_id
  }
  ```
  
- **MUST** compute `stock_on_hand` as a sum of ledger entries (never a cached column).
- **MUST** validate stock before deducting in a sale (fail early if insufficient).
- **MUST** prevent negative stock without an explicit adjustment reason.
- **MUST** track stock location/warehouse (Phase 1+: single warehouse; Phase 3+: multi-warehouse).

### 3.4 Money Rules

- **MUST** define currency as a project constant (e.g., INR, USD) and enforce it everywhere.
- **MUST** store money as integers (cents/paise) or precise decimals; never floats.
- **MUST** define and centralize all rounding rules:
  ```typescript
  function roundMoney(value: number): number {
    return Math.round(value * 100) / 100;  // 2 decimal places
  }
  ```
  
- **MUST** ensure tax, discount, and totals always balance:
  ```
  subtotal = sum of (quantity × unit_price) for all items
  total_discount = sum of discounts
  total_tax = (subtotal - total_discount) × tax_rate
  final_total = subtotal - total_discount + total_tax
  ```
  
- **MUST** test all financial calculations with edge cases (1 paise items, mixed tax rates, rounding boundaries).

### 3.5 Audit Log Schema

- **MUST** maintain a separate `AuditLog` table:
  ```
  AuditLog {
    id: uuid
    entity_type: string (Order, Payment, StockLedger, User, etc.)
    entity_id: uuid
    operation: enum (CREATE, UPDATE, DELETE, VOID, REFUND, etc.)
    user_id: uuid
    role_at_time: string
    timestamp: timestamp
    old_state: json (nullable)
    new_state: json
    reason: string (nullable)
  }
  ```
  
- **MUST** log every state change automatically (via DB triggers or application middleware).
- **MUST** never delete audit logs; soft-delete if needed, but never hard-delete.
- **MUST** make audit logs queryable (indexed by entity_type, entity_id, timestamp, user_id).

---

## 4. Logging & Observability

### 4.1 What Must Be Logged

**Sales Lifecycle:**
- Order created (order_id, user, items, table/guest info)
- Item added/removed (order_id, item_id, qty, price)
- Discount applied (order_id, discount %, amount, reason, approver)
- Order finalized (order_id, payment method, amount, receipt number)
- Order voided (order_id, reason, approver)
- Refund issued (original_order_id, amount, reason)

**Inventory Lifecycle:**
- Stock-in (item_id, qty, purchase_order_ref, supplier)
- Stock-out (item_id, qty, order_id, reason)
- Adjustment (item_id, qty_change, reason, approver)
- Write-off (item_id, qty, reason, approver)

**Authentication & Authorization:**
- User login (user_id, timestamp, device_id, success/failure)
- User logout (user_id, timestamp)
- Failed login attempt (username, IP, count)
- Permission denied action (user_id, action, required_role)
- Role/permission change (user_id, old_role, new_role, changed_by, timestamp)

**System & Voice:**
- Sync started/ended (timestamp, records sent, records synced, conflicts)
- Sync conflict detected (entity_type, entity_id, local_state, remote_state)
- Printer error (error message, recovery action)
- Voice transcript received (text, intent, confidence %)
- Voice intent validation (input intent, validation result, errors if any)
- Voice action executed (intent, params, result, timestamp)

### 4.2 Log Format & Storage

- **MUST** log to two places simultaneously:
  1. **Database** (queryable, indexed by timestamp/user/entity): `SystemLog` table.
  2. **Rotating file logs** (local files for debugging, max 100MB per file, auto-rotate): `logs/` directory.
  
- **MUST** use structured logging (JSON format):
  ```json
  {
    "timestamp": "2026-02-09T14:30:00Z",
    "level": "INFO",
    "category": "sales.billing",
    "user_id": "user_123",
    "action": "order_finalized",
    "entity_id": "order_456",
    "entity_type": "Order",
    "details": {
      "order_id": "order_456",
      "total": 1500.00,
      "payment_method": "CASH",
      "receipt_number": "REC-2026-001234"
    }
  }
  ```
  
- **MUST NOT** log:
  - Full payment card numbers (log last 4 digits only).
  - Passwords or tokens.
  - Personally identifiable information beyond user_id.
  
- **SHOULD** implement log levels: DEBUG, INFO, WARN, ERROR.
- **SHOULD** provide a log query UI (Phase 2+) to search by date, user, action, entity type.

### 4.3 Observability

- **MUST** expose system health metrics (Phase 2+):
  - DB connection health
  - Sync queue depth & last sync time
  - Voice STT availability (latency)
  - Printer connectivity
  
- **SHOULD** implement dashboards for operations staff:
  - Daily transaction count & revenue
  - Inventory exceptions (low stock, negative adjustments)
  - Failed syncs or voice parse errors
  - System uptime & error rate

---

## 5. Voice/Chat Assistant Rules

### 5.1 Voice Pipeline

Voice input follows this deterministic flow:

```
1. Capture Audio
   ↓
2. STT (Speech-to-Text) → Transcript
   ↓
3. Intent Extraction (NLU/LLM) → Parsed Intent + Entities
   ↓
4. Strict Validation (Schema + Business Rules) → Validated Intent
   ↓
5. Clarification Loop (If missing required fields, ask user)
   ↓
6. Confirmation Summary (Show user what will happen)
   ↓
7. Execute (Commit to DB if user confirms)
   ↓
8. Audio Confirmation (Speak result to user)
```

### 5.2 Assistant Capabilities

The assistant **MUST** support:

- **Order Creation**: "Order 2 biryani and 1 coke for table 5"
  - Extract: [item: biryani, qty: 2], [item: coke, qty: 1], table: 5
  - Clarify: if item ambiguous or table unknown, ask user
  - Confirm: "Creating order for table 5: 2 biryani, 1 coke. Correct?"
  
- **Inventory Queries**: "How much rice do we have?"
  - Respond with current stock and reorder level
  
- **Discounts**: "Apply 10% discount for table 3"
  - Validate: is user allowed to apply ≥10% discount?
  - Confirm: "Apply 10% discount (₹150) to table 3 order?"
  
- **Clarification**: Guide user if required fields are missing
  - Q: "Order for table?" A: (silent/unclear)
  - Assistant: "I didn't catch the table number. Is it table 1, 2, 3, or 4?"
  
- **Natural Language Parsing**: Support variations
  - "2 biryani" = 2× biryani item
  - "Tea, coffee, water" = 1 tea, 1 coffee, 1 water (all qty 1)

### 5.3 Assistant Constraints

The assistant **MUST NOT**:

- ❌ Bypass authentication: "Log in as manager" is forbidden; voice user is always the currently logged-in person.
- ❌ Exceed permission limits: If logged-in user is waiter, voice cannot apply discounts >5% or void orders.
- ❌ Skip validation: Voice is treated the same as UI input; all schema validation applies.
- ❌ Execute without confirmation: Sensitive actions (void, refund, high discount) require explicit "yes" response.
- ❌ Make assumptions about ambiguous input: If "order 2" could mean 2 items or 2 orders, ask for clarification.

### 5.4 Voice Logging & Compliance

- **MUST** log transcript, parsed intent, validation result, and executed action separately.
- **MUST** maintain a voice audit trail: "User X said Y, we understood Z, executed W at timestamp T."
- **SHOULD** implement voice training mode: allow staff to practice without committing actions (Phase 2+).

---

## 6. UX Principles

### 6.1 Speed-Optimized POS Flow

Every critical flow **MUST** meet these action counts:

| Flow | Max Actions | Example |
|------|-------------|---------|
| Create new order | 2 | (1) Select table, (2) Done (items added next) |
| Add item to order | 1 | Voice: "add 2 biryani" or UI: select item, confirm qty |
| Apply discount | 2 | (1) Select discount reason, (2) Confirm % or amount |
| Process payment | 3 | (1) Select payment method, (2) Enter amount, (3) Confirm |
| Finalize & print | 1 | Auto-print receipt after payment |

### 6.2 Dual-Mode Interface

- **MUST** provide simultaneous Touch/Keyboard and Voice/Chat modes:
  
  **Touch/Keyboard Mode:**
  - Large buttons (56px minimum), high contrast
  - Tab-navigable, keyboard shortcuts for common actions (F1=help, Ctrl+S=save, numeric pad for qty)
  - MUST support offline (no external API calls for UI rendering)
  
  **Voice/Chat Mode:**
  - Listen button always visible (one-tap to start recording)
  - Transcript displayed as user speaks
  - Parsed intent shown with confidence score
  - Confirmation screen before action
  - Text fallback: if voice fails, user can type

### 6.3 System State Display (Always Visible)

Every screen **MUST** show:

- **Order Summary** (if order is open):
  - Order ID, table/guest name, number of items
  - Running subtotal, discount (if any), tax, **total**
  
- **Stock Status** (when viewing items):
  - ✅ In stock (qty available) vs. ⚠️ Low stock vs. ❌ Out of stock
  
- **User Info** (top bar):
  - Current user, role, login time, offline indicator (⚠️ if no network)
  
- **System Time** (top right):
  - Current time (UTC or local, clearly labeled)
  
- **Action Feedback**:
  - Success: "✅ Order finalized. Receipt #REC-2026-001234 printed."
  - Error: "❌ Cannot void: insufficient permissions. Contact manager."

### 6.4 Undo & Edit Patterns

- **MUST** support:
  - **Cancel last item**: Remove most recently added item without re-confirming entire order
  - **Hold order**: Pause current order, start new one, return to held order later
  - **Reopen non-finalized order**: If payment was not processed, edit and re-finalize
  - **Cannot edit finalized orders**: Show void/refund option instead
  
- **SHOULD** provide quick access to recent orders (last 20 orders in sidebar).

### 6.5 Error Handling & Recovery

- **MUST** provide clear, actionable error messages:
  - ❌ Bad: "Error: Invalid input"
  - ✅ Good: "❌ Item 'Butter Chicken' is out of stock. (A) Choose alternative, (B) Back to menu"
  
- **MUST** never crash UI; all errors are caught and displayed.
- **MUST** provide offline fallback: if sync fails, queue action locally and retry automatically.

---

## 7. Testing Standards

### 7.1 Unit Tests (Domain/Business Logic)

- **MUST** test all domain functions in isolation:
  - Tax calculation: `calculateTax(subtotal, rate)` → correct result
  - Discount logic: `applyDiscount(price, discountType, amount)` → respects max limits
  - Stock deduction: `deductStock(itemId, qty)` → correct ledger entry created
  - Pricing rules: "buy 3 get 1 free" logic → correct final price
  
- **MUST** cover edge cases:
  - Zero values (₹0 order, 0 qty)
  - Maximum values (100% discount check, large order)
  - Rounding boundaries (0.005 rounds to 0.01)
  - Negative values (stock correction, refund)
  
- **MUST** maintain ≥80% code coverage for domain layer.
- **SHOULD** use property-based testing (QuickCheck, Hypothesis) for financial functions.

### 7.2 Integration Tests (DB + Repositories + Services)

- **MUST** test critical end-to-end flows:
  1. Create order → Add items → Apply discount → Finalize → Verify receipt number and ledger entries
  2. Record stock-in → Verify stock ledger → Query stock_on_hand → Correct
  3. Create order (deducts stock) → Finalize → Void → Verify stock restored and audit log complete
  
- **MUST** test with real database (or in-memory SQLite for tests).
- **MUST** verify all side effects: DB writes, audit logs, computed fields.
- **MUST** test transaction rollback: if payment fails, order and stock changes are rolled back.

### 7.3 Offline-Mode Smoke Tests

- **MUST** disable network and verify:
  - Login works with cached credentials
  - Create order works without cloud API
  - Inventory queries work from local DB
  - Basic reports (daily sales, stock summary) render
  - Sync queue is preserved when network returns
  
- **MUST** simulate network failure (kill network mid-request) and verify graceful degradation.

### 7.4 Voice/Chat Tests

- **MUST** test intent parsing with common phrases:
  - "2 biryani for table 3" → Correctly parsed
  - "order chicken" (ambiguous) → Asks clarification
  - "void last order" → Requires approval
  
- **MUST** test validation: malicious input ("apply 500% discount") is rejected before execution.
- **MUST** test permission enforcement: voice commands respect user role.

### 7.5 Regression Test Policy

- **MUST** add a test for every bug fix before fixing the bug.
- **MUST** keep all regression tests in the repo; never delete old tests.
- **MUST** run full test suite before merging any PR.

### 7.6 Test Documentation

- **MUST** document test scenarios in a `TESTING.md` file:
  - Offline smoke test procedure
  - Integration test setup (DB migrations, seed data)
  - Known flaky tests and workarounds

---

## 8. Coding Standards

### 8.1 Language & Type Safety

- **MUST** use typed languages:
  - Backend: TypeScript, Python (with type hints), or Go
  - Database: SQL with type-safe query builders (not string concatenation)
  - **NO** dynamic typing for domain logic; static analysis **MUST** pass
  
- **MUST** configure strict mode:
  - TypeScript: `"strict": true`, `"noImplicitAny": true`
  - Python: Run `mypy` in strict mode
  
- **MUST** use linting and formatting:
  - ESLint/Prettier (JS/TS)
  - Black/Flake8 (Python)
  - Consistent indentation (2 spaces for JSON, 4 for code)

### 8.2 Function & Module Design

- **MUST** keep functions small:
  - Pure business functions: ≤20 lines
  - Services: ≤50 lines per method
  - No "god functions" doing multiple responsibilities
  
- **MUST** prefer pure functions (no side effects):
  - ✅ `calculateTotal(items: Item[]): Money`
  - ❌ `calculateTotalAndSaveToDb(orderId)` (mixes logic + I/O)
  
- **MUST** make dependencies explicit:
  - Use dependency injection (pass dependencies as parameters or constructor args)
  - ❌ `class OrderService { db = new Database(); }` (hidden dependency)
  - ✅ `class OrderService { constructor(private db: IOrderRepository) {} }` (explicit)
  
- **MUST** define clear error types:
  - Create domain exceptions (ValidationError, InsufficientStockError, PermissionDeniedError)
  - Use structured error responses in APIs
  ```typescript
  interface ErrorResponse {
    code: string;        // "INSUFFICIENT_STOCK"
    message: string;     // "Item out of stock"
    details?: object;    // { item_id: "...", required_qty: 5, available: 2 }
  }
  ```

### 8.3 Module Organization

- **MUST** organize by feature/domain (not layer):
  ```
  src/
    sales/
      domain/           (business logic)
        order.ts        (Order entity, business rules)
        payment.ts      (Payment entity, rules)
      application/      (orchestration)
        createOrderService.ts
        finalizeOrderService.ts
      infrastructure/   (DB, external calls)
        orderRepository.ts
        paymentRepository.ts
      api/              (HTTP endpoints)
        salesController.ts
      __tests__/
        order.spec.ts
        orderService.spec.ts
    inventory/
      domain/
        stock.ts
      ...
  ```
  
- **MUST** prevent circular dependencies (use dependency injection to break cycles).
- **MUST** keep module coupling low (prefer stable abstractions over concrete implementations).

### 8.4 Documentation

- **MUST** include:
  - **Module README**: Purpose, exports, dependencies, examples
  - **Type/Interface comments**: Purpose of each field, valid ranges, constraints
  - **Complex logic comments**: Why (not what), especially for non-obvious algorithms
  - **Error handling**: What can go wrong and how it's handled
  
- **MUST** keep docs in sync with code: update docs in the same commit as code changes.
- **SHOULD** use JSDoc/Sphinx style comments for automatic doc generation.

### 8.5 Version Control

- **MUST** follow commit message format:
  ```
  <type>(<scope>): <subject>
  
  <body>
  
  Fixes: #<issue_number>
  ```
  Example:
  ```
  feat(sales): add support for percentage discounts
  
  - Implement discount validation (max 50% per item)
  - Add discount reason tracking
  - Update audit log schema
  
  Fixes: #124
  ```
  
- **MUST** use meaningful branch names: `feature/add-voice-assistant`, `fix/inventory-rounding`, `docs/architecture`.
- **MUST** never commit secrets; use `.gitignore` + environment variables.
- **SHOULD** require code review (PR) before merging to main.

---

## 9. Scope & Phasing Rules

### 9.1 Phase 1: Foundation (Months 1–3) — MUST Include

**Core Features:**
- ✅ User authentication (login, logout, cached offline)
- ✅ Order creation, items, finalization, receipt printing
- ✅ Basic inventory (stock tracking by ledger, stock-out on sale)
- ✅ Payments (cash, simple voucher)
- ✅ Roles & permissions (waiter, manager, admin)
- ✅ Audit logging (all state changes logged to DB)
- ✅ Basic reports (daily sales, inventory snapshot)
- ✅ Offline mode (all above work without network)

**Infrastructure:**
- ✅ SQLite DB with schema
- ✅ Rotating file logs + DB logs
- ✅ Printer stub (mock printer for testing)
- ✅ Touch/Keyboard UI (web or desktop)

**Quality:**
- ✅ Unit tests (domain logic, ≥80% coverage)
- ✅ Integration tests (critical flows)
- ✅ Offline smoke tests
- ✅ Architecture documentation

### 9.2 Phase 2: Enhancement (Months 4–6) — SHOULD Include

- ✅ Voice/STT MVP (record → transcribe → parse intent → execute)
- ✅ Inventory management: stock-in, adjustments, wastage
- ✅ Purchase orders (basic procurement)
- ✅ Better reporting: variance analysis, low-stock alerts
- ✅ Sync infrastructure (outbox pattern, conflict resolution rules documented)
- ✅ Multi-language UI (Hindi + English minimum)
- ✅ Advanced discounts (item-level, bill-level, promo codes)
- ✅ Voice training mode (practice without committing)

**Quality:**
- ✅ Voice intent test suite
- ✅ Sync conflict scenarios documented + tested
- ✅ Performance tuning (report query times)

### 9.3 Phase 3: Scale (Months 7+) — CAN INCLUDE

- ✅ Multi-branch sync (conflict resolution, eventual consistency)
- ✅ Finance module (GL, P&L, cost allocation)
- ✅ Loyalty program (points, redemption)
- ✅ Admin dashboard (multi-branch oversight)
- ✅ Advanced inventory (multi-warehouse, transfer orders)
- ✅ Integration with supplier APIs
- ✅ Mobile app (iOS/Android)

### 9.4 Out of Scope (Until Proven Necessary)

- ❌ Real-time analytics (Phase 2+, if perf allows)
- ❌ AI-powered forecasting (Phase 3+, nice-to-have)
- ❌ Blockchain/immutable ledger (unnecessary complexity)
- ❌ Advanced ML (focus on deterministic rules first)
- ❌ 3rd-party payment gateway integration (Phase 2+, if required)

---

## 10. Definition of Done

A feature is **done** (and ready to merge) **only if ALL of the following are true:**

### 10.1 Functional Completeness
- [ ] Feature requirements met (spec updated + verified)
- [ ] Works in offline mode (no network, no crashes)
- [ ] Works in online mode (syncs correctly if applicable)
- [ ] Error cases handled gracefully (no user-facing stack traces)

### 10.2 Testing
- [ ] Unit tests added for domain/business logic
- [ ] Integration tests cover critical paths
- [ ] All tests pass locally and in CI
- [ ] No regression: old tests still pass
- [ ] Offline scenario tested (if applicable)

### 10.3 Logging & Observability
- [ ] All state-changing operations logged (audit trail complete)
- [ ] Structured logging (JSON format, queryable)
- [ ] Error cases logged with context (user, action, timestamp, error details)
- [ ] No secrets logged (tokens, full payment details, passwords)

### 10.4 Permissions & Security
- [ ] Role-based authorization enforced (no bypass possible)
- [ ] Destructive actions require confirmation + approver role
- [ ] Logged-in user verified (no privilege escalation)
- [ ] No hardcoded secrets in code

### 10.5 Documentation
- [ ] Spec/feature doc updated (if applicable)
- [ ] Code comments added for non-obvious logic
- [ ] Module README updated (if new module or new API)
- [ ] Architecture diagram updated (if structure changed)
- [ ] Database schema changes documented + migrated

### 10.6 Code Quality
- [ ] Type checking passes (TypeScript strict, mypy, etc.)
- [ ] Linting passes (ESLint, Black, etc.)
- [ ] Code reviewed by at least one peer
- [ ] No circular dependencies introduced
- [ ] Function size ≤20 lines for business logic

---

## 11. Amendments & Change Control

### 11.1 How to Amend This Constitution

- **Any deviation from this constitution requires explicit amendment** (not implicit workarounds).
- Proposed amendment **MUST** include:
  1. **Rationale**: Why the change is necessary
  2. **Impact Analysis**: Affected components, risks, timelines
  3. **Risk Mitigation**: How to minimize negative effects
  4. **Approval**: Signed off by tech lead + product owner
  
- Amendment is added as a dated entry below with version bump.

### 11.2 Amendment Log

| Date | Version | Amendment | Rationale | Approved By |
|------|---------|-----------|-----------|-------------|
| 2026-02-09 | 1.0 | Initial constitution | Project kickoff | Tech Lead |
| | | | | |

---

## 12. Appendices

### A. Quick Reference: Must/Should/May

- **MUST**: Non-negotiable requirement; feature cannot be released without it.
- **SHOULD**: Strong recommendation; only skip with documented rationale.
- **MAY**: Optional; implement if time/resources allow.

### B. Key Definitions

- **Offline-first**: System operates with full functionality without internet; sync is secondary.
- **Deterministic**: Given same inputs, always produces same outputs (no randomness, no LLM-dependent behavior).
- **Auditability**: Every state change is logged with who, what, when, why, and reversible.
- **Role-based Authorization**: User actions restricted by assigned role (waiter ≠ manager ≠ admin).
- **Idempotent**: Operation can be retried safely; second execution has no additional side effects.
- **Soft-delete**: Mark record as deleted (set deleted_at field) instead of removing from DB.

### C. Related Documents

- `ARCHITECTURE.md` — Detailed architecture diagrams, module interactions
- `TESTING.md` — Test scenario documentation, setup procedures
- `API.md` — REST API specification (Phase 2+)
- `VOICE_SPEC.md` — Voice/chat pipeline details, intent schema
- `DB_SCHEMA.md` — Database schema, migrations, constraints
- `SYNC_RULES.md` — Conflict resolution, sync protocol (Phase 3+)
- `DEPLOYMENT.md` — Packaging, installation, configuration

---

## 13. Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | [Name] | 2026-02-09 | |
| Tech Lead | [Name] | 2026-02-09 | |
| Architecture Lead | [Name] | 2026-02-09 | |

---

**Status**: ✅ Approved and Active | **Last Updated**: 2026-02-09 | **Next Review**: 2026-04-30

This constitution is binding. All code, specifications, and decisions must align with these principles.

