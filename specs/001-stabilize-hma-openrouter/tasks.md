# Tasks: HMA Production Stabilization & OpenRouter LLM Integration

**Input**: Design documents from `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\`
**Prerequisites**: `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\plan.md` (required), `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\spec.md` (required), `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\research.md`, `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\data-model.md`, `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\contracts\`

**Tests**: No new automated tests are added in this feature. Manual verification checkpoints are required after each phase. Existing tests must continue to pass.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no incomplete dependency)
- **[Story]**: User story label for story phases only (`[US1]`, `[US2]`, `[US3]`)
- Every task includes an absolute file path or absolute execution path

## Path Conventions

- Repository root: `C:\Users\akhil\Hotel_management_agent\`
- Source code: `C:\Users\akhil\Hotel_management_agent\src\`
- Specs: `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\`

## Phase 1: Setup (Runtime Fact Collection)

**Purpose**: Collect runtime compatibility facts before making edits.

- [X] T001 Run icon API capability check from `C:\Users\akhil\Hotel_management_agent\` using `python -c "import flet as ft; print('Icons:', hasattr(ft, 'Icons')); print('icons:', hasattr(ft, 'icons'))"` and record the result in `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\quickstart.md`
- [X] T002 Run asset URL check from `C:\Users\akhil\Hotel_management_agent\` by starting `python src\launcher.py`, opening `http://localhost:8080/images/paneer_tikka.jpg`, and recording result in `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\quickstart.md`
- [X] T003 Run ElevatedButton compatibility check from `C:\Users\akhil\Hotel_management_agent\` using `python -c "import flet as ft; b = ft.ElevatedButton('Test'); print('OK')"` and record result in `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\quickstart.md`
- [X] T004 Inspect banned patterns in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\receipt_screen.py` (`letter_spacing`, `tooltip=` on `ft.Container`, `dict | None` forms, pre-`super().__init__()` method calls) and record findings in `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\research.md`
- [X] T005 [P] Verify `assets_dir` absolute-path setup in `C:\Users\akhil\Hotel_management_agent\src\ui\app.py` and record status in `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\research.md`
- [X] T006 [P] Verify button constructor usage in `C:\Users\akhil\Hotel_management_agent\src\ui\components\ui_helpers.py` and record status in `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\research.md`

**Checkpoint**: Runtime facts captured and documented; no implementation guesses remain.

---

## Phase 2: Foundational (Blocking Stabilization Prerequisites)

**Purpose**: Apply global compatibility fixes required before any user story validation.

**⚠️ CRITICAL**: No user-story acceptance verification starts until this phase is complete.

- [X] T007 Normalize icon namespace casing across `C:\Users\akhil\Hotel_management_agent\src\ui\app.py` using Phase 1 runtime result and validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\app.py`
- [X] T008 [P] Normalize icon namespace casing in `C:\Users\akhil\Hotel_management_agent\src\ui\components\ui_helpers.py` and validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\components\ui_helpers.py`
- [X] T009 [P] Normalize icon namespace casing in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\auth_screen.py` and validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\auth_screen.py`
- [X] T010 [P] Normalize icon namespace casing in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\dashboard_screen.py` and validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\dashboard_screen.py`
- [X] T011 [P] Normalize icon namespace casing in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\pos_screen.py` and validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\pos_screen.py`
- [X] T012 [P] Normalize icon namespace casing in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\products_screen.py` and validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\products_screen.py`
- [X] T013 [P] Normalize icon namespace casing in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\reports_screen.py` and validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\reports_screen.py`
- [X] T014 [P] Normalize icon namespace casing in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\order_history_screen.py` and validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\order_history_screen.py`
- [X] T015 [P] Normalize icon namespace casing in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\chat_screen.py` and validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\chat_screen.py`
- [X] T016 [P] Normalize icon namespace casing in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\receipt_screen.py` and validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\receipt_screen.py`
- [X] T017 Apply `assets_dir` absolute-path fix in `C:\Users\akhil\Hotel_management_agent\src\ui\app.py` if Phase 1 indicates missing/incorrect config, then validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\app.py`
- [X] T018 Apply ElevatedButton constructor compatibility fix in `C:\Users\akhil\Hotel_management_agent\src\ui\components\ui_helpers.py` based on Phase 1 result, then validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\components\ui_helpers.py`
- [X] T019 Remove banned Flet patterns and init-order violations in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\receipt_screen.py`, then validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\receipt_screen.py`
- [X] T020 [P] Audit and patch banned Flet patterns in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\auth_screen.py`, then validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\auth_screen.py`
- [X] T021 [P] Audit and patch banned Flet patterns in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\dashboard_screen.py`, then validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\dashboard_screen.py`
- [X] T022 [P] Audit and patch banned Flet patterns in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\pos_screen.py`, then validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\pos_screen.py`
- [X] T023 [P] Audit and patch banned Flet patterns in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\products_screen.py`, then validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\products_screen.py`
- [X] T024 [P] Audit and patch banned Flet patterns in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\reports_screen.py`, then validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\reports_screen.py`
- [X] T025 [P] Audit and patch banned Flet patterns in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\order_history_screen.py`, then validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\order_history_screen.py`
- [X] T026 [P] Audit and patch banned Flet patterns in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\chat_screen.py`, then validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\chat_screen.py`
- [X] T027 Perform full restart and foundational navigation smoke pass from `C:\Users\akhil\Hotel_management_agent\` using `python src\launcher.py` and validate Login→Dashboard→POS→Inventory→Billing→Reports→Kitchen→AI Agent with no blocking tracebacks

**Checkpoint**: Foundation is stable; all story work is unblocked.

---

## Phase 3: User Story 1 - Reliable Agent-First Chat Experience (Priority: P1) 🎯 MVP

**Goal**: Deliver live OpenRouter-backed Ask/Command AI interactions with graceful degraded behavior.

**Independent Test**: Login, open AI Agent screen, run Ask and Command prompts, then repeat with invalid key to verify degraded behavior without crashes.

- [X] T028 [US1] Add OpenRouter provider routing/defaults/availability/query handling in `C:\Users\akhil\Hotel_management_agent\src\agents\llm_client.py` and validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\agents\llm_client.py`
- [X] T029 [P] [US1] Add OpenRouter request headers (`HTTP-Referer`, `X-Title`) in `C:\Users\akhil\Hotel_management_agent\src\agents\llm_client.py` and re-validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\agents\llm_client.py`
- [X] T030 [P] [US1] Update AI provider/model display to environment-driven values in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\chat_screen.py` and validate with `python -m py_compile C:\Users\akhil\Hotel_management_agent\src\ui\screens\chat_screen.py`
- [X] T031 [P] [US1] Configure runtime provider variables in `C:\Users\akhil\Hotel_management_agent\.env` (`LLM_PROVIDER`, `OPENROUTER_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT`) with real local key values
- [X] T032 [US1] Execute Ask-mode verification from `C:\Users\akhil\Hotel_management_agent\` by restarting `python src\launcher.py` and validating a live AI response on `C:\Users\akhil\Hotel_management_agent\src\ui\screens\chat_screen.py`
- [X] T033 [US1] Execute Command-mode verification from `C:\Users\akhil\Hotel_management_agent\` by issuing a natural-language operational command in AI Agent screen and confirming workflow side-effects in UI
- [X] T034 [US1] Execute outage degradation verification by setting invalid key in `C:\Users\akhil\Hotel_management_agent\.env`, restarting from `C:\Users\akhil\Hotel_management_agent\`, and confirming degraded but user-visible AI responses

**Checkpoint**: US1 is independently functional and demonstrable.

---

## Phase 4: User Story 2 - Stable Screen Rendering Across Operations (Priority: P2)

**Goal**: Ensure every primary screen renders reliably without blank panels or crash-causing runtime errors.

**Independent Test**: Complete one full navigation cycle across all primary screens and confirm visible content/empty-state with no blocking runtime exceptions.

- [X] T035 [US2] Verify Login screen rendering and successful manager login flow in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\auth_screen.py`
- [X] T036 [US2] Verify Dashboard summary cards/activity feed rendering in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\dashboard_screen.py`
- [X] T037 [US2] Verify POS screen card-grid rendering and non-blank layout in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\pos_screen.py`
- [X] T038 [US2] Verify Inventory screen card-grid rendering and non-blank layout in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\products_screen.py`
- [X] T039 [US2] Verify Billing left-panel rendering and payment section visibility in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\receipt_screen.py`
- [X] T040 [US2] Verify Reports screen rendering and date-selector availability in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\reports_screen.py`
- [X] T041 [US2] Verify Kitchen screen rendering and status-control visibility in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\order_history_screen.py`
- [X] T042 [US2] Verify AI Agent screen render shell, mode toggles, provider metadata, and agent status indicators in `C:\Users\akhil\Hotel_management_agent\src\ui\screens\chat_screen.py`

**Checkpoint**: US2 is independently validated with complete screen availability.

---

## Phase 5: User Story 3 - Verified Core Transaction Workflows (Priority: P3)

**Goal**: Validate and preserve core operational workflows end-to-end without regressions.

**Independent Test**: Complete order creation/finalization, billing payment, kitchen status progression, and reports review in one run.

- [X] T043 [US3] Execute POS order creation and finalization workflow validation against `C:\Users\akhil\Hotel_management_agent\src\ui\screens\pos_screen.py` and patch file if workflow fails
- [X] T044 [US3] Execute inventory browsing/filter workflow validation against `C:\Users\akhil\Hotel_management_agent\src\ui\screens\products_screen.py` and patch file if workflow fails
- [X] T045 [US3] Execute billing payment/change-calculation workflow validation against `C:\Users\akhil\Hotel_management_agent\src\ui\screens\receipt_screen.py` and patch file if workflow fails
- [X] T046 [US3] Execute kitchen status progression workflow validation against `C:\Users\akhil\Hotel_management_agent\src\ui\screens\order_history_screen.py` and patch file if workflow fails
- [X] T047 [US3] Execute reports data/date-interaction workflow validation against `C:\Users\akhil\Hotel_management_agent\src\ui\screens\reports_screen.py` and patch file if workflow fails

**Checkpoint**: US3 workflows are independently executable and stable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final quality gate, regression check, and operational documentation updates.

- [X] T048 Run terminal error sweep during full navigation from `C:\Users\akhil\Hotel_management_agent\` and confirm zero blocking `AttributeError`/`TypeError` tracebacks
- [X] T049 Run regression suite from `C:\Users\akhil\Hotel_management_agent\` using `pytest tests/ -x -q` and resolve any introduced failures in touched files
- [X] T050 Update troubleshooting knowledge in `C:\Users\akhil\Hotel_management_agent\SKILLS.md` with concise entries (error, root cause, fix, files touched, prevention)
- [X] T051 Update progress notes in `C:\Users\akhil\Hotel_management_agent\PROGRESS.md` with phase completion checkpoints and final acceptance status

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Starts immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 completion; blocks all user stories
- **Phase 3 (US1)**: Depends on Phase 2 completion
- **Phase 4 (US2)**: Depends on Phase 2 completion
- **Phase 5 (US3)**: Depends on Phase 2 completion and benefits from US2 completion for stable navigation confidence
- **Phase 6 (Polish)**: Depends on completion of selected user stories

### User Story Dependencies

- **US1 (P1)**: No dependency on US2/US3 once foundational fixes complete
- **US2 (P2)**: No dependency on US1/US3 once foundational fixes complete
- **US3 (P3)**: Depends on foundational stability; uses render reliability established by US2

### Dependency Graph

- `Setup -> Foundational -> {US1, US2} -> US3 -> Polish`
- `US1` and `US2` can run in parallel after Foundational

---

## Parallel Execution Examples

### Parallel Example: User Story 1

```bash
Task T029 [US1]: Update OpenRouter headers in C:\Users\akhil\Hotel_management_agent\src\agents\llm_client.py
Task T030 [US1]: Update provider/model display in C:\Users\akhil\Hotel_management_agent\src\ui\screens\chat_screen.py
Task T031 [US1]: Update local runtime vars in C:\Users\akhil\Hotel_management_agent\.env
```

### Parallel Example: User Story 2

```bash
Task T035 [US2]: Validate auth screen in C:\Users\akhil\Hotel_management_agent\src\ui\screens\auth_screen.py
Task T036 [US2]: Validate dashboard screen in C:\Users\akhil\Hotel_management_agent\src\ui\screens\dashboard_screen.py
Task T040 [US2]: Validate reports screen in C:\Users\akhil\Hotel_management_agent\src\ui\screens\reports_screen.py
```

### Parallel Example: User Story 3

```bash
Task T043 [US3]: Validate POS order workflow in C:\Users\akhil\Hotel_management_agent\src\ui\screens\pos_screen.py
Task T044 [US3]: Validate inventory workflow in C:\Users\akhil\Hotel_management_agent\src\ui\screens\products_screen.py
Task T047 [US3]: Validate reports workflow in C:\Users\akhil\Hotel_management_agent\src\ui\screens\reports_screen.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2
2. Complete Phase 3 (US1)
3. Validate Ask mode, Command mode, and degraded behavior
4. Demo/release MVP if acceptable

### Incremental Delivery

1. Finish Setup + Foundational
2. Deliver US1 (agent-first AI value)
3. Deliver US2 (screen reliability)
4. Deliver US3 (core workflow reliability)
5. Run Phase 6 polish before release

### Parallel Team Strategy

1. Team completes Phase 1 and Phase 2 together
2. After foundation is stable:
   - Engineer A: US1 (`llm_client.py`, `chat_screen.py`, `.env`)
   - Engineer B: US2 (screen render verification)
   - Engineer C: US3 (transaction workflow validation)
3. Merge and run final polish gates

---

## Notes

- Tasks marked `[P]` are safe for parallel execution
- User story labels provide strict traceability from spec to implementation
- No new dependencies, migrations, backend API changes, or test files are added in this feature
- Full restarts are mandatory for runtime validation steps
