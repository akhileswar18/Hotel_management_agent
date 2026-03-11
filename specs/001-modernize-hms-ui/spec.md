# Feature Specification: Modernized HMS UI

**Feature Branch**: `001-modernize-hms-ui`  
**Created**: 2026-03-11  
**Status**: Draft  
**Input**: User description: "Build a modernized Hotel Management System (HMS) UI for small Indian hotels and restaurants. The system is already built and working - this effort is purely a visual and interaction redesign of the existing screens. No backend changes are needed. The users are non-technical hotel staff - waiters, cashiers, kitchen cooks, and a manager. They use this system all day on a desktop browser to take orders, manage inventory, print bills, and view reports. The current UI is plain white and hard to read quickly during a busy service. The goal is a dark-themed, modern interface that reduces errors, speeds up common tasks, and makes critical information instantly visible. The system has 8 screens that need to be redesigned: login, dashboard, POS, inventory, invoice, reports, kitchen display, and AI agent interaction."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Faster Order Taking (Priority: P1)

A waiter or cashier starts a new order during busy service, finds menu items quickly, avoids out-of-stock mistakes, sees totals clearly, and completes hold, resume, discount, payment, or void actions with minimal hesitation.

**Why this priority**: Order entry is the most frequent and revenue-critical workflow. Any delay or confusion here directly slows service and increases billing errors.

**Independent Test**: Can be fully tested by logging in as waiter or cashier, creating a new order, adding items from multiple categories, applying permitted actions, and confirming that out-of-stock items cannot be ordered.

**Acceptance Scenarios**:

1. **Given** a staff member opens the POS screen, **When** they browse or filter menu categories, **Then** menu items are shown as easy-to-scan cards with price and stock state visible at a glance.
2. **Given** an item is out of stock, **When** the user attempts to order it, **Then** the interface prevents the action and makes the unavailable state visually obvious before selection.
3. **Given** a manager or cashier is working on an active order, **When** they open the action area, **Then** discount and void options are visible and clearly separated from standard actions.
4. **Given** a waiter is working on an active order, **When** they open the action area, **Then** discount and void options are not shown.

---

### User Story 2 - Immediate Shift Awareness (Priority: P1)

After login, staff members land on a home screen that gives them immediate awareness of the day: current revenue, active orders, low-stock items, recent activity, and shortcuts to the most common tasks.

**Why this priority**: Staff currently land without context. A high-visibility home screen reduces mode switching and helps managers and frontline staff react faster.

**Independent Test**: Can be fully tested by logging in with a named user, opening the home screen, and confirming that summary cards, quick actions, active orders, and recent activity are visible without scrolling through multiple screens.

**Acceptance Scenarios**:

1. **Given** a staff member has logged in successfully, **When** the home screen loads, **Then** it greets them by name, shows today's date, and presents the defined business summary cards.
2. **Given** there are active orders in different states, **When** the user views the home screen, **Then** active orders are listed with their current status highlighted for quick recognition.
3. **Given** staff need to move quickly between workflows, **When** they use quick actions, **Then** they can reach new order, stock, reports, and kitchen views directly from the home screen.

---

### User Story 3 - Low-Stock and Billing Confidence (Priority: P2)

A manager or cashier can detect stock risk early, inspect stock accountability, preview bills before printing, and reprint recent invoices without leaving the primary workflow.

**Why this priority**: Inventory shortages and billing mistakes have immediate operational and customer impact, but they occur less frequently than order entry.

**Independent Test**: Can be fully tested by opening inventory and billing screens with existing data, confirming low-stock alerts, stock history visibility, payment method selection, change calculation, receipt preview, and invoice reprint access.

**Acceptance Scenarios**:

1. **Given** inventory data includes healthy, low, critical, and out-of-stock items, **When** the manager opens stock management, **Then** urgent items are called out separately and each item row shows a clear visual stock status.
2. **Given** a cashier is finalizing a bill, **When** they select a payment method and enter received amount, **Then** the bill preview updates clearly enough to verify charges before printing.
3. **Given** a customer requests a duplicate bill, **When** the cashier checks recent invoices, **Then** they can identify and reprint the correct invoice from the same screen.

---

### User Story 4 - Kitchen Urgency Handling (Priority: P2)

Kitchen staff view incoming orders as time-sensitive tickets, recognize urgency by color and timer, mark item progress, and mark orders ready without scanning dense text.

**Why this priority**: Kitchen delays create direct guest dissatisfaction, but the kitchen display depends on order data already being available from the main workflow.

**Independent Test**: Can be fully tested by opening the kitchen display with fresh and aged orders, confirming urgency styling changes over time, marking individual items complete, and setting the full order to ready.

**Acceptance Scenarios**:

1. **Given** multiple kitchen orders are active, **When** cooks view the kitchen display, **Then** each order appears as a dedicated ticket card showing table, wait time, and ordered items.
2. **Given** an order has crossed the defined late thresholds, **When** the kitchen display updates, **Then** the ticket styling changes to the correct urgency state and the timer remains highly visible.
3. **Given** a cook completes some items in an order, **When** they mark individual items done, **Then** completed items are visually differentiated while the remaining items stay actionable.

---

### User Story 5 - Transparent AI-Assisted Operations (Priority: P3)

Staff and managers can use the AI interaction screen with confidence because it shows agent health, command mode, clarification prompts, execution trace, and live event activity instead of hiding system behavior behind a simple chat box.

**Why this priority**: This improves trust and auditability for an advanced workflow, but it is less critical than the core operational screens used continuously throughout service.

**Independent Test**: Can be fully tested by opening the AI screen, switching between ask, command, and voice modes, submitting clear and ambiguous requests, and verifying that agent status, execution trace, clarifications, and event activity are shown.

**Acceptance Scenarios**:

1. **Given** a staff member opens the AI interaction screen, **When** the screen loads, **Then** all agents are visible with a live status indicator and the chat area shows the available interaction modes.
2. **Given** the user submits a multi-step command, **When** the system processes it, **Then** the screen shows a step-by-step execution trace of the business actions performed.
3. **Given** a command is ambiguous, **When** the system needs clarification, **Then** the user is presented with explicit selectable options instead of the system guessing.

---

### Edge Cases

- What happens when the system is offline at login or during service? The interface must continue to show an offline-ready state and avoid suggesting that internet access is required for normal operation.
- What happens when there are no active orders, no recent invoices, or no recent activity? Each affected panel must show an intentional empty state rather than a blank area.
- How does the system handle very long item names, large order totals, or many line items? The layout must preserve readability without truncating critical values such as item identity, quantity, total amount, or status.
- How does the system handle multiple urgent kitchen tickets at once? Urgent tickets must remain distinguishable without requiring users to open each one.
- How does the system handle ambiguous AI commands? It must request clarification with explicit options before committing an action.
- How does the system handle a user opening screens they are not permitted to act on? Restricted actions must remain hidden or non-actionable while still preserving necessary visibility for their role.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The redesigned interface MUST preserve all existing business workflows, calculations, and data behavior without requiring backend changes.
- **FR-002**: The redesigned interface MUST use a consistent dark visual theme across all eight target screens.
- **FR-003**: The redesigned interface MUST use a consistent visual language for normal, warning, urgent, success, and unavailable states across all screens.
- **FR-004**: All primary interactive controls MUST remain readable and usable by staff working while standing at a service counter.
- **FR-005**: The login screen MUST display a branded identity area, role selection options for Waiter, Cashier, Manager, Kitchen, Clerk, and Admin, masked PIN feedback, and an always-visible offline-ready indicator.
- **FR-006**: The login screen MUST make the currently selected role visually distinct before PIN entry is completed.
- **FR-007**: After successful login, users MUST land on a dashboard or home screen instead of being sent directly to order entry.
- **FR-008**: The dashboard MUST show the logged-in staff member's name, the current date, daily revenue, order count, low-stock item count, and average order value.
- **FR-009**: The dashboard MUST provide quick actions for new order, add stock, reports, and kitchen view.
- **FR-010**: The dashboard MUST show active orders by table with visible status labels for pending, cooking, ready, and late states.
- **FR-011**: The dashboard MUST show recent activity and a payment method breakdown in a format that can be interpreted at a glance.
- **FR-012**: The POS screen MUST present menu items as a visual grid of cards that shows item name, price, and current stock state.
- **FR-013**: The POS screen MUST provide category-based filtering so staff can narrow the visible menu rapidly during service.
- **FR-014**: The POS screen MUST show the current order summary in a dedicated side panel with running total, discount, and tax information clearly separated from item browsing.
- **FR-015**: The POS screen MUST provide hold order, resume held order, finalize or pay, and other relevant order actions in a dedicated action area.
- **FR-016**: The POS screen MUST prevent users from adding out-of-stock items to an order.
- **FR-017**: Discount and void actions MUST only be visible to roles authorized to perform them, specifically Managers and Cashiers.
- **FR-018**: The inventory screen MUST display urgent stock items in a persistent alert area separate from the full inventory list.
- **FR-019**: The inventory screen MUST show each inventory item with a stock status badge and a visual quantity indicator that communicates healthy, low, critical, or out states.
- **FR-020**: The inventory screen MUST include a stock ledger view showing who changed stock, when it changed, and by how much.
- **FR-021**: The billing screen MUST provide selectable payment methods, entry of amount received, and automatic display of change due when applicable.
- **FR-022**: The billing screen MUST show a live receipt preview with hotel identity, receipt reference, itemized charges, tax breakdown, and total before print confirmation.
- **FR-023**: The billing screen MUST include access to recent invoices and support reprint from the same workspace.
- **FR-024**: The reports screen MUST show hourly revenue comparison for today versus yesterday, payment breakdown, top-selling items, and inventory snapshot summary for the selected date.
- **FR-025**: The reports screen MUST allow users to change the reporting date and export both sales data and inventory data.
- **FR-026**: The kitchen display MUST show active orders as ticket-style cards with table identifier, elapsed or remaining time indicator, and item list.
- **FR-027**: The kitchen display MUST visibly differentiate fresh, warning, and late orders using urgency styling tied to wait time.
- **FR-028**: The kitchen display MUST allow staff to mark individual items as done and whole orders as ready.
- **FR-029**: The kitchen display MUST show aggregate kitchen status metrics including urgent order count, in-progress count, ready count, and average preparation time for the day.
- **FR-030**: The AI interaction screen MUST display agent health or availability status for all visible agents.
- **FR-031**: The AI interaction screen MUST support ask, command, and voice interaction modes as distinct user-selectable modes.
- **FR-032**: The AI interaction screen MUST show a step-by-step execution trace after each AI-driven command so staff can see which actions were performed.
- **FR-033**: The AI interaction screen MUST present explicit clarification options when a command cannot be resolved confidently.
- **FR-034**: The AI interaction screen MUST display a live event activity stream that allows staff or managers to audit what happened and when.
- **FR-035**: Empty, loading, warning, and error states across all redesigned screens MUST be intentional, readable, and visually consistent with the overall interface.
- **FR-036**: The redesign MUST maintain touch-friendly control sizing for staff using the application in fast-paced operational settings.

### Key Entities *(include if feature involves data)*

- **Staff Session**: Represents the logged-in user context, including displayed name, selected role, and permitted actions in the interface.
- **Dashboard Summary**: Represents the at-a-glance operational metrics shown after login, including current revenue, order volume, average order value, low-stock count, and recent activity.
- **Order Ticket**: Represents an active guest order as displayed in POS, dashboard, billing, and kitchen views, including table identifier, order status, line items, totals, and wait-time state.
- **Menu Item Status**: Represents the sellable state of a menu item in ordering views, including name, price, category, and stock availability signal.
- **Inventory Record**: Represents a tracked stock item with current quantity state, urgency level, and accountability history.
- **Invoice Summary**: Represents a finalized bill, including receipt reference, line items, payment method, tax breakdown, total amount, and reprint eligibility.
- **Agent Activity**: Represents visible AI workflow status, including agent health, interaction mode, execution trace steps, clarification prompts, and event activity.

## Assumptions

- The redesign applies only to the existing user interface and interaction layer; business rules, data structures, roles, and backend integrations remain unchanged.
- Existing role permissions are already defined by the current system, and this feature only changes how those permissions are surfaced visually.
- Existing reporting, inventory, billing, and AI data are already available and accurate enough to populate the redesigned screens.
- The primary usage context is desktop browser operation in hotel or restaurant service areas, with staff often reading the screen from arm's length rather than seated close to the monitor.
- All eight screens must feel like one coherent product, even though different roles will use different subsets of the interface.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In moderated usability testing, at least 90% of staff participants can log in with their role and PIN without guidance in 20 seconds or less.
- **SC-002**: In moderated usability testing, at least 90% of waiter and cashier participants can add a standard order of three items and reach the payment-ready state in 45 seconds or less.
- **SC-003**: At least 95% of test participants can correctly identify low-stock inventory items and late kitchen orders within 5 seconds of those screens loading.
- **SC-004**: At least 90% of cashier participants can verify a bill and confirm the correct payment method without printing a test receipt first.
- **SC-005**: At least 90% of manager participants can identify today's revenue, order count, low-stock count, and payment mix within 15 seconds of reaching the dashboard or reports view.
- **SC-006**: At least 85% of staff participants report that the redesigned interface is easier to read and faster to operate than the current interface in post-test feedback.
