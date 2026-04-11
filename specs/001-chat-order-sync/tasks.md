# Tasks: Chat Order Real-Time Sync

**Input**: Design documents from `/specs/001-chat-order-sync/`
**Prerequisites**: [plan.md](C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/plan.md), [spec.md](C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/spec.md), [research.md](C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/research.md), [data-model.md](C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/data-model.md), [contracts/order-change-notification.md](C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/contracts/order-change-notification.md), [quickstart.md](C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/quickstart.md)

**Tests**: Manual runtime verification is required in every phase. No new automated test tasks are included because the feature specification did not request TDD or new automated coverage.

**Organization**: Tasks are grouped by verify-first setup, shared infrastructure, and user story phases so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`)
- Every task includes an exact file path

## Path Conventions

- Single project layout under `src/` and `tests/`
- Feature docs live under `specs/001-chat-order-sync/`

## Phase 0: Runtime Verification Only

**Purpose**: Confirm actual runtime behavior before any code changes.

- [X] T001 Run the baseline verify-first flow from C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/quickstart.md and record current Chat Command -> KDS behavior in C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/research.md
- [X] T002 Verify whether C:/Users/akhil/Hotel_management_agent/src/ui/screens/receipt_screen.py exposes any external refresh entry point and document the actual draft/recent refresh methods in C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/research.md
- [X] T003 Verify whether the installed Flet runtime exposes `page.pubsub` and reconcile that result against C:/Users/akhil/Hotel_management_agent/requirements.txt and C:/Users/akhil/Hotel_management_agent/AGENTS.md in C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/research.md
- [X] T004 Audit screen construction timing in C:/Users/akhil/Hotel_management_agent/src/ui/app.py and document whether KDS and Billing are created eagerly or lazily in C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/research.md

**Checkpoint**: Runtime findings are documented and no implementation assumptions remain unverified.

---

## Phase 1: Shared Registry Infrastructure

**Purpose**: Add the minimal shared notification mechanism that all screens will use.

- [X] T005 Implement `register_order_listener`, `unregister_order_listener`, and `notify_order_change` in C:/Users/akhil/Hotel_management_agent/src/ui/app.py following C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/contracts/order-change-notification.md
- [X] T006 Add the app-shell wiring needed for registry access and no-op safety in C:/Users/akhil/Hotel_management_agent/src/ui/app.py so notifications do not fail when no listener is registered
- [X] T007 Manually smoke-verify `notify_order_change` no-op and active-listener behavior through C:/Users/akhil/Hotel_management_agent/src/ui/app.py and capture the verification steps in C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/quickstart.md

**Checkpoint**: Shared registry exists, does not crash with zero listeners, and is ready for screen-specific adoption.

---

## Phase 2: User Story 1 - See Chat Orders in Kitchen Immediately (Priority: P1) 🎯 MVP

**Goal**: Ensure already-open KDS screens refresh immediately when notified of successful order changes.

**Independent Test**: Open KDS, trigger `notify_order_change`, and confirm the kitchen grid refreshes without waiting for the 30-second timer or manual navigation.

### Implementation for User Story 1

- [X] T008 [P] [US1] Update the KDS refresh adapter in C:/Users/akhil/Hotel_management_agent/src/ui/screens/order_history_screen.py so `notify_external_update` cleanly accepts registry event payloads and remains idempotent
- [X] T009 [US1] Register the KDS listener during screen initialization in C:/Users/akhil/Hotel_management_agent/src/ui/screens/order_history_screen.py using the shared registry from C:/Users/akhil/Hotel_management_agent/src/ui/app.py
- [X] T010 [US1] Unregister the KDS listener during cleanup in C:/Users/akhil/Hotel_management_agent/src/ui/screens/order_history_screen.py so closed screens do not retain stale callbacks
- [ ] T011 [US1] Manually invoke `notify_order_change` with KDS open and document the KDS listener verification steps in C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/quickstart.md

**Checkpoint**: KDS can subscribe, unsubscribe, and refresh immediately from the shared registry on its own.

---

## Phase 3: User Story 2 - See Chat Orders in Billing Immediately (Priority: P1)

**Goal**: Ensure already-open Billing screens refresh draft and recent order data based on order event type.

**Independent Test**: Open Billing, trigger `notify_order_change`, and confirm draft orders refresh for `order.created` and `order.updated`, while both drafts and recents refresh for `order.finalized` and `order.voided`.

### Implementation for User Story 2

- [X] T012 [P] [US2] Implement `notify_external_update` in C:/Users/akhil/Hotel_management_agent/src/ui/screens/receipt_screen.py so `order.created` and `order.updated` refresh drafts, while `order.finalized` and `order.voided` refresh both drafts and recents using the Phase 0-verified load methods
- [X] T013 [US2] Register the Billing listener during screen initialization in C:/Users/akhil/Hotel_management_agent/src/ui/screens/receipt_screen.py using the shared registry from C:/Users/akhil/Hotel_management_agent/src/ui/app.py
- [X] T014 [US2] Add safe listener cleanup or unregister behavior in C:/Users/akhil/Hotel_management_agent/src/ui/screens/receipt_screen.py so Billing callbacks are removed when the screen is torn down
- [ ] T015 [US2] Manually invoke `notify_order_change` with Billing open and document the Billing listener verification steps in C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/quickstart.md

**Checkpoint**: Billing can subscribe, unsubscribe, and refresh the correct UI sections based on event type.

---

## Phase 4: User Story 3 - Keep Active Screens in Sync Without Interrupting Work (Order Confirmation Flow) (Priority: P2)

**Goal**: Broadcast order creation from the parse-confirm flow without blocking the caller or breaking the existing return flow.

**Independent Test**: Complete the Chat Order parse-confirm flow with KDS and Billing open and confirm both views update within 2 seconds while the confirmation screen still returns normally.

### Implementation for User Story 3

- [X] T016 [P] [US3] Accept and store an `on_order_change` callback in C:/Users/akhil/Hotel_management_agent/src/ui/screens/order_confirmation_screen.py without removing existing screen behavior
- [X] T017 [US3] Emit `order.created` after successful `POST /api/orders/from-intent` in C:/Users/akhil/Hotel_management_agent/src/ui/screens/order_confirmation_screen.py before calling `on_back()`
- [X] T018 [US3] Wire the `on_order_change` callback into the Order Confirmation screen creation path in C:/Users/akhil/Hotel_management_agent/src/ui/app.py so it routes through `notify_order_change`
- [ ] T019 [US3] Verify the Chat Order parse-confirm end-to-end flow against KDS and Billing and document the result in C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/quickstart.md

**Checkpoint**: Parse-confirm order creation updates open KDS and Billing views without interrupting navigation.

---

## Phase 5: User Story 3 - Keep Active Screens in Sync Without Interrupting Work (Chat Command Flow) (Priority: P2)

**Goal**: Broadcast chat command order changes with correct event mapping while preserving backward compatibility.

**Independent Test**: Use Chat Command mode with KDS and Billing open and confirm `create_order`, `finalize_order`, `void_order`, and `add_item` actions emit the expected event types and refresh open views within 2 seconds.

### Implementation for User Story 3

- [X] T020 [P] [US3] Accept and store an `on_order_change` callback in C:/Users/akhil/Hotel_management_agent/src/ui/screens/chat_screen.py while keeping the existing `on_kitchen_update` callback and `_emit_kitchen_update()` path for backward compatibility
- [X] T021 [US3] Map `create_order` -> `order.created`, `finalize_order` -> `order.finalized`, `void_order` -> `order.voided`, and `add_item` -> `order.updated` in C:/Users/akhil/Hotel_management_agent/src/ui/screens/chat_screen.py and emit those events after successful API responses
- [X] T022 [US3] Wire the `on_order_change` callback into the Chat screen constructor in C:/Users/akhil/Hotel_management_agent/src/ui/app.py so Chat Command mode routes through `notify_order_change`
- [ ] T023 [US3] Verify Chat Command end-to-end updates for KDS and Billing and document the action-to-event mapping checks in C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/quickstart.md

**Checkpoint**: Chat Command mode broadcasts the right event types, keeps KDS backward compatibility, and updates both target screens.

---

## Phase 6: User Story 3 - Keep Active Screens in Sync Without Interrupting Work (Optional POS Broadcaster) (Priority: P2)

**Goal**: Extend the shared broadcaster mechanism to POS for consistency, while keeping it optional for MVP.

**Independent Test**: With KDS and Billing open, create or change an order from POS and confirm both views update through the shared registry without breaking existing kitchen update behavior.

### Implementation for User Story 3

- [X] T024 [P] [US3] Accept and store an `on_order_change` callback in C:/Users/akhil/Hotel_management_agent/src/ui/screens/pos_screen.py while preserving the existing `on_kitchen_update` and `_emit_kitchen_update()` compatibility path
- [X] T025 [US3] Emit `order.created`, `order.finalized`, `order.voided`, and `order.updated` from the successful POS API paths in C:/Users/akhil/Hotel_management_agent/src/ui/screens/pos_screen.py
- [X] T026 [US3] Wire the `on_order_change` callback into the POS screen constructor in C:/Users/akhil/Hotel_management_agent/src/ui/app.py so POS routes through `notify_order_change`
- [ ] T027 [US3] Verify optional POS end-to-end updates for KDS and Billing and record the MVP-optional status in C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/quickstart.md

**Checkpoint**: POS can participate in the shared sync mechanism, but the feature is already MVP-ready before this phase.

---

## Phase 7: Polish & Cross-Cutting Regression

**Purpose**: Validate the full matrix, resilience, and required documentation updates across all stories.

- [ ] T028 Run the regression matrix for Chat Order, Chat Command, and POS against both KDS and Billing using C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/quickstart.md and record final results there
- [ ] T029 Exercise edge cases for unopened screens, listener error resilience, rapid-fire commands, and full screen navigation regression using C:/Users/akhil/Hotel_management_agent/src/ui/app.py and record the outcomes in C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/quickstart.md
- [X] T030 Update troubleshooting notes for this fix in C:/Users/akhil/Hotel_management_agent/SKILLS.md with error, root cause, fix, files touched, and prevention guidance

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 0**: Starts immediately and must finish before any code changes.
- **Phase 1**: Depends on Phase 0 findings and blocks all story work.
- **Phase 2 (US1)**: Depends on Phase 1.
- **Phase 3 (US2)**: Depends on Phase 1.
- **Phase 4 (US3 Order Confirmation)**: Depends on Phase 1 and is most useful after US1 and US2 listeners exist.
- **Phase 5 (US3 Chat Command)**: Depends on Phase 1 and is most useful after US1 and US2 listeners exist.
- **Phase 6 (US3 POS optional)**: Depends on Phase 1 and can be deferred until after MVP.
- **Phase 7**: Depends on all implemented phases that are in scope for the release.

### User Story Dependencies

- **US1**: Can start after the shared registry is in place; no dependency on US2 or US3.
- **US2**: Can start after the shared registry is in place; no dependency on US1 or US3.
- **US3**: Depends on the shared registry and becomes end-to-end valuable once at least one listener story is complete.
- **Optional POS work**: Part of US3 consistency, but not required for MVP.

### Recommended Completion Order

1. Phase 0 -> Phase 1
2. Phase 2 (US1) and Phase 3 (US2)
3. Phase 4 (US3 Order Confirmation) and Phase 5 (US3 Chat Command)
4. **MVP checkpoint**: Stop after Phase 5 if POS consistency is out of scope
5. Phase 6 (optional POS)
6. Phase 7 regression and documentation

## Parallel Opportunities

- After Phase 1, Phase 2 (US1 KDS listener) and Phase 3 (US2 Billing listener) can be implemented in parallel because they touch different screen files.
- After Phase 1, the file-scoped callback additions in Phase 4, Phase 5, and optional Phase 6 can begin in parallel before `app.py` constructor wiring is merged.
- Phase 7 regression can split the verification matrix by order path once implementation is complete.

## Parallel Example: User Story 1

```text
Task: T008 [US1] Update the KDS refresh adapter in src/ui/screens/order_history_screen.py
Task: T012 [US2] Implement Billing notify_external_update in src/ui/screens/receipt_screen.py
```

## Parallel Example: User Story 3

```text
Task: T016 [US3] Accept on_order_change in src/ui/screens/order_confirmation_screen.py
Task: T020 [US3] Accept on_order_change in src/ui/screens/chat_screen.py
Task: T024 [US3] Accept on_order_change in src/ui/screens/pos_screen.py
```

## Implementation Strategy

### MVP First

1. Complete Phase 0 runtime verification.
2. Complete Phase 1 shared registry infrastructure.
3. Complete Phase 2 (US1 KDS listener).
4. Complete Phase 3 (US2 Billing listener).
5. Complete Phase 4 and Phase 5 for the two chat-originated broadcaster paths.
6. Validate the MVP with the end-to-end scenarios in C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/quickstart.md.

### Incremental Delivery

1. Deliver the registry base first.
2. Deliver KDS and Billing listeners as independently testable increments.
3. Add the parse-confirm broadcaster.
4. Add the Chat Command broadcaster.
5. Add POS consistency only if the MVP is already stable.

### Notes

- All tasks follow the required checklist format.
- `[P]` is used only where the task can be executed independently in a different file.
- Manual verification is required at the end of each functional phase because the feature’s primary risk is “fix written but never applied.”
