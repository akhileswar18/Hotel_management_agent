# Feature Specification: Agent-Based Architecture Refactor

**Feature Branch**: `001-agent-architecture-refactor`
**Created**: 2026-02-13
**Status**: Draft
**Input**: Upgrade HMS v2.0 monolith to agent-based event-driven architecture with central event bus, rule-based agents for core operations, LLM-powered insight agent for advisory reasoning, orchestrator for multi-step workflows, and voice/chat pipeline for hands-free ordering.

---

## User Scenarios & Testing

### User Story 1 — Event-Driven Order Flow (Priority: P1)

A cashier creates an order, adds items, and finalizes payment. The entire flow is handled by rule-based agents communicating via an event bus, instead of direct service calls. The UI and API contract remain identical — the cashier notices no difference in behavior, but internally every action is an event that is logged, auditable, and extensible.

**Why this priority**: This is the foundational architecture change. Every other story depends on the event bus and OrderAgent working correctly. Without this, no other agents can function.

**Independent Test**: Create an order via the existing POS UI → add 2 items → finalize with cash → verify order in DB, receipt generated, stock deducted, and every step recorded as an event in the event_log table.

**Acceptance Scenarios**:

1. **Given** the event bus is running and OrderAgent is registered, **When** a cashier clicks "New Order" in the POS UI, **Then** an `order.create` event is published, OrderAgent processes it, and the order appears in the database exactly as it does today.
2. **Given** an open draft order, **When** the cashier adds an item via the UI, **Then** an `order.add_item` event is published, stock is validated, and the order summary updates with correct totals.
3. **Given** a draft order with items, **When** the cashier clicks "Finalize", **Then** an `order.finalize` event cascades to PaymentAgent (records payment), InventoryAgent (deducts stock), PrintAgent (saves receipt), and AuditAgent (logs everything).
4. **Given** the entire flow completes, **When** an admin queries the event_log table, **Then** every step of the order lifecycle is recorded as immutable events with correlation IDs linking them.
5. **Given** the event bus is running, **When** all 73 existing tests are executed, **Then** every test passes with zero regressions.

---

### User Story 2 — Inventory Agent with Automatic Stock Management (Priority: P1)

When an order is finalized, stock is automatically deducted for every line item. When stock falls below the reorder level, a low-stock alert event is fired. When stock reaches zero, an out-of-stock notification appears. All inventory operations (stock-in, adjustments, archive) flow through events.

**Why this priority**: Inventory accuracy is a core business requirement. Auto-deduction on finalization prevents manual errors and ensures stock is always correct.

**Independent Test**: Record a stock-in event → verify stock updated. Finalize an order → verify stock deducted for each item. Verify low-stock alert fires when stock drops below reorder level.

**Acceptance Scenarios**:

1. **Given** an item with 50 units in stock, **When** an order with 3 units is finalized, **Then** the InventoryAgent automatically deducts 3 units, leaving 47 in stock.
2. **Given** an item with stock at reorder level (e.g., 10), **When** a sale reduces stock to 8, **Then** an `inventory.low_stock` event is published and the NotificationAgent displays a low-stock warning.
3. **Given** an item with 1 unit in stock, **When** a sale reduces stock to 0, **Then** an `inventory.out_of_stock` event is published.
4. **Given** an order is voided, **When** the InventoryAgent receives `order.voided`, **Then** it reverses the stock deductions for all line items.

---

### User Story 3 — Complete Agent Mesh (Priority: P2)

All system operations (authentication, payments, receipts, reports, notifications) are handled by dedicated agents. Each agent has a single responsibility, subscribes to specific events, and publishes outcomes. The system is fully decoupled — adding new functionality means adding a new agent, not modifying existing code.

**Why this priority**: Completes the architectural migration. Without all agents wired, the system is partially event-driven, which creates maintenance complexity.

**Independent Test**: Login via auth event → session created. Finalize order → payment recorded by PaymentAgent. Generate report via ReportingAgent event. Print receipt via PrintAgent event. Verify each agent handles only its declared events.

**Acceptance Scenarios**:

1. **Given** a user enters credentials, **When** `auth.login` event is published, **Then** AuthAgent validates credentials, creates a session, and publishes `auth.logged_in`.
2. **Given** an order is finalized, **When** `payment.process` event is published, **Then** PaymentAgent records the payment and publishes `payment.completed`.
3. **Given** a manager requests a daily report, **When** `report.daily_sales` event is published, **Then** ReportingAgent generates the summary without modifying any data.
4. **Given** any error occurs in any agent, **When** an `*.error` event is published, **Then** NotificationAgent displays a user-friendly toast message.

---

### User Story 4 — LLM-Powered Insights (Priority: P3)

An optional, advisory LLM agent provides intelligent suggestions: upsell recommendations based on current order items, sales trend analysis, and natural language queries ("What was our best-selling item last week?"). The LLM agent is strictly read-only — it can query data but never write to the database. The system works perfectly without it. If the LLM is unavailable or times out, the system continues operating normally with no impact on core functionality.

**Why this priority**: Adds intelligence layer without risking core operations. Advisory-only means it can be enabled/disabled at will.

**Independent Test**: Request an upsell suggestion for an order with Biryani → LLM suggests Raita and Lassi. Disable LLM → verify system continues working. LLM timeout → verify no impact on order flow.

**Acceptance Scenarios**:

1. **Given** an order with Biryani and Coke, **When** the system requests upsell suggestions, **Then** the InsightAgent returns 2-3 contextually relevant item suggestions with confidence scores.
2. **Given** the LLM service is unavailable, **When** an insight request is made, **Then** the system returns gracefully with no suggestions (no error, no crash, no delay to core operations).
3. **Given** the LLM takes more than 5 seconds, **When** the timeout expires, **Then** the request is silently dropped and the user sees no impact.
4. **Given** a manager asks "What was our revenue yesterday?", **When** a natural language query is submitted, **Then** the InsightAgent queries sales data (read-only) and returns a formatted answer.
5. **Given** the InsightAgent is running, **When** any database write is attempted from InsightAgent code, **Then** the system blocks the write and logs a security violation.

---

### User Story 5 — Voice & Chat Ordering (Priority: P3)

Staff can place orders using voice commands ("2 Biryani and 1 Coke for table 5, pay cash") or text chat. A local speech-to-text engine (Whisper) transcribes voice input offline. An intent parser extracts structured data (items, quantities, table, payment method). The OrchestratorAgent decomposes the command into a sequence of events (create order → add items → finalize). A confirmation step shows the parsed intent before executing. Text-to-speech provides audio feedback.

**Why this priority**: Voice ordering is the capstone feature that leverages the full agent architecture. It requires the event bus, orchestrator, and optionally the LLM for ambiguity resolution.

**Independent Test**: Say "2 Biryani for table 5" → verify transcript → verify parsed intent → confirm → verify order created with 2 Biryani assigned to table 5. Test offline (no internet) → verify Whisper works locally.

**Acceptance Scenarios**:

1. **Given** a cashier presses the microphone button, **When** they say "2 Biryani and 1 Coke for table 5", **Then** the system transcribes the speech, parses the intent (items: [{Biryani, 2}, {Coke, 1}], table: 5), and shows a confirmation dialog.
2. **Given** the confirmation dialog shows the parsed intent, **When** the cashier confirms, **Then** the OrchestratorAgent fires: `order.create` → `order.add_item` (Biryani x2) → `order.add_item` (Coke x1) in sequence.
3. **Given** the voice command includes "pay cash", **When** confirmed, **Then** the orchestrator also fires `order.finalize` with payment method CASH.
4. **Given** no internet connection, **When** voice input is captured, **Then** local Whisper STT processes it offline with acceptable accuracy.
5. **Given** the voice command is ambiguous ("I want chicken"), **When** multiple items match, **Then** the system asks for clarification ("Did you mean Butter Chicken or Chicken Tikka?") via TTS or UI dialog.
6. **Given** a user types "what's on the menu?" in the chat interface, **Then** the system lists available items with prices.

---

### User Story 6 — System Verification & Documentation (Priority: P2)

All existing functionality continues working unchanged. Performance meets or exceeds current benchmarks. Every event contract is validated. Test coverage reaches 80%+. All documentation reflects the agent-based architecture.

**Why this priority**: Ensures the refactor doesn't break anything and the system is maintainable long-term.

**Independent Test**: Run full test suite → all tests pass. Run performance benchmarks → no regression. Validate event contracts → all schemas match.

**Acceptance Scenarios**:

1. **Given** the agent refactor is complete, **When** all 73 existing tests are run, **Then** every test passes without modification.
2. **Given** the event bus is active, **When** performance benchmarks are run, **Then** order creation is still under 100ms and finalization under 500ms.
3. **Given** the event contracts in `specs/main/contracts/`, **When** contract validation tests run, **Then** every event type matches its declared schema and every agent subscribes/publishes only its declared events.
4. **Given** the full test suite, **When** coverage is measured, **Then** it exceeds 80% across all source files.

---

### Edge Cases

- What happens when an agent crashes mid-event? The event bus retries up to 3 times with exponential backoff, then routes to dead letter queue.
- What happens when two agents try to modify the same order simultaneously? Events are processed sequentially per correlation_id — no concurrent modification.
- What happens when the event_log table grows very large? Periodic cleanup via `scripts/backup.py vacuum` and optional archival of old events.
- What happens when the LLM suggests an item that's out of stock? The suggestion is advisory — the user must add it through the normal order flow, which will check stock.
- What happens when voice recognition fails? The system falls back to text input. No order is created until the user explicitly confirms.
- What happens when a multi-step orchestrator workflow fails partway? The orchestrator rolls back by voiding any partially created order.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST route all order operations through an in-process event bus without degrading response time by more than 5%.
- **FR-002**: System MUST support event types in dot-notation format (e.g., `order.create`, `inventory.stock_in`) with wildcard subscription (`*`, `order.*`).
- **FR-003**: System MUST persist every event to an append-only event_log table with correlation IDs linking related events.
- **FR-004**: Rule-based agents MUST handle all database-writing operations (orders, inventory, payments, auth). LLM agents MUST be read-only.
- **FR-005**: System MUST function normally when LLM agents are unavailable, timed out, or disabled.
- **FR-006**: The existing UI and API contract MUST remain unchanged — all current screens, endpoints, and response formats work identically.
- **FR-007**: Voice input MUST be processed locally using an offline-capable speech-to-text engine with acceptable accuracy for menu item names.
- **FR-008**: Multi-step voice commands MUST show a confirmation dialog before executing any order changes.
- **FR-009**: System MUST support a text-based chat interface for natural language ordering as an alternative to voice.
- **FR-010**: All agent actions MUST be auditable — who triggered it, what changed, when, and the event that caused it.
- **FR-011**: System MUST retry failed event handlers up to 3 times before routing to a dead letter queue.
- **FR-012**: System MUST support event replay for debugging — given a correlation_id, reproduce the full event sequence.

### Key Entities

- **Event**: The fundamental communication unit — immutable, with type, payload, source, timestamp, and correlation_id. Persisted to event_log.
- **Agent**: A handler that subscribes to specific event types, processes them, and optionally publishes new events. Has declared capabilities (writes_to_db, uses_llm).
- **EventBus**: The central router that dispatches events to subscribed agents. Supports publish (fire-and-forget) and publish_and_wait (request-reply).
- **EventStore**: Append-only persistence layer for all events. Supports query by type, correlation_id, and time range.
- **AgentRegistry**: Maps event types to agent handlers. Supports wildcard matching and agent lifecycle management.
- **Workflow**: A multi-step sequence of events coordinated by the OrchestratorAgent, triggered by a single high-level command (e.g., voice order).

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: All existing 73 tests pass with zero modifications after the agent refactor is complete.
- **SC-002**: Order creation completes in under 100ms and order finalization in under 500ms, even when routed through the event bus.
- **SC-003**: The event bus can process 10,000+ events per second in-process (verified by benchmark).
- **SC-004**: System operates fully offline — all core operations (orders, inventory, payments, reports, auth) work without any network connection.
- **SC-005**: When the LLM agent is disabled or unavailable, zero core functionality is affected — orders, inventory, and reports work identically.
- **SC-006**: Voice commands are transcribed with 90%+ accuracy for common menu items when tested with 3 different speakers.
- **SC-007**: Test coverage across all source files reaches 80% or higher.
- **SC-008**: Every event type defined in the contract files has a corresponding handler, and every agent publishes only its declared event types (verified by contract tests).
- **SC-009**: A complete order workflow (create → add 3 items → finalize → receipt) via voice command completes in under 15 seconds including confirmation.
- **SC-010**: Documentation (README, ARCHITECTURE, DEPLOYMENT) accurately describes the agent-based architecture and voice/chat features.

---

## Assumptions

- Whisper (OpenAI's open-source STT model) can run locally on the target hardware (Windows 10+, 8GB+ RAM) with acceptable latency (<4 seconds per utterance).
- Menu item names in the restaurant are primarily in English or Romanized Hindi — the STT model handles these adequately.
- The existing SalesService, InventoryService, AuthService, and ReportingService are correct and well-tested — agents wrap them without modifying their internal logic.
- SQLite's WAL mode can handle the additional event_log writes without measurable performance impact.
- pyttsx3 (or similar) provides adequate text-to-speech quality for voice feedback on Windows.
- Staff will be trained on voice commands and the confirmation workflow before production use.

---

## Scope Boundaries

### In Scope
- In-process event bus (asyncio-based, no external broker)
- 10 agents (8 rule-based + 1 LLM + 1 orchestrator)
- Event persistence (event_log table)
- Local STT via Whisper
- Local TTS via pyttsx3
- Text chat interface
- Intent parsing (rule-based with LLM fallback)
- API route migration to events
- Contract and integration tests

### Out of Scope
- Cloud sync / multi-device event distribution
- External message brokers (Redis, Kafka, RabbitMQ)
- Real-time multi-user collaboration
- Mobile app voice integration
- Multi-language STT (English only for Phase 1)
- Custom LLM fine-tuning
- Purchase order workflows
- Loyalty/rewards integration
