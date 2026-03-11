# Implementation Plan: Modernized HMS UI

**Branch**: `001-modernize-hms-ui` | **Date**: 2026-03-11 | **Spec**: `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\spec.md`
**Input**: Feature specification from `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\spec.md`

## Summary

Modernize the existing HMS experience by redesigning eight existing Flet screens around a shared dark design system, faster visual scanning, and clearer role-based actions while preserving current workflows and business logic. Implementation stays concentrated in the UI layer, with only two additive backend surfaces: a read-only audit log endpoint and persisted `kitchen_status` metadata exposed on orders.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flet 0.80.5, FastAPI, httpx, pydantic, existing standard-library threading/timer utilities  
**Storage**: Existing SQLite database (`hms.db`) via current repository pattern, plus one additive SQL migration for `kitchen_status`  
**Testing**: Existing `pytest` suite in `C:\Users\akhil\Hotel_management_agent\tests` plus manual browser validation through `python src/launcher.py`  
**Target Platform**: Desktop browser via Flet web mode on `localhost:8080` with FastAPI on `localhost:8000`  
**Project Type**: Single Python application with a Flet UI and FastAPI backend in one repository  
**Performance Goals**: Preserve current responsiveness for local/offline hotel operations; main screens should render shell immediately, populate local data sections without noticeable blocking, and keep critical status information readable at a glance during live service  
**Constraints**: No new dependencies; UI HTTP must remain synchronous via `httpx.Client`; domain, service, repository, agent, and voice layers stay frozen; charts must use Flet primitives only; minimum interactive control height is 48px; POS keyboard shortcuts must be preserved; prototype HTML/screens referenced in the prompt are not present in the workspace, so the textual feature brief is the planning source of truth  
**Scale/Scope**: 8 screen redesigns, 1 new screen file, 6 major screen rewrites, app-shell navigation redesign, 2 API additions, 1 additive migration, zero business-rule changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The repository constitution at `C:\Users\akhil\Hotel_management_agent\.specify\memory\constitution.md` is still an unfilled template with no ratified project-specific principles or enforceable gates. In its place, this plan applies the explicit constraints from the approved feature request as operational gates:

- **Gate 1 - No dependency expansion**: PASS. Plan uses only the installed stack and Flet primitives.
- **Gate 2 - Frozen business logic boundary**: PASS. Planned code changes stay in `src/ui/*`, `src/api/app.py`, and one additive migration file only.
- **Gate 3 - Backend changes tightly scoped**: PASS WITH EXPLICIT EXCEPTION. The prompt authorizes two minimal backend additions; persisting `kitchen_status` also requires one new migration file in `C:\Users\akhil\Hotel_management_agent\migrations`, which is the smallest viable implementation.
- **Gate 4 - Existing interaction model preserved**: PASS. Existing handlers, endpoints, keyboard shortcuts, and synchronous request patterns remain intact.
- **Gate 5 - Validation discipline**: PASS. Existing automated tests remain part of the acceptance gate, supplemented by screen-by-screen manual checks from `quickstart.md`.

No unresolved clarification blocks remain for planning.

## Project Structure

### Documentation (this feature)

```text
C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts\
│   ├── backend-api.md
│   └── ui-workflows.md
└── tasks.md
```

### Source Code (repository root)

```text
C:\Users\akhil\Hotel_management_agent\
├── migrations\
│   ├── 001_init_schema.sql
│   ├── 002_add_is_active.sql
│   ├── 003_add_event_log.sql
│   ├── 004_add_held_status.sql
│   └── runner.py
├── src\
│   ├── api\
│   │   └── app.py
│   ├── ui\
│   │   ├── app.py
│   │   ├── components\
│   │   │   └── ui_helpers.py
│   │   └── screens\
│   │       ├── auth_screen.py
│   │       ├── chat_screen.py
│   │       ├── order_history_screen.py
│   │       ├── pos_screen.py
│   │       ├── products_screen.py
│   │       ├── receipt_screen.py
│   │       ├── reports_screen.py
│   │       └── dashboard_screen.py
│   └── launcher.py
└── tests\
    ├── contract\
    ├── integration\
    ├── performance\
    ├── smoke\
    └── unit\
```

**Structure Decision**: Keep the existing single-project structure. Concentrate implementation in the existing Flet shell and screen modules, add one new dashboard screen, and document the one required migration as the only persistent data-layer exception.

## Phase 0: Research Outcomes

Phase 0 produced `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\research.md` and resolved all planning unknowns:

- Use the detailed feature brief as the authoritative design source because the referenced prototype HTML and screenshot folders are not present locally.
- Centralize visual tokens and shared builders in `src/ui/components/ui_helpers.py` to keep eight screen rewrites consistent.
- Source activity feed and AI event log from `audit_log` through a new API mapping layer because that read path already exists conceptually, unlike `event_log`.
- Treat `kitchen_status` as additive order metadata stored directly in the orders table and exposed through API models without changing the frozen domain/service layers.
- Keep all charts, progress indicators, timers, and badges in Flet primitives with synchronous refresh patterns.

## Phase 1: Design Artifacts

Phase 1 produced the following artifacts:

- `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\data-model.md`
- `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\contracts\backend-api.md`
- `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\contracts\ui-workflows.md`
- `C:\Users\akhil\Hotel_management_agent\specs\001-modernize-hms-ui\quickstart.md`

Design coverage includes:

- View-model definitions for dashboard, POS, inventory, billing, kitchen, and AI panels
- Backend contract definitions for audit log reads, kitchen-status updates, and order payload extension
- UI workflow contracts for navigation, role-gated actions, empty states, and refresh behavior
- Manual validation steps aligned to the requested implementation order

## Post-Design Constitution Check

- **No dependency expansion**: PASS. Design uses current libraries only.
- **Frozen business logic boundary**: PASS. Design keeps domain/application/agent changes out of scope.
- **Scoped backend surface**: PASS WITH EXPLICIT EXCEPTION. One additive migration remains necessary for persistent `kitchen_status`, and no other schema or backend broadening is introduced.
- **Synchronous UI data flow**: PASS. All planned fetches remain synchronous and local to screen lifecycle or periodic refresh timers.
- **Validation discipline**: PASS. Design artifacts define both automated regression expectations and manual screen verification.

The feature is ready to proceed to task breakdown.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Additive migration outside the UI/app manifest | Persistent `kitchen_status` cannot exist across sessions without schema support | A UI-only or in-memory status would break dashboard, kitchen, and billing consistency and would not survive reloads |
