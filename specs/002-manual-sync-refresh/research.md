# Research: Manual Sync / Refresh Button

**Feature**: 002-manual-sync-refresh  
**Date**: 2026-02-13

## Research Items

### 1. Existing Refresh Patterns in Codebase

**Decision**: Two screens already have refresh mechanisms; standardize all screens to use a shared component.

**Findings**:
- `ReportsScreen` has a `refresh_button` (IconButton) and `_handle_refresh()` method at line 454
- `UserManagementScreen` has a `refresh_btn` (IconButton) that calls `_load_users()` at line 36
- `POSScreen`, `ProductsScreen`, `OrderHistoryScreen` have no refresh mechanism
- `ChatScreen` has no list data to refresh (on-demand chat)

**Rationale**: Creating a reusable `RefreshButton` component ensures visual consistency, shared debounce logic, and reduces per-screen implementation effort. Existing ad-hoc buttons will be replaced.

**Alternatives considered**:
- Per-screen custom buttons: Rejected — leads to inconsistent UX and duplicated debounce/loading logic
- Pull-to-refresh gesture: Rejected — Flet desktop doesn't support native pull-to-refresh

---

### 2. Flet 0.80.5 IconButton + ProgressRing Compatibility

**Decision**: Use `ft.IconButton` with dynamic `icon` property swap for loading state.

**Findings**:
- `ft.IconButton(icon=ft.icons.REFRESH)` works in Flet 0.80.5
- Cannot nest a `ProgressRing` inside `IconButton` directly
- Best approach: Use a `ft.Container` or `ft.Stack` that swaps between `IconButton` and `ProgressRing`
- Alternative: Disable the button and change its icon to a different static icon while loading

**Rationale**: A `ft.Stack` with conditional visibility gives the smoothest UX — icon visible when idle, spinner visible when loading, both in the same screen position.

---

### 3. Debounce Implementation in Python/Flet

**Decision**: Simple timestamp-based debounce within the component.

**Findings**:
- Flet runs in a single Python thread; no need for thread-safe debounce
- Store `_last_refresh_time` as a float (from `time.time()`)
- On tap: if `time.time() - _last_refresh_time < 2.0`, ignore
- No external debounce library needed

**Rationale**: Simplest possible implementation. No dependencies. Reliable for single-user desktop app.

**Alternatives considered**:
- `asyncio` debounce decorator: Overly complex for this use case
- Third-party `debounce` package: Unnecessary dependency for one component

---

### 4. State Preservation During Refresh

**Decision**: Each screen's existing data-loading method already preserves state by design.

**Findings**:
- `POSScreen._load_items()` only updates `self.items_grid` — it does NOT touch `self.current_order` or `self.current_order_items`
- `ProductsScreen._load_items(category)` accepts the current filter as a parameter
- `ReportsScreen._load_reports()` reads `self._selected_date` without clearing it
- `OrderHistoryScreen._load_orders()` reads filter values from its dropdown widgets
- No screen's data loader clears user input or draft state

**Rationale**: The refresh callback for each screen is simply its existing data-loader method. No additional state management needed.

---

### 5. Toast/Success Feedback in Flet

**Decision**: Use existing `show_success_toast` from `ui_helpers.py`.

**Findings**:
- `src/ui/components/ui_helpers.py` already has `show_toast()`, `show_success_toast()`, `show_error_toast()`, `show_warning_toast()` functions
- These use `ft.SnackBar` internally and work with Flet 0.80.5
- Can reuse directly in the RefreshButton component

**Rationale**: No new toast/notification system needed. Existing helpers are well-tested and consistent.

## Summary

All research items resolved. No NEEDS CLARIFICATION markers remain. The implementation is straightforward:
1. Create `RefreshButton` in `ui_helpers.py`
2. Add to 4 screens (POS, Products, OrderHistory, Chat)
3. Standardize 2 screens (Reports, UserMgmt) to use the shared component
