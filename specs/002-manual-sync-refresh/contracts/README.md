# Contracts: Manual Sync / Refresh Button

**No new API contracts are needed for this feature.**

This is a UI-only feature. The refresh button calls existing backend API endpoints:

| Endpoint | Method | Used By Screen |
|----------|--------|----------------|
| `/api/inventory/items` | GET | POSScreen, ProductsScreen |
| `/api/reports/daily-sales` | GET | ReportsScreen |
| `/api/reports/inventory-snapshot` | GET | ReportsScreen |
| `/api/sales/orders` | GET | OrderHistoryScreen |
| `/api/users` | GET | UserMgmtScreen |

## Component Contract: RefreshButton

### Input
- `on_refresh: Callable` — the data-loading function to call
- `page: ft.Page` — page reference for toast notifications
- `tooltip: str` — optional tooltip (default: "Refresh data")

### Behavior Contract
1. Ignores taps within 2 seconds of the last refresh (debounce)
2. Shows spinner while `on_refresh()` executes
3. On success: restores icon, shows "Data refreshed" toast
4. On error: restores icon, shows error toast, retains existing data
5. Never modifies screen state beyond what `on_refresh()` does
