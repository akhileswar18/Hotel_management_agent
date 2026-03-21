# Contract: UI Stabilization and Screen Availability

## Scope
Defines expected rendering and interaction guarantees for all existing primary screens.

## In-Scope Screens
- Login
- Dashboard
- POS
- Inventory
- Billing
- Reports
- Kitchen Display
- AI Agent

## Behavioral Contract
1. Each screen MUST render visible interactive content or explicit empty state.
2. Billing screen MUST render left operational panel and keep it interactive.
3. POS and Inventory card views MUST remain functional even when media assets are unavailable.
4. Navigation across all screens in one session MUST complete without blocking runtime failures.
5. Existing business workflows MUST remain unchanged in semantics.

## Error Contract
- Rendering incompatibility in one screen MUST surface as diagnosable runtime output and be patchable without cross-layer changes.
- UI incompatibility fixes MUST remain within allowed files and not alter frozen layers.

## Acceptance Signals
- End-to-end navigation pass succeeds across all 8 screens.
- Zero blocking runtime crashes in consecutive full verification runs.
- Core workflow checks (order, billing, kitchen, reporting, chat) succeed.
