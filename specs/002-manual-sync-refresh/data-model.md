# Data Model: Manual Sync / Refresh Button

**Feature**: 002-manual-sync-refresh  
**Date**: 2026-02-13

## Overview

This feature is **UI-only**. No new database tables, columns, or entities are required. The refresh button re-fetches data from existing backend API endpoints.

## Component Model

### RefreshButton (UI Component)

| Property | Type | Description |
|----------|------|-------------|
| `on_refresh` | `Callable` | Async or sync function to call when refresh is triggered |
| `page` | `ft.Page` | Page reference for showing toast notifications |
| `tooltip` | `str` | Tooltip text (default: "Refresh data") |

### Internal State

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `_is_refreshing` | `bool` | `False` | Whether a refresh is currently in progress |
| `_last_refresh_time` | `float` | `0.0` | Timestamp of last refresh (for debounce) |
| `DEBOUNCE_SECONDS` | `float` | `2.0` | Minimum interval between refreshes |

### State Transitions

```
IDLE --[tap]--> CHECK_DEBOUNCE
                    |
            +-------+-------+
            |               |
        [too soon]    [allowed]
            |               |
        IDLE          LOADING --[on_refresh()]--> RESULT
                                                    |
                                            +-------+-------+
                                            |               |
                                        [success]       [error]
                                            |               |
                                      TOAST_SUCCESS   TOAST_ERROR
                                            |               |
                                            +-------+-------+
                                                    |
                                                  IDLE
```

## Screen Integration Points

| Screen | Header Row Location | Callback | Preserves |
|--------|-------------------|----------|-----------|
| POSScreen | Top `ft.Row` (line ~124) | `_load_items` | draft order, table ID |
| ProductsScreen | Top `ft.Row` (line ~70) | `_load_items(category_filter.value)` | category filter |
| ReportsScreen | Top `ft.Row` (line ~202) | `_load_reports` | selected date, txn filters |
| OrderHistoryScreen | Top `ft.Row` (line ~83) | `_load_orders` | status/date filters |
| UserMgmtScreen | Header container (line ~52) | `_load_users` | none |
| ChatScreen | Top area (line ~31) | clear chat history | none |

## Existing API Endpoints Used (no changes)

| Endpoint | Used By |
|----------|---------|
| `GET /api/inventory/items` | POSScreen, ProductsScreen |
| `GET /api/reports/daily-sales` | ReportsScreen |
| `GET /api/reports/inventory-snapshot` | ReportsScreen |
| `GET /api/sales/orders` | OrderHistoryScreen |
| `GET /api/users` | UserMgmtScreen |
