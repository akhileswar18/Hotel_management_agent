# Tasks: Modernized HMS UI

**Input**: Design documents from `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\`
**Prerequisites**: `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\plan.md`, `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\spec.md`, `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\research.md`, `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\data-model.md`, `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\contracts\backend-api.md`, `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\contracts\ui-workflows.md`

**Tests**: No story-level TDD tasks were generated because the specification does not require test-first delivery. Manual independent-test checkpoints are included per story, and final regression tasks cover `tests/`.

**Organization**: Tasks are grouped by user story so each story remains independently implementable and testable once the shared foundation is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: User story label for story-specific phases only
- Every task includes exact file paths

## Phase 1: Setup (Shared Context)

**Purpose**: Establish the visual references and baseline runtime used by every implementation phase.

- [X] T001 Review screenshot mappings in `C:\Users\akhil\Hotel_management_agent\.specify\screens\README.md` and confirm the target assets in `C:\Users\akhil\Hotel_management_agent\.specify\screens\current\` and `C:\Users\akhil\Hotel_management_agent\.specify\screens\target\`
- [X] T002 Smoke-run the baseline app from `C:\Users\akhil\Hotel_management_agent\src\launcher.py` and capture any pre-existing UI/runtime issues against `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared backend and shell work that MUST be complete before any user story can be finished.

**⚠️ CRITICAL**: No user story is complete until this phase is done.

- [X] T003 Replace HMS color tokens and add shared builders in `C:\Users\akhil\Hotel_management_agent\src\ui\components\ui_helpers.py`
- [X] T004 Create the additive `kitchen_status` migration in `C:\Users\akhil\Hotel_management_agent\migrations\005_add_kitchen_status.sql`
- [X] T005 [P] Add audit-log normalization and `GET /api/audit/log` in `C:\Users\akhil\Hotel_management_agent\src\api\app.py`
- [X] T006 Add `kitchen_status` request/response support and `PATCH /api/sales/orders/{order_id}/kitchen-status` in `C:\Users\akhil\Hotel_management_agent\src\api\app.py`
- [X] T007 [P] Replace the current shell with the dark theme, custom sidebar, shared header wiring, and dashboard-first routing in `C:\Users\akhil\Hotel_management_agent\src\ui\app.py`

**Checkpoint**: Shared design system, minimal backend additions, and app shell are ready for story work.

---

## Phase 3: User Story 1 - Faster Order Taking (Priority: P1) 🎯 MVP

**Goal**: Give waiters and cashiers a faster, clearer POS flow that prevents stock mistakes and preserves current order-entry behavior.

**Independent Test**: Log in as waiter or cashier, open POS, filter categories, add multiple items, verify out-of-stock items are blocked, and complete hold/resume/finalize using the existing handlers and shortcuts.

- [X] T008 [US1] Rebuild the POS toolbar, search area, and layout split to match `C:\Users\akhil\Hotel_management_agent\.specify\screens\current\02_pos.png` and `C:\Users\akhil\Hotel_management_agent\.specify\screens\target\03_pos.png` in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\pos_screen.py`
- [X] T009 [US1] Implement the three-column menu card grid, category tabs, and stock-state visuals in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\pos_screen.py`
- [X] T010 [US1] Update the order summary panel, role-based action visibility, and preserved keyboard shortcuts in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\pos_screen.py`

**Checkpoint**: User Story 1 is complete when POS is visually redesigned and still supports end-to-end ordering independently of other story screens.

---

## Phase 4: User Story 2 - Immediate Shift Awareness (Priority: P1)

**Goal**: Move staff to a dashboard-first experience with at-a-glance operational awareness, improved login confidence, and clearer daily analytics.

**Independent Test**: Log in successfully, land on the dashboard, verify greeting/date/summary cards/quick actions/activity feed, then open reports and confirm the visual summaries render without breaking the shell.

- [X] T011 [US2] Create the dashboard screen shell with greeting, stat cards, quick actions, active orders, and sidebar panels in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\dashboard_screen.py`
- [X] T012 [US2] Implement dashboard data loading, fallback values, quick-action navigation, and activity/payment rendering in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\dashboard_screen.py`
- [X] T013 [P] [US2] Redesign the login experience with branding, role chips, offline badge, and animated PIN dots in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\auth_screen.py`
- [X] T014 [P] [US2] Rework the reports screen into the target analytics layout with summary cards, chart primitives, ranking rows, and export controls in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\reports_screen.py`

**Checkpoint**: User Story 2 is complete when staff can log in to a polished dashboard, see shift awareness data immediately, and open the redesigned reports view independently.

---

## Phase 5: User Story 3 - Low-Stock and Billing Confidence (Priority: P2)

**Goal**: Make low-stock risk and cashier billing verification obvious without requiring users to leave their current workflow.

**Independent Test**: Open inventory and billing screens with existing data, verify alert/sidebar emphasis, stock bars, ledger visibility, payment-method selection, receipt preview, change calculation, and invoice reprint access.

- [X] T015 [P] [US3] Redesign the inventory sidebar, alert cards, category list, and snapshot tiles using `C:\Users\akhil\Hotel_management_agent\.specify\screens\current\03_menu_management.png` and `C:\Users\akhil\Hotel_management_agent\.specify\screens\target\04_inventory.png` in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\products_screen.py`
- [X] T016 [US3] Add stock-bar rendering, status badges, searchable item rows, and ledger history presentation in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\products_screen.py`
- [X] T017 [P] [US3] Rebuild the billing workspace with payment cards, amount-received flow, change calculation, and receipt preview using `C:\Users\akhil\Hotel_management_agent\.specify\screens\target\05_invoice.png` in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\receipt_screen.py`
- [X] T018 [US3] Add recent invoice rows, reprint affordances, and finalized/void status styling in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\receipt_screen.py`

**Checkpoint**: User Story 3 is complete when managers and cashiers can use inventory and billing screens confidently without relying on the old text-heavy layouts.

---

## Phase 6: User Story 4 - Kitchen Urgency Handling (Priority: P2)

**Goal**: Give kitchen staff a true ticket-based KDS that surfaces urgency, supports progress tracking, and persists kitchen progression.

**Independent Test**: Open the kitchen display with active orders, confirm ticket-card rendering and timer color shifts, mark item progress, and mark an order ready using the `kitchen_status` endpoint.

- [ ] T019 [US4] Repurpose the order-history screen into the fullscreen kitchen display shell using `C:\Users\akhil\Hotel_management_agent\.specify\screens\current\06_kitchen_queue.png` and `C:\Users\akhil\Hotel_management_agent\.specify\screens\target\07_kitchen.png` in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\order_history_screen.py`
- [ ] T020 [US4] Implement urgency timers, ticket styling, item-complete interactions, stats bar, and `kitchen_status` updates in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\order_history_screen.py`

**Checkpoint**: User Story 4 is complete when kitchen staff can work entirely from the redesigned KDS and see urgency states update independently.

---

## Phase 7: User Story 5 - Transparent AI-Assisted Operations (Priority: P3)

**Goal**: Make AI-assisted workflows observable and trustworthy through agent status, command traces, clarification chips, and live activity visibility.

**Independent Test**: Open the AI screen, switch modes, submit command and question flows, verify the three-panel layout, pipeline trace expansion, clarification chips, and event-feed updates.

- [X] T021 [US5] Redesign the chat screen into the left/center/right AI workspace using `C:\Users\akhil\Hotel_management_agent\.specify\screens\target\08_ai_agent.png` in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\chat_screen.py`
- [X] T022 [US5] Add agent status rows, pipeline trace rendering, ambiguity chips, and periodic audit-log refresh behavior in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\chat_screen.py`

**Checkpoint**: User Story 5 is complete when AI-driven interactions are observable without changing the existing command endpoints.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Finish the redesign cleanly across all touched screens and validate the full application behavior.

- [ ] T023 [P] Normalize empty, loading, offline, and error states across `C:\Users\akhil\Hotel_management_agent\src\ui\screens\auth_screen.py`, `C:\Users\akhil\Hotel_management_agent\src\ui\screens\dashboard_screen.py`, `C:\Users\akhil\Hotel_management_agent\src\ui\screens\pos_screen.py`, `C:\Users\akhil\Hotel_management_agent\src\ui\screens\products_screen.py`, `C:\Users\akhil\Hotel_management_agent\src\ui\screens\receipt_screen.py`, `C:\Users\akhil\Hotel_management_agent\src\ui\screens\reports_screen.py`, `C:\Users\akhil\Hotel_management_agent\src\ui\screens\order_history_screen.py`, and `C:\Users\akhil\Hotel_management_agent\src\ui\screens\chat_screen.py`
- [ ] T024 [P] Verify 48px minimum touch targets, shared header usage, and dark-theme consistency in `C:\Users\akhil\Hotel_management_agent\src\ui\app.py` and `C:\Users\akhil\Hotel_management_agent\src\ui\components\ui_helpers.py`
- [ ] T025 Re-run the manual validation sequence from `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\quickstart.md` using `C:\Users\akhil\Hotel_management_agent\src\launcher.py`
- [ ] T026 Run the regression suite under `C:\Users\akhil\Hotel_management_agent\tests\` and resolve any resulting failures in touched UI/API files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup** has no dependencies and starts immediately.
- **Phase 2: Foundational** depends on Phase 1 and blocks every story phase.
- **Phase 3: US1** depends on Phase 2 only.
- **Phase 4: US2** depends on Phase 2 only.
- **Phase 5: US3** depends on Phase 2 only.
- **Phase 6: US4** depends on Phase 2, especially `T004` and `T006` for persisted `kitchen_status`.
- **Phase 7: US5** depends on Phase 2, especially `T005` for the audit-log feed.
- **Phase 8: Polish** depends on all desired story phases being complete.

### User Story Completion Order

1. **US1 - Faster Order Taking**: MVP and highest-value delivery slice
2. **US2 - Immediate Shift Awareness**
3. **US3 - Low-Stock and Billing Confidence**
4. **US4 - Kitchen Urgency Handling**
5. **US5 - Transparent AI-Assisted Operations**

### Dependency Graph

- **US1**: Starts after `T003` and `T007`
- **US2**: Starts after `T003`, `T005`, `T006`, and `T007`
- **US3**: Starts after `T003` and `T007`
- **US4**: Starts after `T004`, `T006`, and `T007`
- **US5**: Starts after `T005`, `T007`, and `T003`

---

## Parallel Opportunities

- `T005` and `T007` can run in parallel after `T003`, while `T004` prepares the schema update needed by `T006`.
- Within **US2**, `T013` and `T014` can run in parallel once `T011` and `T012` define the dashboard target behavior.
- Within **US3**, `T015` and `T017` can run in parallel because they touch different files.
- `T023` and `T024` can run in parallel during polish.

---

## Parallel Example: User Story 2

```text
Task A: T013 [US2] in C:\Users\akhil\Hotel_management_agent\src\ui\screens\auth_screen.py
Task B: T014 [US2] in C:\Users\akhil\Hotel_management_agent\src\ui\screens\reports_screen.py
```

## Parallel Example: User Story 3

```text
Task A: T015 [US3] in C:\Users\akhil\Hotel_management_agent\src\ui\screens\products_screen.py
Task B: T017 [US3] in C:\Users\akhil\Hotel_management_agent\src\ui\screens\receipt_screen.py
```

## Parallel Example: Polish Phase

```text
Task A: T023 across the touched files in C:\Users\akhil\Hotel_management_agent\src\ui\screens\
Task B: T024 in C:\Users\akhil\Hotel_management_agent\src\ui\app.py and C:\Users\akhil\Hotel_management_agent\src\ui\components\ui_helpers.py
```

---

## Implementation Strategy

### MVP First

1. Complete **Phase 1: Setup**
2. Complete **Phase 2: Foundational**
3. Complete **Phase 3: US1**
4. Validate US1 independently through the POS workflow in `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\quickstart.md`

### Incremental Delivery

1. Deliver **US1** first for immediate service-speed gains
2. Add **US2** for dashboard-first operations and login confidence
3. Add **US3** for inventory and billing confidence
4. Add **US4** for kitchen urgency handling
5. Add **US5** for AI transparency
6. Finish with **Phase 8** regression and polish

### Independent Test Criteria by Story

- **US1**: POS supports category filtering, out-of-stock protection, role-aware actions, and finalize/hold/resume flows
- **US2**: Login redirects to dashboard, dashboard shows summary/quick actions/activity, and reports render visually
- **US3**: Inventory shows low-stock urgency and billing shows payment selection plus receipt preview
- **US4**: Kitchen tickets show urgency timers and persist readiness via `kitchen_status`
- **US5**: AI screen shows agent health, pipeline trace, clarification chips, and live activity feed

---

## Notes

- All tasks use the required checklist format: checkbox, task ID, optional `[P]`, required `[US#]` for story phases, and exact file paths.
- No story-level test-first tasks were created because TDD was not explicitly requested in the feature specification.
- The recommended MVP scope is **US1 only** after Setup and Foundational phases.
