# Research: Chat Order Real-Time Sync

## Decision 1: Use a shared callback registry in `app.py` instead of relying on direct KDS-only callbacks

**Rationale**:

- The current runtime path proves that Chat Command mode already reaches KDS when the kitchen screen is instantiated: `ChatScreen._handle_command()` calls `_emit_kitchen_update()`, which invokes the callback provided by `HMSApp`, and `HMSApp._notify_kitchen_update()` forwards to `OrderHistoryScreen.notify_external_update()`.
- That path is too narrow because it only targets KDS and does not provide a reusable mechanism for Billing or other active order-management screens.
- A small registry in `app.py` keeps the coordination local to the UI shell, satisfies the in-process/offline-first constraint, and lets multiple already-visible screens subscribe without each broadcaster needing to know every target.

**Alternatives considered**:

- Keep the current direct `on_kitchen_update` callback and add more one-off callbacks for Billing. Rejected because it scales poorly and repeats the current coordination gap.
- Use Flet `page.pubsub`. Rejected for this feature because the runtime/version story is inconsistent and a local registry is simpler and more predictable.

## Decision 2: Treat the existing Chat Command -> KDS path as verified, but incomplete

**Rationale**:

- Evidence from [src/ui/screens/chat_screen.py](C:/Users/akhil/Hotel_management_agent/src/ui/screens/chat_screen.py): on successful command execution, `_handle_command()` calls `_emit_kitchen_update(data)`.
- Evidence from [src/ui/app.py](C:/Users/akhil/Hotel_management_agent/src/ui/app.py): `ChatScreen` is instantiated with `on_kitchen_update=self._notify_kitchen_update`, and `_notify_kitchen_update()` forwards to the kitchen screen’s `notify_external_update()`.
- Evidence from [src/ui/screens/order_history_screen.py](C:/Users/akhil/Hotel_management_agent/src/ui/screens/order_history_screen.py): `notify_external_update()` reloads orders and re-renders immediately.
- Therefore, the path exists today for KDS, but only for that single listener and only if the screen instance is already present in `self.screens`.

**Alternatives considered**:

- Assume the callback wiring is broken and redesign from scratch. Rejected because direct code inspection shows the KDS path is present.
- Leave KDS untouched and only add Billing updates. Rejected because both KDS and Billing should move to the same shared mechanism for consistency.

## Decision 3: Add an explicit external refresh entry point to Billing

**Rationale**:

- [src/ui/screens/receipt_screen.py](C:/Users/akhil/Hotel_management_agent/src/ui/screens/receipt_screen.py) has `_load_draft_orders()` and `_load_recent()`, but no `notify_external_update()` or similar externally callable refresh hook.
- Billing currently loads drafts during initialization and through manual UI interactions only.
- A dedicated external refresh method lets Billing participate in the same registry contract as KDS without overloading route navigation or screen construction behavior.

**Alternatives considered**:

- Recreate the Billing screen on every order event. Rejected because it is heavier, more disruptive to user context, and unnecessary.
- Rely on first navigation only. Rejected because the feature requires already-open Billing views to update within 2 seconds.

## Decision 4: Do not depend on `page.pubsub` for this feature

**Rationale**:

- The installed runtime exposes `flet.Page.pubsub` in the local environment.
- However, repository guidance is inconsistent: [AGENTS.md](C:/Users/akhil/Hotel_management_agent/AGENTS.md) says Flet `0.80.5`, while [requirements.txt](C:/Users/akhil/Hotel_management_agent/requirements.txt) currently pins `flet==0.21.2`.
- Given the feature scope, a simple callback registry is lower risk than adopting a framework event surface the team has already flagged as API-unstable.

**Alternatives considered**:

- Standardize immediately on `page.pubsub`. Rejected because the feature does not require it and the version mismatch makes it a needless planning dependency.
- Leave `page.pubsub` unresolved. Rejected because Phase 0 explicitly required verifying whether it exists.

## Decision 5: Notifications should only accelerate already-open screens; lazy screen construction remains unchanged

**Rationale**:

- The current app shell stores screen instances in `self.screens`, but user expectations only require automatic refresh for screens that are already instantiated and visible in the current session.
- When a screen is not yet open, there is no reason to synthesize a hidden instance purely to receive notifications.
- Keeping first-time navigation behavior unchanged avoids new lifecycle complexity and aligns with the stated constraint that missing targets must not cause crashes.

**Alternatives considered**:

- Force eager construction of all screens solely to ensure every event has a target. Rejected because it increases memory/lifecycle complexity without user benefit.
- Persist queued notifications for future screens. Rejected because normal screen load already fetches fresh data from the existing API.

## Decision 6: Make listener callbacks idempotent and tolerant of redundant refreshes

**Rationale**:

- KDS already uses `threading.Timer` auto-refresh every 30 seconds, so event-driven refresh can overlap with timer-based refresh.
- Both KDS and Billing can safely respond using reload-and-render behavior rather than incremental mutations, which keeps callbacks simple and reduces race sensitivity.
- Silent catch behavior on listener errors satisfies the requirement that one failed listener must not block other listeners or the originating workflow.

**Alternatives considered**:

- Try to debounce or serialize every refresh. Rejected because it adds complexity for little value at this scope.
- Push fine-grained partial updates into each screen. Rejected because it is harder to reason about and more fragile than full reload-and-render.

## Verified Findings (2026-04-09)

- `ChatScreen._handle_command()` already reached `HMSApp._notify_kitchen_update()` and then `OrderHistoryScreen.notify_external_update()` before this feature work; the gap was that Billing never received an equivalent signal.
- `ReceiptScreen` had `_load_draft_orders()` and `_load_recent()` but no externally callable refresh entry point or listener lifecycle hooks.
- `HMSApp._init_main_shell()` eagerly constructed both KDS and Billing screens, so listener registration at construction time is valid in the current shell design.
- The local runtime exposes `flet.Page.pubsub`, but the repository still has a version mismatch between guidance in `AGENTS.md` and the pinned dependency in `requirements.txt`, so the implementation stayed with the simpler in-process registry.
