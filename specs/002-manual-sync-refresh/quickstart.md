# Quickstart: Manual Sync / Refresh Button

**Feature**: 002-manual-sync-refresh

## What This Feature Does

Adds a consistent **Refresh** button to every screen in the HMS Flet UI. Users can tap it to manually reload data from the backend when automatic updates are insufficient.

## How It Works

1. A reusable `RefreshButton` component lives in `src/ui/components/ui_helpers.py`
2. Each screen imports and places `RefreshButton` in its header/toolbar area
3. On tap → debounce check (2s) → spinner → call screen's data loader → toast result
4. No new backend endpoints — uses existing API

## Files Changed

| File | Change |
|------|--------|
| `src/ui/components/ui_helpers.py` | Add `RefreshButton` class |
| `src/ui/screens/pos_screen.py` | Add RefreshButton to header row |
| `src/ui/screens/products_screen.py` | Add RefreshButton to header row |
| `src/ui/screens/reports_screen.py` | Replace ad-hoc refresh with RefreshButton |
| `src/ui/screens/order_history_screen.py` | Add RefreshButton to header row |
| `src/ui/screens/user_mgmt_screen.py` | Replace ad-hoc refresh_btn with RefreshButton |
| `src/ui/screens/chat_screen.py` | Add RefreshButton to header row |

## How to Test

```bash
# Run existing smoke tests (should still pass)
python -m pytest tests/smoke/ -v

# Run the app and manually verify
python -m src

# Manual test:
# 1. Login as cashier
# 2. Go to POS screen → see refresh icon in top-right
# 3. Add a product via Products screen
# 4. Go back to POS → press Refresh → new product appears
# 5. Check that draft order is preserved
```

## Design Decisions

- **Reusable component**: One `RefreshButton` class for all screens ensures visual and behavioral consistency
- **Debounce**: 2-second cooldown prevents accidental rapid taps from hammering the backend
- **State preservation**: Refresh only reloads display data, never clears draft orders or filters
- **Error handling**: On failure, shows error toast and keeps existing data visible
