# Implementation Plan: Manual Sync / Refresh Button

**Branch**: `002-manual-sync-refresh` | **Date**: 2026-02-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-manual-sync-refresh/spec.md`

## Summary

Add a consistent, debounced Refresh button to every main screen in the HMS Flet UI so users can manually reload data from the backend when automatic updates are insufficient. The implementation is UI-only — no new backend endpoints are required.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Flet 0.80.5 (UI), httpx (HTTP client), FastAPI (backend)  
**Storage**: SQLite (local, via existing backend API)  
**Testing**: pytest with FastAPI TestClient  
**Target Platform**: Desktop (Windows) via Flet  
**Project Type**: Single project — `src/` for source, `tests/` for tests  
**Performance Goals**: Refresh completes in < 3 seconds under normal conditions  
**Constraints**: Offline-first (local SQLite backend), must not lose draft order state  
**Scale/Scope**: 6 screens to update, ~1 reusable component

## Constitution Check

*GATE: Constitution is a placeholder template — no project-specific rules defined. No violations to check.*

**Pre-design**: PASS (no gates defined)  
**Post-design**: PASS (no gates defined)

## Project Structure

### Documentation (this feature)

```text
specs/002-manual-sync-refresh/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (minimal — UI-only feature)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (no new endpoints)
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── ui/
│   ├── components/
│   │   └── ui_helpers.py          # Add RefreshButton reusable component
│   ├── screens/
│   │   ├── pos_screen.py          # Add refresh (P1)
│   │   ├── products_screen.py     # Add refresh (P1)
│   │   ├── reports_screen.py      # Already has refresh — standardize (P2)
│   │   ├── order_history_screen.py # Add refresh (P2)
│   │   ├── user_mgmt_screen.py    # Already has refresh — standardize (P3)
│   │   └── chat_screen.py         # Add refresh (P3)

tests/
├── smoke/
│   └── test_agent_smoke.py        # Add refresh-related HTTP tests
```

**Structure Decision**: Single project. All changes are in the existing `src/ui/` layer. A shared `RefreshButton` component goes in `src/ui/components/ui_helpers.py` to ensure consistency across screens.

## Design

### Approach: Reusable RefreshButton Component

Create a single `RefreshButton` widget in `ui_helpers.py` that encapsulates:
- A Flet `IconButton` with `ft.icons.REFRESH` icon
- Loading state (swap icon to `ProgressRing` spinner while refreshing)
- Debounce logic (ignore taps within 2 seconds of last tap)
- Error callback for displaying failure messages
- Success callback for optional toast notification

Each screen imports `RefreshButton`, passes its data-loading method as the `on_refresh` callback, and places the button in its header row.

### Screen-by-Screen Plan

| Screen | Data Loader | State to Preserve | Current Refresh | Action |
|--------|------------|-------------------|-----------------|--------|
| POSScreen | `_load_items()` | `current_order`, `current_order_items`, `table_id_field` | None | Add RefreshButton to header row |
| ProductsScreen | `_load_items(category)` | `category_filter.value` | None | Add RefreshButton; pass current filter |
| ReportsScreen | `_load_reports()` | `_selected_date`, txn filters | Has custom refresh | Replace with standardized RefreshButton |
| OrderHistoryScreen | `_load_orders()` | `status_filter.value`, `date_filter.value` | None | Add RefreshButton to header row |
| UserMgmtScreen | `_load_users()` | None | Has IconButton | Replace with standardized RefreshButton |
| ChatScreen | N/A (on-demand) | `chat_history` | None | Add RefreshButton that clears chat history |

### RefreshButton Component Design

```
RefreshButton(
    on_refresh: Callable  — async/sync function to call on tap
    page: ft.Page         — for toast notifications
    tooltip: str          — default "Refresh data"
)

Behavior:
1. User taps → check debounce (2s cooldown)
2. If allowed → show spinner, disable button
3. Call on_refresh()
4. On success → restore icon, show "Data refreshed" toast
5. On error → restore icon, show error toast
6. Re-enable button
```

### Error Handling

- **Backend unreachable**: httpx.ConnectError → toast "Could not refresh — server unavailable"
- **Timeout**: httpx.TimeoutException → toast "Refresh timed out — try again"
- **Other errors**: Generic → toast "Refresh failed: {error}"
- **In all cases**: Existing data remains displayed, button re-enables

### State Preservation Strategy

Each screen's refresh callback only reloads *display data* — it never clears:
- POSScreen: `_load_items()` reloads the item grid; `current_order` and `current_order_items` are separate state that remains untouched
- ProductsScreen: `_load_items(self.category_filter.value)` passes the current filter
- ReportsScreen: `_load_reports()` uses `self._selected_date`
- OrderHistoryScreen: `_load_orders()` uses existing filter values
- UserMgmtScreen: `_load_users()` has no filter state
- ChatScreen: refresh clears chat history (by design — fresh context)

## Complexity Tracking

No constitution violations. No complexity justification needed.

## Enhancement: Chat Command Mode (added post-refresh)

### Scope

Rename "Order Command" to **"Command"** mode in ChatScreen. This mode understands natural language commands for ALL operations (not just ordering), and asks follow-up questions when required information is missing.

### Supported Commands

| Command | Example | Required Fields |
|---------|---------|-----------------|
| `create_order` | "create order for table 5 with 2 biryani" | table_id, items |
| `add_item` | "add 3 coke to current order" | item(s) |
| `finalize_order` | "finalize order" / "pay cash" | payment_method |
| `void_order` | "void current order" | reason (optional) |
| `hold_order` | "hold current order" | — |
| `create_product` | "add new product biryani at 250" | name, price, category |
| `stock_in` | "add 50 units of biryani to stock" | item, quantity |
| `report` | "show today's sales" | — |

### Follow-Up Question Flow

When required fields are missing, the system asks follow-up questions:

```
User: "create order"
HMS: "Which table? And what items would you like to add?"
User: "table 3, 2 biryani and 1 coke"
HMS: "Order created! Table 3: 2 Biryani, 1 Coke"
```

### Implementation

1. `IntentParser` — expanded with new intents + `get_missing_fields()` method
2. `/api/voice/text-command` — handles all command types, returns follow-up prompts
3. `ChatScreen` — tracks `_pending_intent` for conversational context

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Flet icon/component API changes | Low | Medium | Pin Flet 0.80.5; test on startup |
| Refresh during active order loses state | Medium | High | Refresh only reloads item grid, not order state |
| Rapid taps cause multiple API calls | Medium | Low | Debounce (2s cooldown) built into component |
| Refresh spinner stuck if callback errors | Low | Medium | Try/finally in RefreshButton ensures spinner clears |
