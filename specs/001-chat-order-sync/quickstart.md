# Quickstart: Chat Order Real-Time Sync

## Prerequisites

- Start the local FastAPI backend.
- Start the Flet UI application from the current feature branch.
- Log in with a user that can access Chat, KDS, Billing, and POS.

## Verify-First Baseline

1. Open KDS and Billing at least once so their current behavior is known.
2. Keep KDS open and submit a Chat Command order.
3. Confirm whether KDS updates immediately or only after manual navigation/timer refresh.
4. Keep Billing open and submit the same style of chat-originated order.
5. Confirm Billing does not update automatically today.
6. Submit a chat parse-confirm order and confirm the confirmation screen navigates back without refreshing Billing.

## Implementation Validation

### Scenario 1: Chat Command -> KDS and Billing

1. Open Chat, KDS, and Billing in the current session.
2. Submit a Chat Command that creates an order.
3. Confirm KDS and Billing both reflect the new order within 2 seconds.

### Scenario 2: Chat Confirmation Flow

1. Start from the parse-confirm ordering flow.
2. Confirm the order from the confirmation screen.
3. Confirm KDS and Billing both refresh within 2 seconds after success.

### Scenario 3: Void/Finalize Flow

1. Use a chat-originated order that can be finalized or voided.
2. Perform the state change from a supported workflow.
3. Confirm both open views end in the correct final state without duplicate or stale entries.

### Scenario 4: Lazy Screen Construction

1. Keep only Chat open.
2. Submit a chat-originated order while KDS and Billing are not open.
3. Confirm the order action succeeds without errors.
4. Navigate to KDS and Billing afterward and confirm both load current data normally.

### Scenario 5: POS Consistency

1. Open POS, KDS, and Billing.
2. Create or update an order from POS.
3. Confirm KDS and Billing still refresh correctly through the shared registry path.

## Regression Checks

- Manual Refresh buttons still work on KDS and Billing.
- KDS timer-based refresh still runs.
- Listener failures do not crash the caller.
- No database or API contracts changed.

## Local Verification Notes (2026-04-09)

- Targeted smoke tests passed for:
  - shared order-listener registry registration, fan-out, and listener-error isolation
  - KDS `notify_external_update()` reload-and-render behavior
  - Billing `notify_external_update()` event-type routing (`order.created`/`order.updated` vs `order.finalized`/`order.voided`)
  - `OrderConfirmationScreen` success-path broadcast callback
  - Chat Command action-to-event mapping
  - POS action-to-event mapping
- Syntax validation passed via `python -m py_compile` on all touched UI modules.
- Full interactive end-to-end UI validation across real screens is still recommended before release because this workspace verification used mocked callbacks and responses rather than live screen driving.
