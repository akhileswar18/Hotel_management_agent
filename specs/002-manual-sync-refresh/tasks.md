# Tasks: Manual Sync / Refresh Button

**Input**: Design documents from `/specs/002-manual-sync-refresh/`  
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in the feature specification. Smoke/manual testing per quickstart.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root

---

## Phase 1: Foundational (Blocking Prerequisite)

**Purpose**: Create the reusable `RefreshButton` component that ALL user stories depend on

**CRITICAL**: No screen-level work can begin until this phase is complete

- [x] T001 Create `RefreshButton` class in `src/ui/components/ui_helpers.py` — a reusable `ft.Container` using `ft.Stack` with `ft.IconButton(icon=ft.icons.REFRESH)` and `ft.ProgressRing(visible=False)`, accepting `on_refresh: Callable`, `page: ft.Page`, and `tooltip: str = "Refresh data"` parameters
- [x] T002 Implement debounce logic in `RefreshButton` in `src/ui/components/ui_helpers.py` — store `_last_refresh_time` as `float`, ignore taps within `DEBOUNCE_SECONDS = 2.0` using `time.time()` comparison
- [x] T003 Implement loading state toggle in `RefreshButton` in `src/ui/components/ui_helpers.py` — on tap: hide icon / show `ProgressRing` / disable button; on complete (success or error): restore icon / hide spinner / re-enable button using `try/finally`
- [x] T004 Implement success/error toast feedback in `RefreshButton` in `src/ui/components/ui_helpers.py` — on success call `show_success_toast(page, "Data refreshed")`; on `httpx.ConnectError` call `show_error_toast(page, "Could not refresh — server unavailable")`; on `httpx.TimeoutException` call `show_error_toast(page, "Refresh timed out — try again")`; on other exceptions call `show_error_toast(page, f"Refresh failed: {error}")`

**Checkpoint**: `RefreshButton` component complete — can be imported and used by any screen. Verify by instantiating in a test script.

---

## Phase 2: User Story 1 — Refresh Data on POS Screen (Priority: P1)

**Goal**: Cashier/waiter can tap Refresh on the POS screen to reload menu items and stock levels without losing their current draft order.

**Independent Test**: Add a new product via the Products screen, switch to POS, observe it's missing, press Refresh, confirm it now appears — draft order stays intact.

### Implementation for User Story 1

- [x] T005 [US1] Import `RefreshButton` from `src/ui/components/ui_helpers.py` in `src/ui/screens/pos_screen.py`
- [x] T006 [US1] Instantiate `RefreshButton(on_refresh=self._load_items, page=self._page)` in `src/ui/screens/pos_screen.py` and add it to the top header `ft.Row` (right-aligned, after existing buttons)
- [x] T007 [US1] Verify `_load_items()` in `src/ui/screens/pos_screen.py` does NOT reset `self.current_order`, `self.current_order_items`, or `self.table_id_field.value` — read method and confirm state preservation

**Checkpoint**: POS screen has a working Refresh button. Draft orders are preserved after refresh.

---

## Phase 3: User Story 2 — Refresh Data on Products/Inventory Screen (Priority: P1)

**Goal**: Manager can tap Refresh on the Products screen to reload all product listings, stock counts, and categories while preserving the active category filter.

**Independent Test**: Record a stock-in via the API, press Refresh on the Products screen, verify updated stock count. Confirm category filter is preserved.

### Implementation for User Story 2

- [x] T008 [P] [US2] Import `RefreshButton` from `src/ui/components/ui_helpers.py` in `src/ui/screens/products_screen.py`
- [x] T009 [US2] Create a refresh callback wrapper in `src/ui/screens/products_screen.py` that calls `self._load_items(self.category_filter.value)` to pass the current filter value
- [x] T010 [US2] Instantiate `RefreshButton(on_refresh=<wrapper>, page=self._page)` in `src/ui/screens/products_screen.py` and add it to the top header `ft.Row` (right-aligned, after existing action buttons)

**Checkpoint**: Products screen has a working Refresh button. Category filter is preserved after refresh.

---

## Phase 4: User Story 3 — Refresh Data on Reports Screen (Priority: P2)

**Goal**: Manager can tap Refresh on the Reports screen to reload daily sales, transactions, and inventory snapshot while preserving date and filter selections.

**Independent Test**: Finalize an order, switch to Reports, press Refresh, verify the new transaction appears in the summary. Confirm selected date filter is preserved.

### Implementation for User Story 3

- [x] T011 [P] [US3] Import `RefreshButton` from `src/ui/components/ui_helpers.py` in `src/ui/screens/reports_screen.py`
- [x] T012 [US3] Remove the existing ad-hoc `refresh_button` (`ft.IconButton`) and `_handle_refresh()` method from `src/ui/screens/reports_screen.py`
- [x] T013 [US3] Instantiate `RefreshButton(on_refresh=self._load_reports, page=self._page)` in `src/ui/screens/reports_screen.py` and place it in the same top header `ft.Row` position where the old refresh button was
- [x] T014 [US3] Verify `_load_reports()` in `src/ui/screens/reports_screen.py` reads `self._selected_date` and transaction filter values without clearing them — confirm state preservation

**Checkpoint**: Reports screen uses the standardized RefreshButton. Date/filter selections preserved after refresh.

---

## Phase 5: User Story 4 — Refresh Data on Order History Screen (Priority: P2)

**Goal**: Staff member can tap Refresh on Order History to see latest orders while preserving status and date filters.

**Independent Test**: Finalize a new order, press Refresh on Order History, confirm the new order appears. Verify status/date filters are preserved.

### Implementation for User Story 4

- [x] T015 [P] [US4] Import `RefreshButton` from `src/ui/components/ui_helpers.py` in `src/ui/screens/order_history_screen.py`
- [x] T016 [US4] Instantiate `RefreshButton(on_refresh=self._load_orders, page=self._page)` in `src/ui/screens/order_history_screen.py` and add it to the top header `ft.Row` (right-aligned)
- [x] T017 [US4] Verify `_load_orders()` in `src/ui/screens/order_history_screen.py` reads `self.status_filter.value` and `self.date_filter.value` without clearing them — confirm state preservation

**Checkpoint**: Order History screen has a working Refresh button. Status/date filters preserved after refresh.

---

## Phase 6: User Story 5 — Refresh Data on User Management and Chat Screens (Priority: P3)

**Goal**: Manager can refresh the User Management user list; staff can refresh/clear Chat context. Completes 100% screen coverage.

**Independent Test**: Create a new user via API, press Refresh on User Management, confirm new user appears. On Chat, press Refresh and confirm history clears.

### Implementation for User Story 5

- [x] T018 [P] [US5] Import `RefreshButton` from `src/ui/components/ui_helpers.py` in `src/ui/screens/user_mgmt_screen.py`
- [x] T019 [US5] Remove the existing ad-hoc `refresh_btn` (`ft.IconButton`) from `src/ui/screens/user_mgmt_screen.py`
- [x] T020 [US5] Instantiate `RefreshButton(on_refresh=self._load_users, page=self._page)` in `src/ui/screens/user_mgmt_screen.py` and place it in the header container where the old button was
- [x] T021 [P] [US5] Import `RefreshButton` from `src/ui/components/ui_helpers.py` in `src/ui/screens/chat_screen.py`
- [x] T022 [US5] Create a refresh callback in `src/ui/screens/chat_screen.py` that clears `self.chat_history` (the `ListView` children) and resets the chat context
- [x] T023 [US5] Instantiate `RefreshButton(on_refresh=<clear_callback>, page=self._page)` in `src/ui/screens/chat_screen.py` and add it to the top header area (right-aligned)

**Checkpoint**: All 6 screens now have a standardized RefreshButton. SC-002 (100% screen coverage) achieved.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate consistency, update documentation, run regression

- [x] T024 Verify consistent button placement across all 6 screens — RefreshButton must be in the top-right area of each screen's header row (FR-007)
- [x] T025 Run full existing smoke test suite (`python -m pytest tests/smoke/ -v`) to confirm no regressions in `src/ui/screens/` or `src/ui/components/`
- [ ] T026 Run the app (`python -m src`) and perform manual quickstart validation per `specs/002-manual-sync-refresh/quickstart.md` — test all 6 screens
- [x] T027 [P] Update `specs/002-manual-sync-refresh/checklists/requirements.md` to mark feature as implemented and validated

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies — can start immediately. BLOCKS all screen work.
- **US1 POS (Phase 2)**: Depends on Phase 1 completion
- **US2 Products (Phase 3)**: Depends on Phase 1 completion — can run in PARALLEL with Phase 2
- **US3 Reports (Phase 4)**: Depends on Phase 1 completion — can run in PARALLEL with Phases 2-3
- **US4 Order History (Phase 5)**: Depends on Phase 1 completion — can run in PARALLEL with Phases 2-4
- **US5 UserMgmt + Chat (Phase 6)**: Depends on Phase 1 completion — can run in PARALLEL with Phases 2-5
- **Polish (Phase 7)**: Depends on ALL user story phases being complete

### User Story Dependencies

- **US1 (POS, P1)**: Depends only on Phase 1 — no cross-story dependencies
- **US2 (Products, P1)**: Depends only on Phase 1 — no cross-story dependencies
- **US3 (Reports, P2)**: Depends only on Phase 1 — no cross-story dependencies
- **US4 (Order History, P2)**: Depends only on Phase 1 — no cross-story dependencies
- **US5 (UserMgmt + Chat, P3)**: Depends only on Phase 1 — no cross-story dependencies

### Parallel Opportunities

After Phase 1 (Foundational) is complete, ALL user stories (Phases 2-6) can execute in parallel since they each modify different screen files with no cross-file dependencies.

---

## Parallel Example: All User Stories After Phase 1

```bash
# After T001-T004 are complete, launch all screen integrations in parallel:
Task: "[US1] Add RefreshButton to src/ui/screens/pos_screen.py"
Task: "[US2] Add RefreshButton to src/ui/screens/products_screen.py"
Task: "[US3] Standardize RefreshButton in src/ui/screens/reports_screen.py"
Task: "[US4] Add RefreshButton to src/ui/screens/order_history_screen.py"
Task: "[US5] Add RefreshButton to src/ui/screens/user_mgmt_screen.py + chat_screen.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Create RefreshButton component (T001-T004)
2. Complete Phase 2: POS Screen integration (T005-T007)
3. **STOP and VALIDATE**: Test POS refresh independently
4. Highest-impact screen now has manual sync

### Incremental Delivery

1. Phase 1 → RefreshButton component ready
2. US1 (POS) → Highest-impact screen done → Validate
3. US2 (Products) → Second highest-impact screen done → Validate
4. US3 + US4 (Reports + OrderHistory) → P2 screens done → Validate
5. US5 (UserMgmt + Chat) → 100% coverage → Validate
6. Polish → Documentation and regression → Ship

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 27 |
| **Foundational** | 4 tasks (T001-T004) |
| **US1 (POS, P1)** | 3 tasks (T005-T007) |
| **US2 (Products, P1)** | 3 tasks (T008-T010) |
| **US3 (Reports, P2)** | 4 tasks (T011-T014) |
| **US4 (Order History, P2)** | 3 tasks (T015-T017) |
| **US5 (UserMgmt + Chat, P3)** | 6 tasks (T018-T023) |
| **Polish** | 4 tasks (T024-T027) |
| **Parallel opportunities** | All 5 user stories can run in parallel after Phase 1 |
| **MVP scope** | Phase 1 + US1 = 7 tasks for highest-impact refresh |

---

## Chat Command Mode Enhancement (added post-refresh)

### Tasks

- [x] T028 [US-CMD] Expand `IntentParser` with all command types: `create_order`, `finalize_order`, `void_order`, `hold_order`, `add_item`, `create_product`, `stock_in`, `report` — `src/voice/intent_parser.py`
- [x] T029 [US-CMD] Add `get_missing_fields()` and `get_followup_prompt()` methods to `IntentParser` for detecting incomplete intents
- [x] T030 [US-CMD] Add `parse_followup()` method to merge follow-up answers into pending intents
- [x] T031 [US-CMD] Enhance `/api/voice/text-command` endpoint to handle all command types with proper service method signatures — `src/api/app.py`
- [x] T032 [US-CMD] Add `pending_intent` parameter to `TextCommandRequest` for follow-up conversation context
- [x] T033 [US-CMD] Add `followup` response status with `missing_fields` and prompt message
- [x] T034 [US-CMD] Rename mode toggle in `ChatScreen` from "Order Command" to "Command" — `src/ui/screens/chat_screen.py`
- [x] T035 [US-CMD] Implement `_pending_intent` state tracking in `ChatScreen` for multi-turn follow-up conversations
- [x] T036 [US-CMD] Replace `_handle_order_command` with `_handle_command` supporting all command types + follow-up flow
- [x] T037 [US-CMD] Add `_handle_mode_change` callback with examples hint on Command mode selection
- [x] T038 [US-CMD] Add cancel support ("cancel", "nevermind", "stop", "reset") to abort pending follow-ups
- [x] T039 [US-CMD] Update hint text dynamically: "Answer the question above..." when follow-up is pending
- [x] T040 [US-CMD] Update POS quick command dialog to support follow-up flow with `_pos_pending_intent` — `src/ui/screens/pos_screen.py`
- [x] T041 [US-CMD] Update plan.md with Command mode documentation

---

## Notes

- This is a **UI-only feature** — no backend changes, no new API endpoints, no database migrations (refresh part)
- Chat Command Mode adds backend changes to `/api/voice/text-command` endpoint
- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Two screens already have ad-hoc refresh (Reports, UserMgmt) — these are replaced with the standardized component
- Existing toast helpers (`show_success_toast`, `show_error_toast`) in `ui_helpers.py` are reused
- All data-loading methods already preserve user state by design (confirmed in research.md)
