# Contract: UI Workflow and Rendering Expectations

## Navigation Contract

- User can navigate across all eight primary screens in one session.
- Each screen must render visible content or explicit empty states.
- No screen may fail silently into a blank unusable panel.

## Screen-Specific Contracts

### Billing

- Left-side panel must render on load and remain interactive through payment flow.

### POS and Inventory

- Product/item cards render even when image assets are unavailable.
- Missing images must use fallback visual handling without screen failure.

### Reports

- Daily summary content is visible for selected date context.

### Kitchen

- Active orders and status action controls are visible and usable.

### AI Agent Chat

- Ask mode accepts free-text query and returns response text.
- Command mode accepts operational command and returns execution outcome.
- Screen shows agent health indicators and provider/model metadata.
- Provider outage yields degraded but user-visible response state.

## Compatibility Contract

- UI code must avoid known runtime-incompatible control patterns in current Flet build.
- Icon namespace usage must be consistent with runtime-supported API variant.
- Control initialization order must not access incomplete view state before base initialization completes.
