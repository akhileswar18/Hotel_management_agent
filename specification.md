# HMS High-Level Specification
## Hotel/Fast-Food Management & Billing System

**Version**: 1.0 | **Date**: February 9, 2026 | **Status**: Foundation Spec

---

## 1. Vision & Purpose

### 1.1 Core Mission

To create a **reliable, offline-first agentic Hotel and Restaurant Management System** that empowers small and medium businesses to run sales, billing, and inventory with minimal training, intuitive voice and chat assistance, and complete auditability — ensuring accuracy, speed, and clarity for every transaction, even without internet connectivity.

### 1.2 Why It Matters

**Problem**: Small restaurants and hotels struggle with:
- High staff training burden (complex POS systems, manual processes)
- Billing errors and revenue leaks (manual entry, unclear totals, no audit trails)
- Inventory inaccuracy (stock miscounts, no real-time visibility)
- Network dependency (go dark when internet fails; lose critical sales data)
- Limited insight (no quick reports, hard to debug discrepancies)

**Solution**: HMS provides:
- ✅ Works offline (all critical workflows continue without internet)
- ✅ Voice/chat assistance (staff speaks orders; system understands and confirms)
- ✅ Deterministic accuracy (no guesswork; money, stock, and audit always correct)
- ✅ Minimal friction (2-tap billing, 1-tap order, large touch UI)
- ✅ Full auditability (every transaction, edit, and permission change logged)

### 1.3 Guiding Principles (from Constitution)

- **Offline-first**: All critical workflows function without internet.
- **Deterministic core**: Business rules are predictable, testable, and LLM-agnostic.
- **Auditability**: Every action is logged with who, what, when, before/after state.
- **Safety first**: Destructive actions require confirmation and proper permissions.
- **Minimal friction**: Simple UI, fast flows, voice-assisted workflows.
- **Correctness > Reliability > Usability > Performance > Features**

---

## 2. Target Users & Roles

### 2.1 Stakeholders

| Stakeholder | Needs | Pains |
|---|---|---|
| **Business Owner** | Visibility into revenue, inventory, staff performance; low operational cost; reliable system | Manual reconciliation, lost sales, staff errors |
| **Manager** | Quick reports, staff oversight, permission to adjust orders/discounts, easy training | Handling exceptions, debugging issues |
| **Waiter/Staff** | Fast order entry, clear feedback, simple UI, voice help | Slow POS, confusing buttons, training overhead |
| **Cashier/Checkout** | Fast payment, receipt, clear totals, easy refunds | Line delays, customer disputes, error correction |
| **Inventory Clerk** | Stock tracking, purchase orders, low-stock alerts, easy adjustments | Manual counts, stock-outs, no visibility |

### 2.2 User Roles & Permissions

| Role | Can Do | Cannot Do |
|---|---|---|
| **Waiter/Staff** | Create orders, add items, view totals, take payment (cash/card), view basic inventory | Void orders, apply discounts >5%, delete/edit finalized bills, access reports, user management |
| **Cashier** | All waiter actions + finalize payment, print receipt, reopen non-finalized orders | Void finalized orders, manual stock adjustments, staff management |
| **Manager** | All cashier actions + void/refund orders, apply any discount, manual stock adjustments, view reports, print daily summary, manage staff roles | User account creation, system config, financial/GL setup |
| **Inventory Clerk** | Record stock-in, stock-out, adjustments, view inventory reports, create purchase orders | Void/refund orders, cashier functions, user management |
| **Owner/Admin** | All actions (user management, system config, financial setup, reporting, compliance audits) | — |

---

## 3. Core Functional Areas

### 3.1 Billing & Point-of-Sale (POS)

#### Purpose
Enable fast, accurate order creation, item selection, discounting, payment processing, and receipt generation — even offline.

#### User Stories & Requirements

**MUST:**
- [ ] Waiter can create a new order and assign to table/guest in ≤2 actions
- [ ] Waiter can add items (with quantity, special requests) in ≤1 action per item
- [ ] System calculates and displays running subtotal, tax, total in real-time
- [ ] Staff can apply discounts (by reason: "bulk", "promo", "comp", etc.)
- [ ] Discount validation: waiter can apply ≤5%; manager can approve larger discounts
- [ ] Payment methods supported: Cash, Card (local swipe/PIN), Voucher
- [ ] Finalized order receives immutable receipt number (sequential, never reused)
- [ ] Receipt can be printed to local printer (auto-print or on-demand)
- [ ] System prevents editing finalized orders; changes via void/refund only
- [ ] All POS operations work offline (no cloud API required)

**SHOULD:**
- [ ] Waiter can hold order (pause, start new order, resume held order later)
- [ ] Waiter can cancel last item added without re-confirming entire order
- [ ] Manager can reopen non-finalized orders (before payment) to edit
- [ ] Quick-access sidebar showing last 20 orders (search by table/guest name)
- [ ] Voice mode: waiter can say "order 2 biryani, 1 coke for table 3" and system parses
- [ ] Show discount cap before applying (e.g., "Max 5% allowed; proceed?")

**CAN:**
- [ ] Complex splits (separate checks for table of 4)
- [ ] Loyalty points/voucher redemption
- [ ] Item modifiers (e.g., "Chicken Biryani - extra spice, no onion")
- [ ] Printed kitchen order (send to kitchen display system)

---

### 3.2 Inventory & Stock Tracking

#### Purpose
Track stock changes via append-only ledger; provide real-time stock status and low-stock alerts; prevent overselling; support stock adjustments with reason & approval.

#### User Stories & Requirements

**MUST:**
- [ ] System tracks stock as a ledger (never direct update of "stock_on_hand")
- [ ] Stock ledger entries: transaction_type (PURCHASE, SALE, ADJUSTMENT, WASTAGE, RETURN), quantity_change, reason, reference (order_id or manual)
- [ ] Stock-on-hand = sum of all ledger entries for that item (computed, not cached)
- [ ] When item added to order, system deducts from stock_on_hand (fails if insufficient)
- [ ] Inventory clerk can record stock-in (e.g., purchase delivery) with reference number
- [ ] Inventory clerk can record adjustments (e.g., "found 3 units, manual recount") with reason & approval
- [ ] System prevents negative stock without explicit adjustment reason & manager approval
- [ ] All inventory operations work offline (queued for sync when online)
- [ ] Stock ledger entries include created_by, created_at (audit trail)

**SHOULD:**
- [ ] Low-stock alerts for high-velocity items (e.g., "Rice down to 2 units")
- [ ] Stock variance reports (expected vs. actual after manual recount)
- [ ] Item categorization (section: "rice", "proteins", "beverages", etc.)
- [ ] Reorder level & quantity defined per item
- [ ] Inventory snapshot at day-end (total units, cost, value)
- [ ] Stock history graph (qty over time)

**CAN:**
- [ ] Multi-warehouse/storage location tracking
- [ ] Supplier management & auto-purchase orders
- [ ] Expiry date tracking (for perishables)
- [ ] Barcode scanning for stock-in/out

---

### 3.3 Procurement (Phase 2+)

#### Purpose
Create purchase orders, record stock-in from suppliers, track costs, and manage supplier relationships.

#### User Stories & Requirements

**MUST (Phase 2):**
- [ ] Inventory clerk can create purchase order (select items, qty, supplier)
- [ ] Inventory clerk can record stock-in (match PO, receive qty, validate)
- [ ] Purchase order creates ledger entry (PURCHASE transaction type)
- [ ] Cost tracking: each purchase order records item cost, total cost, delivery date

**SHOULD:**
- [ ] Supplier master data (name, contact, delivery lead-time)
- [ ] Auto-suggested reorder: "Rice at 5 units, reorder level 50, suggest order?"
- [ ] PO approval workflow (for large orders)

---

### 3.4 Reporting & Analytics

#### Purpose
Provide managers and owners with actionable insights into sales, inventory, and performance — accessible offline (basic reports) and cloud-synced (advanced dashboards).

#### User Stories & Requirements

**MUST:**
- [ ] Daily sales summary: total revenue, payment methods, items sold, top items
- [ ] Daily inventory snapshot: stock on hand, low-stock items, recent adjustments
- [ ] Filterable transaction log: search by date, user, table, item, payment method
- [ ] Report output: screen display (queryable) and print to file (CSV, PDF)
- [ ] All queries run locally on offline DB (no cloud dependency)

**SHOULD:**
- [ ] Period reports (weekly, monthly): revenue trend, variance (budgeted vs actual)
- [ ] Staff performance: number of orders, avg order value, discounts applied
- [ ] Inventory variance report: recount results vs. expected stock
- [ ] User audit report: logins, permission changes, destructive actions (voids, refunds)

**CAN:**
- [ ] Profit & loss statement (Phase 3, with cost accounting)
- [ ] Advanced analytics (busiest hours, item popularity, customer segments)
- [ ] Forecasting (demand prediction for procurement)

---

### 3.5 Authentication & Authorization

#### Purpose
Ensure only authorized staff perform actions; track who did what when; support offline login with cached credentials.

#### User Stories & Requirements

**MUST:**
- [ ] User login: username + PIN (4–6 digits, numeric for simplicity on touch devices)
- [ ] Offline login: system caches last N user credentials locally (encrypted), allows login if offline
- [ ] Online login: validate against server (if available); sync new users/roles when online
- [ ] Session scope: one user per device; logout on app exit or manual logout
- [ ] Permission enforcement: system prevents unauthorized actions (e.g., waiter cannot void order)
- [ ] Role-based access control: users assigned role (Waiter, Cashier, Manager, Clerk, Admin)
- [ ] Audit log: all login/logout/failed login attempts logged (timestamp, user, device, success/failure)

**SHOULD:**
- [ ] Role permission matrix: clear definition of "who can do what" (in system configuration)
- [ ] Password/PIN change: users can update own credentials
- [ ] Session timeout: auto-logout after 30 min inactivity
- [ ] Failed login lockout: 3 failed attempts → locked for 15 min

**CAN:**
- [ ] Biometric login (fingerprint, face) for future phones
- [ ] Two-factor authentication for sensitive roles (manager approval for large voids)

---

### 3.6 Audit Logging & Compliance

#### Purpose
Create an immutable record of all state-changing operations for compliance, debugging, and dispute resolution.

#### User Stories & Requirements

**MUST:**
- [ ] Every state-changing operation logged: operation type, user, timestamp, before/after state, reason (if applicable)
- [ ] Audit log persists locally (searchable) and syncs to cloud (Phase 2+)
- [ ] Log categories: Sales (order create, finalize, void, refund), Inventory (stock-in, adjustment, write-off), Auth (login, role change), System (sync events, errors)
- [ ] Cannot delete/edit audit logs; soft-delete only (logical deletion, not physical)
- [ ] Audit log visible to manager/owner: filter by date range, user, action type, entity

**SHOULD:**
- [ ] "Before/After" state for changes (e.g., discount from 0 to ₹150)
- [ ] Approval trail: log who approved a destructive action (void, large discount)
- [ ] Sensitive action flagging: flag voids, refunds, permission changes for easy review
- [ ] Compliance export: generate compliant audit report (e.g., "all transactions for tax period")

**CAN:**
- [ ] Real-time alerts for suspicious activity (too many voids, unusual discounts)
- [ ] Digital signing (manager signature for high-value transactions)

---

### 3.7 Offline Sync Behavior

#### Purpose
Ensure data is never lost; sync when online; handle conflicts gracefully; maintain single source of truth (local DB).

#### User Stories & Requirements

**MUST:**
- [ ] Local SQLite DB is always source of truth (not cloud)
- [ ] When online: background sync sends new transactions to cloud (append-only)
- [ ] Sync is non-blocking: staff can work while sync happens
- [ ] Sync retry logic: exponential backoff (max 10 retries over 24 hours)
- [ ] Sync status visible: indicator shows "synced", "syncing", "error" state
- [ ] Conflict rules documented: how conflicts are detected and resolved (last-write-wins for non-critical; reject-on-conflict for financial)

**SHOULD:**
- [ ] Sync progress indicator: "synced 47/50 transactions"
- [ ] Manual sync trigger: manager can force sync "now"
- [ ] Conflict resolution UI: if conflict detected, show "local vs. remote" and allow manual choice
- [ ] Audit log of sync events: when sync started, completed, failed, what was synced

**CAN:**
- [ ] Selective sync: choose which entities to sync (Phase 3)
- [ ] Bandwidth optimization: compress payloads, delta sync

---

### 3.8 Voice & Chat Assistant

#### Purpose
Enable natural language order entry and queries; reduce friction for low-tech staff; validate all AI-suggested actions before execution.

#### User Stories & Requirements

**MUST (Phase 2):**
- [ ] Voice input: staff taps microphone button, speaks order (e.g., "2 biryani, 1 coke, table 3")
- [ ] Speech-to-Text (STT): capture audio, transcribe to text
- [ ] Intent extraction: parse order intent (item, quantity, table/guest)
- [ ] Clarification loop: if ambiguous (item out of stock, table unknown), ask staff to clarify
- [ ] Validation: check all extracted fields against schema (item exists? quantity valid? table/guest valid?)
- [ ] Confirmation: show staff a summary before executing ("Creating order for table 3: 2 biryani, 1 coke. Confirm?")
- [ ] Execution: only after confirmation, create order in system
- [ ] Audio feedback: confirm result to staff ("Order created. Receipt number 1234.")
- [ ] Voice logs: log transcript, parsed intent, validation result, executed action (for debugging)
- [ ] Permission respect: voice cannot bypass roles (e.g., waiter voice cannot void order)

**SHOULD:**
- [ ] Natural language queries: "How much rice do we have?" → "254 units in stock"
- [ ] Discount handling: "Apply 10% discount for table 3" → validation → confirmation → execute
- [ ] Error recovery: if STT unclear, ask staff to repeat or suggest alternatives
- [ ] Training mode: practice voice without committing actions (Phase 2+)

**CAN:**
- [ ] Multi-language support (Hindi, Tamil, etc.)
- [ ] Accent/dialect learning (staff-specific STT models)
- [ ] Proactive suggestions ("Low on rice, suggest order?")

---

## 4. Non-Functional Requirements

### 4.1 Offline Reliability

- **MUST** work reliably without internet for ≥7 days (assume no network available)
- **MUST** queue all changes locally and sync when network available (no data loss)
- **MUST** not require cloud login to operate (cached credentials OK)
- **MUST** handle network reconnection gracefully (auto-resume sync, no manual intervention)

### 4.2 Performance Targets

| Operation | Target | Notes |
|---|---|---|
| Create order | ≤500ms | Local DB write + calculations |
| Finalize order (payment) | ≤1000ms | DB transaction, audit log, calculation |
| Print receipt | ≤2000ms | Printer I/O |
| Stock query (current qty) | ≤200ms | Sum ledger entries |
| Generate daily report | ≤5000ms | Aggregate ~1000 transactions |
| Search orders (by date) | ≤500ms | Indexed query |

### 4.3 Security & Data Protection

- **MUST** encrypt sensitive data at rest (PINs, payment details, cached credentials)
- **MUST NOT** store full credit card details (last 4 digits only)
- **MUST NOT** commit secrets (API keys, DB passwords) to version control
- **MUST** enforce authentication before any action (no guest/anonymous access)
- **MUST** validate all user input (prevent SQL injection, XSS, etc.)
- **SHOULD** use HTTPS for cloud communication (Phase 2+)

### 4.4 Auditability & Compliance

- **MUST** log all state-changing operations (immutable audit trail)
- **MUST** support compliance queries (e.g., "all voids in Jan 2026 for tax audit")
- **MUST** maintain financial data integrity (audit trail, checksums, no deletions)
- **SHOULD** support multi-currency (Phase 2+, for expansion)
- **SHOULD** integrate with tax/compliance frameworks (e.g., GST in India; Phase 3+)

### 4.5 Scalability & Hardware

**Phase 1 Target Hardware:**
- CPU: Dual-core, 1.5 GHz (e.g., Raspberry Pi 4, older laptop)
- RAM: 2–4 GB
- Storage: 16 GB (SQLite + logs + OS)
- Network: Intermittent LTE, WiFi, or offline

**Scalability Limits (Phase 1):**
- ≤1000 transactions/day
- ≤5000 inventory items
- ≤20 concurrent users (single branch)
- ≤1 year history (local DB)

**Phase 3 (Multi-branch):**
- Archive old data to cloud (keep recent 6 months locally)
- Sync only changed records (delta sync)

### 4.6 Usability & Accessibility

- **MUST** support touch UI (56px+ buttons, large text, high contrast)
- **MUST** support keyboard navigation (tab, enter, numeric shortcuts)
- **MUST** work with low-vision/colorblind users (WCAG AA standard minimum; Phase 2+)
- **MUST** support low-tech users (no prior POS experience)
- **MUST** provide contextual help (tooltips, on-screen guidance, help mode)

### 4.7 Maintainability

- **MUST** use typed code (TypeScript, Python with type hints, or similar)
- **MUST** maintain ≥80% test coverage for business logic
- **MUST** keep modules small and decoupled (clean architecture)
- **MUST** document architecture, APIs, and data schema (kept in sync with code)
- **MUST** use version control (Git) with clear commit messages
- **SHOULD** enable easy logging/debugging (queryable logs, debug mode)

---

## 5. Success Criteria

A specification is **complete and ready for implementation planning** if:

### 5.1 Functional Completeness

- [ ] **Billing & POS**: All must-haves specified (order creation, finalization, payment, receipt, void/refund)
- [ ] **Inventory**: Stock ledger, deduction on sale, adjustments, low-stock tracking defined
- [ ] **Reporting**: Daily reports (sales, inventory) specified; queries possible offline
- [ ] **Auth & Roles**: All roles defined; permissions matrix complete; offline login specified
- [ ] **Audit**: Logging requirements clear (what, when, by whom, before/after)
- [ ] **Offline/Sync**: Offline-first behavior, sync rules, conflict resolution defined
- [ ] **Voice** (Phase 2): Intent parsing, validation, confirmation flow clear (if Phase 1 includes voice)

### 5.2 Stakeholder Alignment

- [ ] Owner/Manager reviewed spec and agrees on Phase 1 priorities (sales + inventory + reports)
- [ ] Waiter/Cashier use cases validated (staff understands flow, no unknowns)
- [ ] Inventory Clerk requirements clear (stock-in, adjustments, visibility)
- [ ] Security/Compliance lead reviews audit log & data protection requirements

### 5.3 Technical Clarity

- [ ] Data model (schema, entities, relationships) conceptually clear
- [ ] Offline/online behavior unambiguous (what syncs, when, conflict rules)
- [ ] Role/permission model explicit (no guessing about "manager can do X")
- [ ] Performance targets realistic and measurable
- [ ] No "TBD" or "TK" items in core requirements

### 5.4 Traceability to Constitution

- [ ] Spec references Constitution (offline-first, deterministic, auditable, modular)
- [ ] All "must" requirements align with Constitution's non-negotiable principles
- [ ] Phase 1 scope matches Constitution Phase 1 scope
- [ ] Testing strategy aligned with Constitution standards (unit, integration, offline smoke tests)

### 5.5 Mockup/Wireframe Sketches (Optional)

- [ ] Rough sketches of POS screen (order entry, payment, receipt) exist
- [ ] Voice flow diagram (STT → parse → validate → confirm → execute) sketched
- [ ] Report example layout sketched (columns, filters, export options)

### 5.6 Known Constraints & Assumptions

- [ ] Assumptions documented (e.g., "Phase 1 is single branch only", "no multi-currency")
- [ ] Risks identified (e.g., "offline sync complexity", "STT accuracy for accents")
- [ ] Out-of-scope items listed (what won't be in Phase 1)

---

## 6. Constraints & Assumptions

### 6.1 Phase 1 Constraints

- **Single branch only**: No multi-location; all data is local to one restaurant/hotel
- **No advanced payments**: Cash + simple card swipe (no online payment gateways; Phase 2+)
- **No loyalty program**: Simple discounts only; no points, memberships (Phase 3+)
- **No complex GL/Finance**: No cost accounting, P&L, multi-currency (Phase 3+)
- **No advanced reporting**: No ML forecasts, real-time dashboards (Phase 3+)
- **Voice is optional in Phase 1**: MVP can launch with touch/keyboard only; voice adds in Phase 2

### 6.2 Assumptions

- **Staff have access to one device per shift** (shared tablet, cash register, or laptop)
- **WiFi/internet available at least once per day** (for sync backup; not required for operation)
- **Items and suppliers are pre-configured** (owner sets up menu, suppliers before go-live)
- **Tax rate is fixed** (single tax rate; multi-rate support Phase 3+)
- **Currency is fixed** (e.g., INR for India; no multi-currency in Phase 1)
- **No integration with external systems** (POS → Accounting, 3PL, etc. in Phase 3+)

### 6.3 Out of Scope (Phase 1)

- ❌ Multi-branch management
- ❌ Advanced accounting (GL, cost accounting, P&L)
- ❌ Loyalty/membership programs
- ❌ Online payments (payment gateway integration)
- ❌ Kitchen display system (KDS) integration
- ❌ Real-time analytics dashboards
- ❌ Advanced inventory (expiry tracking, multi-warehouse)
- ❌ Cloud reporting (all reporting is local)
- ❌ Mobile app (web or desktop only)
- ❌ Barcode scanning
- ❌ Third-party integrations (Zomato, Swiggy, UberEats)

---

## 7. Related Documents

- **[constitution.md](constitution.md)** — Non-negotiable principles, architecture guardrails, data rules
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Layered architecture, module boundaries, dependencies (TBD)
- **[DB_SCHEMA.md](DB_SCHEMA.md)** — SQLite schema, entity relationships, constraints (TBD)
- **[PHASE_1_ROADMAP.md](PHASE_1_ROADMAP.md)** — Detailed feature breakdown, sprints, milestones (TBD)
- **[API_SPEC.md](API_SPEC.md)** — REST API endpoints, request/response types (TBD, Phase 2+)
- **[VOICE_SPEC.md](VOICE_SPEC.md)** — Voice pipeline, intent schema, training data (TBD, Phase 2+)

---

## 8. Sign-Off & Approval

| Role | Name | Date | Status |
|---|---|---|---|
| Product Owner | [Name] | 2026-02-09 | Pending |
| Tech Lead | [Name] | 2026-02-09 | Pending |
| Operations Lead | [Name] | 2026-02-09 | Pending |

---

**Status**: 📋 **Draft** | **Last Updated**: 2026-02-09 | **Next Step**: Stakeholder Review & Refinement

