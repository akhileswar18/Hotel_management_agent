# Implementation Plan: HMA Production Stabilization & OpenRouter LLM Integration

**Branch**: `001-stabilize-hma-openrouter` | **Date**: 2026-03-20 | **Spec**: `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\spec.md`
**Input**: Feature specification from `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\spec.md`

## Summary

Stabilize the existing HMA agent-first product for production use by fixing current UI compatibility regressions, restoring billing and asset rendering reliability, and wiring OpenRouter into the existing LLM client path so AI Ask/Command workflows execute end-to-end while preserving offline graceful degradation.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flet 0.80.5, FastAPI, httpx (synchronous), pydantic, SQLite  
**Storage**: Existing SQLite database (`C:\Users\akhil\Hotel_management_agent\hms.db`), no schema changes  
**Testing**: Existing `pytest` suite plus manual browser verification via `python src/launcher.py`  
**Target Platform**: Desktop browser via Flet web mode on `localhost:8080` with FastAPI on `localhost:8000`  
**Project Type**: Single Python application (Flet UI + FastAPI backend)  
**Performance Goals**: No regression from current baseline; screen shell loads immediately and local API-backed actions complete within 3 seconds in local runs  
**Constraints**: No new dependencies; UI HTTP remains synchronous; frozen layers unchanged (`src/domain`, `src/application`, `src/infrastructure`, `src/events`, `src/voice`, `src/api/app.py`, and `src/agents/*` except `llm_client.py`); changes restricted to `src/ui/*`, `src/agents/llm_client.py`, and `.env`; offline graceful degradation required  
**Scale/Scope**: Stabilization-only patch touching existing files in UI and one LLM client file; no new feature surfaces, migrations, or test suite expansion

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`C:\Users\akhil\Hotel_management_agent\.specify\memory\constitution.md` is an unfilled template. For enforceable gates, this plan uses the explicit constitution constraints supplied in the approved feature context.

- **Gate 1 - Correctness first (no dependency expansion)**: PASS. No new packages or framework changes.
- **Gate 2 - Reliability over feature growth (frozen business layers)**: PASS. Scope constrained to UI stabilization and `llm_client.py` provider routing only.
- **Gate 3 - Offline-first reliability**: PASS. OpenRouter is additive; command/insight paths must degrade without breaking core workflows.
- **Gate 4 - Data correctness**: PASS. No DB schema or business-rule changes.
- **Gate 5 - Auditability and interaction continuity**: PASS. Existing agent/event/audit interaction model remains intact.

No unresolved clarifications block planning.

## Project Structure

### Documentation (this feature)

```text
C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\
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
├── .env
├── src\
│   ├── agents\
│   │   └── llm_client.py
│   └── ui\
│       ├── app.py
│       ├── components\
│       │   └── ui_helpers.py
│       └── screens\
│           ├── auth_screen.py
│           ├── dashboard_screen.py
│           ├── pos_screen.py
│           ├── products_screen.py
│           ├── receipt_screen.py
│           ├── reports_screen.py
│           ├── order_history_screen.py
│           └── chat_screen.py
└── tests\
    ├── contract\
    ├── integration\
    ├── performance\
    ├── smoke\
    └── unit\
```

**Structure Decision**: Keep the single-project structure unchanged. Implement by patching the listed in-scope files only.

## Phase 0: Research Outcomes

Phase 0 produced `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\research.md` and resolved all planning unknowns.

- Reuse existing OpenAI-compatible request path for OpenRouter routing.
- Apply verify-first strategy on each target file before patching.
- Resolve Flet icon API by runtime detection and one consistent codebase convention.
- Stabilize billing by removing Flet-incompatible patterns while preserving redesigned UX.
- Use a deterministic screen/workflow verification checklist to confirm production readiness.

## Phase 1: Design Artifacts

Phase 1 produced:

- `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\data-model.md`
- `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\contracts\backend-api.md`
- `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\contracts\ui-workflows.md`
- `C:\Users\akhil\Hotel_management_agent\specs\001-stabilize-hma-openrouter\quickstart.md`

Design coverage includes:

- Operational data views needed for screen render checks and workflow validation.
- Interface contracts for AI provider behavior and user-visible workflow outcomes.
- End-to-end verification runbook for all eight screens and critical flows.

## Post-Design Constitution Check

- **Gate 1 - No dependency expansion**: PASS. All designs remain on current stack.
- **Gate 2 - Frozen business layers**: PASS. Contracts explicitly keep frozen layers untouched.
- **Gate 3 - Offline-first reliability**: PASS. Explicit degraded behavior contract included for OpenRouter outages.
- **Gate 4 - Data correctness**: PASS. No new persistence model changes; existing data semantics preserved.
- **Gate 5 - Interaction continuity**: PASS. Existing endpoints and workflows are validated, not redesigned.

Feature is ready for `/speckit.tasks`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
