# Feature Specification: HMA Production Stabilization & OpenRouter LLM Integration

**Feature Branch**: `001-stabilize-hma-openrouter`  
**Created**: 2026-03-20  
**Status**: Draft  
**Input**: User description: "Make HMA production-ready by stabilizing existing screens/workflows and enabling live OpenRouter-backed AI agent interactions without adding new features."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reliable Agent-First Chat Experience (Priority: P1)

As a hotel manager, I can use the AI Agent screen in Ask mode and Command mode to get actionable, data-backed responses and execute operational commands so the agent-first workflow is usable in real service.

**Why this priority**: The AI Agent screen is the product differentiator and the most visible promise of the system.

**Independent Test**: Can be fully tested by logging in, opening AI Agent screen, sending an insight question and an operational command, and confirming a response plus resulting operational change.

**Acceptance Scenarios**:

1. **Given** the manager is logged in and online, **When** they submit an Ask-mode question on current business performance, **Then** the system returns an AI response grounded in current hotel data.
2. **Given** the manager is logged in and online, **When** they submit a Command-mode instruction such as creating an order, **Then** the system executes the workflow and reflects the change in operational screens.
3. **Given** the manager is logged in and the external AI provider is unavailable, **When** they submit Ask-mode or Command-mode input, **Then** the system returns a graceful degraded response and remains operational.

---

### User Story 2 - Stable Screen Rendering Across Operations (Priority: P2)

As a manager, I can navigate every primary screen without blank panels or runtime crashes so I can trust the system during service hours.

**Why this priority**: Production readiness depends on stable access to all existing workflows, even before deeper optimization.

**Independent Test**: Can be fully tested by launching the app, logging in, and visiting Login, Dashboard, POS, Inventory, Billing, Reports, Kitchen Display, and AI Agent screens while observing no runtime failures.

**Acceptance Scenarios**:

1. **Given** the application is launched, **When** the manager logs in with valid credentials, **Then** the dashboard and all navigation targets load with visible content or clear empty states.
2. **Given** the manager opens the Billing screen, **When** the screen initializes, **Then** the left panel is visible and interactive.
3. **Given** the manager navigates across all primary screens in a single session, **When** each screen is opened, **Then** the application shows no crash-causing runtime errors.

---

### User Story 3 - Verified Core Transaction Workflows (Priority: P3)

As operations staff, I can complete the key daily flows (order, inventory view, billing, kitchen updates, reporting) so hotel operations continue end-to-end without regressions.

**Why this priority**: Stability must include business-critical outcomes, not only visual rendering.

**Independent Test**: Can be fully tested by creating/finalizing an order, viewing inventory, completing payment, advancing kitchen status, and viewing same-day reporting outputs.

**Acceptance Scenarios**:

1. **Given** menu data is available, **When** staff creates and finalizes an order from POS, **Then** the order is persisted and visible in downstream workflows.
2. **Given** a finalized order exists, **When** staff opens Billing and completes payment, **Then** payment confirmation and transaction records are visible.
3. **Given** active orders exist, **When** kitchen staff updates order status, **Then** status changes are visible to other operational views.
4. **Given** completed transactions exist for the day, **When** the manager opens Reports, **Then** daily sales and related summaries are visible.

---

### Edge Cases

- External AI provider is temporarily unavailable during active use; system must continue with degraded responses and clear user messaging.
- Inventory/menu images are missing or unavailable; cards must still render with fallback visuals and no broken layout.
- There is no recent transactional data; dashboard/reports/chat insights must show empty-state messaging instead of failures.
- User submits ambiguous command text in Command mode; system must request clarification or apply safe fallback behavior.
- Multiple quick screen switches occur during active operations; navigation must not produce partial render states or blank panels.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow a manager to launch, authenticate, and access all primary screens in a single session.
- **FR-002**: The system MUST render each existing primary screen with visible interactive content or explicit empty states.
- **FR-003**: The Billing screen MUST display its left-side operational panel on load and keep it interactive throughout billing actions.
- **FR-004**: The POS and Inventory screens MUST display product cards with image content when available and fallback visuals when unavailable.
- **FR-005**: The system MUST allow staff to create and finalize an order from POS and surface resulting order state to dependent workflows.
- **FR-006**: The system MUST allow billing completion for finalized orders and record transaction outcomes for reporting.
- **FR-007**: The Kitchen Display workflow MUST allow order status progression and synchronize status changes across relevant views.
- **FR-008**: The Reports screen MUST present daily sales output and allow date-based report inspection.
- **FR-009**: The AI Agent screen MUST support Ask mode that returns responses backed by current business data.
- **FR-010**: The AI Agent screen MUST support Command mode that interprets natural-language instructions and triggers operational workflows.
- **FR-011**: The AI Agent screen MUST display active agent health/status indicators and clearly show the current AI provider and model identifier.
- **FR-012**: The system MUST use OpenRouter as a supported live AI provider for agent interactions.
- **FR-013**: The system MUST continue core operations when the external AI provider is unreachable, including graceful degraded responses in the AI Agent screen.
- **FR-014**: The system MUST avoid runtime navigation failures that block normal use across the existing eight-screen workflow.

### Key Entities *(include if feature involves data)*

- **Operational Screen**: A user-facing workspace (Login, Dashboard, POS, Inventory, Billing, Reports, Kitchen Display, AI Agent) with render state, interaction state, and workflow entry points.
- **Order Transaction**: A customer order lifecycle record including creation, item updates, finalization state, kitchen status, and payment association.
- **Agent Interaction Request**: A user-submitted Ask or Command input containing intent text, interaction mode, response payload, and execution outcome.
- **Agent Health Snapshot**: A status view describing whether each operational agent is available, degraded, or recovering.
- **LLM Provider Configuration**: Runtime provider selection metadata containing provider name, model identifier, availability state, and fallback policy.

### Assumptions

- Existing authentication role and credentials remain unchanged for this stabilization scope.
- Existing agent architecture and business rules remain unchanged except provider wiring needed for live AI interaction.
- Production readiness for this scope means stable behavior of currently implemented screens and workflows, not introduction of new workflows.
- Verification is performed using representative operational data and can include valid empty-state scenarios where data is absent.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Application launch and initial login complete successfully in at least 95% of 20 consecutive startup attempts.
- **SC-002**: 100% of primary screens load without blank panels during a full navigation pass across all eight screens.
- **SC-003**: 0 blocking runtime crashes occur during three consecutive end-to-end navigation and workflow verification runs.
- **SC-004**: Staff can complete order creation and finalization in POS in under 2 minutes in standard test conditions.
- **SC-005**: Staff can complete a billing payment flow for a finalized order in under 90 seconds in standard test conditions.
- **SC-006**: Kitchen order status updates are reflected in relevant operational views within 5 seconds for 95% of updates.
- **SC-007**: Daily report view returns visible summary output for selected dates in under 5 seconds for 95% of requests.
- **SC-008**: In online mode, at least 90% of Ask-mode AI queries return a meaningful response on first attempt.
- **SC-009**: In online mode, at least 85% of valid Command-mode instructions execute the intended operational workflow on first attempt.
- **SC-010**: AI Agent screen always displays provider/model metadata and agent status indicators during active sessions.
- **SC-011**: In simulated AI-provider outage conditions, 100% of critical non-AI operational workflows remain executable.
- **SC-012**: During outage conditions, 100% of Ask/Command submissions return a user-visible degraded response instead of failing silently.
