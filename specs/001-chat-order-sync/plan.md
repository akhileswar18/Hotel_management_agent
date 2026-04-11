# Implementation Plan: Chat Order Real-Time Sync

**Branch**: `001-chat-order-sync` | **Date**: 2026-04-09 | **Spec**: [spec.md](C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/spec.md)
**Input**: Feature specification from `/specs/001-chat-order-sync/spec.md`

## Summary

Add an in-process order-change notification path so chat-originated order actions refresh already-open Kitchen Display System and Billing screens within 2 seconds, without waiting for route changes or timer-driven refresh. The plan is deliberately verify-first: confirm the current callback wiring and runtime surface before introducing a small registry in `app.py`, then wire listeners and broadcasters in independent phases.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flet UI runtime, FastAPI backend, httpx (synchronous), pydantic, Python standard-library `threading.Timer`  
**Storage**: Existing SQLite database (`hms.db`), no schema changes  
**Testing**: pytest, targeted manual UI smoke checks for cross-screen sync flows  
**Target Platform**: Desktop/browser-hosted Flet app against local FastAPI server on the same machine  
**Project Type**: Single Python application with `src/` and `tests/`  
**Performance Goals**: Open KDS and Billing views reflect successful chat-originated create/finalize/void changes within 2 seconds in normal local operation  
**Constraints**: Verify-first Phase 0 with zero code changes; offline-first and in-process only; no new dependencies; no database or API changes; safe no-op when target screen does not exist; listener failures must not block the calling workflow; notification callbacks must remain idempotent because KDS already refreshes on `threading.Timer`  
**Scale/Scope**: UI-only change across roughly 6 files and ~130 lines; one app shell, one shared registry, two primary listeners (KDS and Billing), and three broadcaster surfaces (Order Confirmation, Chat Command mode, POS)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still a placeholder template, so it does not provide enforceable gates. For this plan, the repository root [constitution.md](C:/Users/akhil/Hotel_management_agent/constitution.md) is treated as the operative constitution because it contains the project’s actual non-negotiable rules.

- **Offline-First Architecture**: Pass. The design stays in-process, introduces no network dependency, and relies on existing screen reload behavior against the local application stack.
- **Data Correctness is Non-Negotiable**: Pass. The feature changes notification timing only; order creation and mutation remain in existing validated workflows.
- **Auditability & Traceability**: Pass. No business-state changes are moved or hidden; notifications only mirror successful order actions already recorded by current flows.
- **Safety for Destructive Actions**: Pass. Void/finalize permissions and confirmation behavior remain in existing workflows.
- **Minimal Friction UX**: Pass. This feature directly reduces manual navigation and refresh friction for kitchen and billing staff.
- **Deterministic Business Logic**: Pass. No pricing, inventory, or business-rule logic is changed.
- **AI is Assistive, Not Authoritative**: Pass. Chat continues to submit through validated order workflows; the new behavior is only UI synchronization after successful outcomes.
- **Modular Architecture with Clear Boundaries**: Pass with caution. A registry in `app.py` is acceptable if it remains a narrow UI coordination boundary and does not leak business logic into the shell.

**Gate Result (pre-research)**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/001-chat-order-sync/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── order-change-notification.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── ui/
│   ├── app.py
│   └── screens/
│       ├── chat_screen.py
│       ├── order_confirmation_screen.py
│       ├── order_history_screen.py
│       ├── pos_screen.py
│       └── receipt_screen.py
└── ...

tests/
├── ...
```

**Structure Decision**: Keep the work inside the existing single-project `src/` layout. The shared notification registry lives in [src/ui/app.py](C:/Users/akhil/Hotel_management_agent/src/ui/app.py), while each screen keeps its own refresh or broadcast responsibilities.

## Phase Plan

### Phase 0 - Verify-First Research

**Goal**: Confirm actual runtime behavior before any code changes.

1. Trace the existing Chat Command callback path from `ChatScreen._handle_command()` through `_emit_kitchen_update()` into `HMSApp._notify_kitchen_update()` and finally into `OrderHistoryScreen.notify_external_update()`.
2. Confirm whether Billing currently exposes any equivalent external refresh entry point.
3. Confirm whether the installed Flet runtime exposes `page.pubsub`, while treating it as an optional observation rather than a design dependency.
4. Record the implications of lazy screen construction and timer-driven KDS refresh behavior.

**Exit Criteria**:

- All Phase 0 unknowns are resolved in [research.md](C:/Users/akhil/Hotel_management_agent/specs/001-chat-order-sync/research.md).
- No `NEEDS CLARIFICATION` items remain.
- Design direction is explicitly justified from observed runtime behavior.

### Phase 1 - Shared Registry Infrastructure

**Goal**: Introduce a minimal UI coordination layer in `app.py`.

1. Add `register_order_listener`, `unregister_order_listener`, and `notify_order_change` in [src/ui/app.py](C:/Users/akhil/Hotel_management_agent/src/ui/app.py).
2. Keep listener invocation best-effort, silent on listener failure, and non-blocking to the originating workflow.
3. Scope the registry to already-instantiated screens only; first navigation continues to load fresh state normally.

**Parallelism**: None. This phase establishes the shared base required by later phases.

### Phase 2 - Listener Wiring

**Goal**: Make KDS and Billing subscribe and refresh safely.

1. KDS path: register/unregister [src/ui/screens/order_history_screen.py](C:/Users/akhil/Hotel_management_agent/src/ui/screens/order_history_screen.py) and reuse its existing idempotent reload-and-render path.
2. Billing path: add an external refresh method in [src/ui/screens/receipt_screen.py](C:/Users/akhil/Hotel_management_agent/src/ui/screens/receipt_screen.py), then register/unregister it with the shared registry.
3. Preserve current screen context where practical and tolerate redundant refreshes because timer-driven refresh already exists.

**Parallelism**: KDS and Billing listener wiring can proceed independently once Phase 1 is complete.

### Phase 3 - Broadcaster Wiring

**Goal**: Emit order-change notifications from successful order workflows.

1. Chat parse-confirm flow: after successful order creation in [src/ui/screens/order_confirmation_screen.py](C:/Users/akhil/Hotel_management_agent/src/ui/screens/order_confirmation_screen.py), broadcast order change before navigating back.
2. Chat command flow: replace the KDS-only callback usage in [src/ui/screens/chat_screen.py](C:/Users/akhil/Hotel_management_agent/src/ui/screens/chat_screen.py) with the shared notification mechanism.
3. POS consistency path: route [src/ui/screens/pos_screen.py](C:/Users/akhil/Hotel_management_agent/src/ui/screens/pos_screen.py) broadcasts through the shared notification mechanism so all active listeners receive the same signal.

**Parallelism**: The three broadcaster files can be wired independently after Phase 1 and integrated together.

### Phase 4 - Regression and Smoke Validation

**Goal**: Prove the fix is applied across all order paths and screens.

1. Verify KDS updates for chat command create/finalize/void when KDS is already open.
2. Verify Billing updates for chat parse-confirm and chat command order creation when Billing is already open.
3. Verify no crash occurs when KDS or Billing has not been instantiated yet.
4. Verify POS-originated updates still propagate correctly.
5. Verify existing timer refresh and manual refresh continue to work, with redundant refreshes tolerated.

**Parallelism**: Manual smoke scenarios can be split by order path after implementation lands.

## Risk Notes

- **Version mismatch risk**: [AGENTS.md](C:/Users/akhil/Hotel_management_agent/AGENTS.md) documents Flet `0.80.5`, but [requirements.txt](C:/Users/akhil/Hotel_management_agent/requirements.txt) currently pins `flet==0.21.2`. The plan avoids taking a dependency on `page.pubsub` despite its presence in the installed runtime.
- **Lazy construction risk**: Billing or KDS may not exist when an event fires. The registry must treat missing listeners as a no-op and rely on normal initial screen load later.
- **Thread-safety risk**: KDS already uses `threading.Timer`; notification callbacks should stay idempotent and limited to reload-and-render so redundant refreshes are acceptable.
- **False-fix risk**: Because prior failures were caused by code paths not actually reaching active screens, Phase 0 and Phase 4 both explicitly verify end-to-end runtime behavior.

## Post-Design Constitution Check

- **Offline-First Architecture**: Pass. Design remains local and in-process.
- **Data Correctness is Non-Negotiable**: Pass. Notifications occur only after existing successful state changes.
- **Auditability & Traceability**: Pass. Existing order actions remain the source of truth; no audit path is bypassed.
- **Minimal Friction UX**: Pass. Open kitchen and billing views update automatically instead of relying on manual navigation.
- **Modular Architecture with Clear Boundaries**: Pass. The registry is a thin UI coordination contract, and listeners/broadcasters stay screen-scoped.

**Gate Result (post-design)**: PASS

## Complexity Tracking

No constitution violations or extra complexity waivers are currently required. The chosen design is the simplest option that satisfies already-open screen synchronization without adding infrastructure, API changes, or persistence changes.
