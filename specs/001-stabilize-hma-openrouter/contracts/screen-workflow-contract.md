# Contract: Screen Workflow Stability

## Scope
Defines minimum render and workflow guarantees across existing screens.

## Covered Screens
- Login
- Dashboard
- POS
- Inventory
- Billing
- Reports
- Kitchen Display
- AI Agent

## Behavioral Contract
1. Every screen must load with visible content or explicit empty state.
2. Navigation across all screens in one session must not produce blocking crashes.
3. Billing screen must render left operational panel on load.
4. POS and Inventory product cards must render regardless of image availability.
5. Core workflows (order finalize, billing payment, kitchen status update, report view) must remain executable.

## Error Handling Contract
- Runtime failures must be surfaced in logs and user-visible states where applicable.
- Silent blank panels are considered contract violations.

## Compatibility Constraints
- Existing interaction model and scope are preserved.
- Stabilization does not introduce new user workflows.
