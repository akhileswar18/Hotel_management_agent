# Phase 0 Research: Modernized HMS UI

## Decision: Treat the written feature brief as the design source of truth

**Rationale**: The prompt references `hms_figma_prototype.html` and `.specify/screens/current|target`, but those assets are not present in the workspace. The written feature brief still contains enough screen-level detail, color direction, layout intent, and interaction rules to plan the work safely.

**Alternatives considered**:

- Delay planning until prototype assets are restored: rejected because the written brief is already detailed enough for planning.
- Infer target design from the current Flet UI alone: rejected because the prompt supplies clearer redesign intent than the current implementation.

## Decision: Centralize the redesign in shared UI helpers and app shell first

**Rationale**: Eight screens must feel like one coherent product. Replacing tokens and reusable builders in `src/ui/components/ui_helpers.py` and restructuring the shell in `src/ui/app.py` creates consistent status colors, headers, chips, cards, spacing, and navigation before screen-by-screen work begins.

**Alternatives considered**:

- Redesign each screen independently: rejected because it would produce inconsistent styling and duplicate component logic.
- Add a separate design system package: rejected because new dependencies and project structure changes are out of scope.

## Decision: Keep the application architecture unchanged and use only additive backend changes

**Rationale**: The approved scope explicitly freezes domain logic, services, repositories, agents, and voice components. The redesign therefore stays in the Flet layer, with only two backend additions needed to support the new UI: a read-only audit log endpoint and persisted kitchen-status metadata.

**Alternatives considered**:

- Rework domain order status to include kitchen workflow: rejected because the frozen business layer forbids it.
- Move activity feed generation into the UI only: rejected because the dashboard and AI audit panel need shared, consistent event data.

## Decision: Build dashboard activity feed and AI event panel from `audit_log`, not `event_log`

**Rationale**: Existing code already persists audit data and the repository surface is known to support reading audit entries. `event_log` exists separately, but using it would require more new backend translation work and broader design assumptions. For this feature, one unified audit feed is the smallest reliable path.

**Alternatives considered**:

- Use `event_log` for the AI panel and `audit_log` for dashboard activity: rejected because it creates two different semantics for similar UI surfaces.
- Merge audit and event log behavior now: rejected because it broadens backend scope beyond the approved additions.

## Decision: Implement `kitchen_status` as additive order metadata with one migration

**Rationale**: Kitchen progression needs persistence and shared visibility across dashboard, POS, billing, and the kitchen display. Because the domain and service layers are frozen, the least invasive design is an additive database column plus API-layer read/write support.

**Alternatives considered**:

- Keep kitchen status only in the UI session: rejected because status would be lost on reload and would not support multi-screen visibility.
- Encode kitchen progress inside existing order status values: rejected because it changes business semantics and frozen domain contracts.

## Decision: Use Flet primitives only for all charts, bars, and tickets

**Rationale**: The prompt forbids new dependencies and explicitly requires charts and progress indicators to be composed from Flet primitives. This keeps deployment unchanged and avoids compatibility risk with Flet 0.80.5.

**Alternatives considered**:

- Add a charting library or browser-side widget: rejected because new dependencies are forbidden.
- Reduce reports to text-only summaries: rejected because the redesign goal is to make trends visible at a glance.

## Decision: Preserve synchronous UI networking and existing handler entry points

**Rationale**: The codebase already standardized on synchronous `httpx.Client` usage in the UI and explicitly forbids reintroducing asynchronous event-loop patterns in Flet. Reusing current handler methods and keyboard shortcuts lowers regression risk in the busiest workflows.

**Alternatives considered**:

- Convert UI calls to async patterns: rejected because it conflicts with the existing Flet guidance and prior fixes.
- Replace existing handlers with new orchestration flows: rejected because the current workflows already function and only the interaction layer is being redesigned.

## Decision: Validate incrementally in the same order as the requested implementation sequence

**Rationale**: The feature touches the shell, eight screens, and two backend surfaces. Following the user-provided order makes regressions easier to isolate and lets each step be manually verified before the next visual layer is added.

**Alternatives considered**:

- Rebuild all screens first and test at the end: rejected because debugging visual and behavioral regressions would become slower.
- Start with backend additions last: rejected because dashboard, kitchen, and AI event views depend on the new data surfaces.
