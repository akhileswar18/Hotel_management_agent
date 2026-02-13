# Feature Specification: Manual Sync / Refresh Button

**Feature Branch**: `002-manual-sync-refresh`  
**Created**: 2026-02-13  
**Status**: Draft  
**Input**: User description: "I want refresh button in every screen so that if it doesn't sync automatic we should be able to sync manually"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Refresh Data on POS Screen (Priority: P1)

A cashier or waiter is on the POS screen taking an order. They notice the menu items or prices seem stale (e.g., a recently added product doesn't appear, or stock counts are outdated). They tap a visible **Refresh** button on the screen, and all data (menu items, stock availability, prices) reloads from the backend within a few seconds, without losing their current draft order.

**Why this priority**: The POS screen is the most-used screen in the entire system. Stale data here directly causes order errors (wrong prices, ordering out-of-stock items). This is the highest-impact screen for manual refresh.

**Independent Test**: Can be tested by adding a new product via the Products screen, switching to POS, observing it's missing, pressing Refresh, and confirming it now appears — all while a draft order remains intact.

**Acceptance Scenarios**:

1. **Given** a cashier is on the POS screen with a draft order, **When** they tap the Refresh button, **Then** menu items and stock levels reload from the server and the current draft order is preserved.
2. **Given** a new product was added by a manager on another device, **When** the cashier taps Refresh on POS, **Then** the new product appears in the item grid.
3. **Given** the backend server is temporarily unreachable, **When** the user taps Refresh, **Then** a clear error message is shown (e.g., "Could not refresh — server unavailable") and the existing data remains displayed.

---

### User Story 2 - Refresh Data on Products/Inventory Screen (Priority: P1)

A manager is on the Products screen reviewing inventory. Stock levels may be outdated because another staff member just recorded a stock-in. The manager taps the Refresh button, and all product listings, stock counts, and category filters reload with current data.

**Why this priority**: Inventory accuracy is critical for purchasing decisions and stock management. Tied with POS for highest priority since incorrect stock data leads to over/under-ordering.

**Independent Test**: Can be tested by recording a stock-in via the API, then pressing Refresh on the Products screen and verifying the updated stock count.

**Acceptance Scenarios**:

1. **Given** a manager is viewing the Products screen, **When** they tap Refresh, **Then** all item details, stock levels, and categories reload from the server.
2. **Given** the category filter is set to "Beverages", **When** the user taps Refresh, **Then** the data reloads but the selected filter is preserved.

---

### User Story 3 - Refresh Data on Reports Screen (Priority: P2)

A manager is viewing daily sales or inventory reports. The data shown may be from an earlier point in time. They tap Refresh to get the latest report data reflecting any orders finalized since the screen was loaded.

**Why this priority**: Reports are read-only and primarily used at end-of-day or periodically. Slightly lower priority than transactional screens, but still important for accurate decision-making.

**Independent Test**: Can be tested by finalizing an order, switching to Reports, pressing Refresh, and verifying the new transaction appears in the summary.

**Acceptance Scenarios**:

1. **Given** a manager is on the Reports screen viewing today's sales, **When** they tap Refresh, **Then** the sales summary, transaction list, and inventory snapshot reload with current data.
2. **Given** the user has selected a specific date filter, **When** they tap Refresh, **Then** the date filter is preserved and data for that date reloads.

---

### User Story 4 - Refresh Data on Order History Screen (Priority: P2)

A staff member is viewing order history. New orders may have been finalized since the screen was loaded. They tap Refresh to see the latest orders.

**Why this priority**: Order history is used for lookups and reprints. Important but less frequently accessed than POS or inventory.

**Independent Test**: Can be tested by finalizing a new order, pressing Refresh on Order History, and confirming it appears.

**Acceptance Scenarios**:

1. **Given** a user is on the Order History screen, **When** they tap Refresh, **Then** the order list reloads with any new orders, and current filter/search criteria are preserved.

---

### User Story 5 - Refresh Data on User Management and Chat Screens (Priority: P3)

A manager is on the User Management screen or any staff member is on the Chat screen. They tap Refresh to reload user lists or clear/reload chat context.

**Why this priority**: These screens change infrequently and are lower traffic. Included for completeness and consistency.

**Independent Test**: Can be tested by creating a new user via API, pressing Refresh on User Management, and confirming the new user appears.

**Acceptance Scenarios**:

1. **Given** a manager is on the User Management screen, **When** they tap Refresh, **Then** the user list reloads.
2. **Given** a user is on the Chat screen, **When** they tap Refresh, **Then** the chat history clears or reloads as appropriate.

---

### Edge Cases

- What happens when the user taps Refresh while a previous refresh is still in progress? (Should be debounced — ignore rapid repeated taps)
- What happens when the user taps Refresh during an active order creation? (Draft order state must be preserved)
- What happens when the backend is completely down? (Show clear error, retain existing data)
- What happens when the refresh returns data that conflicts with a user's in-progress action? (e.g., an item they added to an order is now out of stock — show a warning but don't remove the item automatically)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every main screen (POS, Products, Reports, Order History, User Management, Chat) MUST display a visible Refresh button in a consistent location.
- **FR-002**: Tapping the Refresh button MUST reload all data displayed on the current screen from the backend server.
- **FR-003**: The Refresh button MUST show a loading indicator (spinner or animation) while the refresh is in progress.
- **FR-004**: If the refresh fails (server unreachable, timeout, error), the system MUST display a user-friendly error message and retain the previously displayed data.
- **FR-005**: Refreshing MUST NOT discard or alter any in-progress user state (e.g., draft orders, selected filters, form inputs, search criteria).
- **FR-006**: The Refresh button MUST be debounced — rapid repeated taps within 2 seconds should only trigger one refresh.
- **FR-007**: The Refresh button MUST be placed in a consistent position across all screens (top-right area of the screen header) for discoverability and muscle memory.
- **FR-008**: After a successful refresh, the system SHOULD briefly indicate success (e.g., a subtle toast message "Data refreshed" or a brief color flash on the button).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can manually refresh any screen's data within 3 seconds (from tap to updated display) under normal conditions.
- **SC-002**: 100% of main application screens have a visible, functional Refresh button.
- **SC-003**: Draft orders and user-selected filters are preserved after refresh in 100% of cases.
- **SC-004**: When the backend is unreachable, users see a clear error message within 5 seconds and can continue working with existing data.
- **SC-005**: Repeated rapid taps on the Refresh button result in only one server request.

## Assumptions

- The Refresh button is a UI-only feature — it re-fetches data from the existing backend API endpoints. No new backend endpoints are needed.
- The backend API already supports all necessary data queries for each screen.
- "Sync" in the user's description refers to refreshing the UI's displayed data from the local backend, not cloud synchronization or multi-device sync.
- The existing offline-first architecture means the backend is local (SQLite), so refresh latency should be minimal.

## Scope Boundaries

- **In scope**: Adding a Refresh button to each screen that re-fetches and re-renders data.
- **Out of scope**: Automatic periodic refresh / polling, real-time push notifications, multi-device synchronization, background sync workers.
