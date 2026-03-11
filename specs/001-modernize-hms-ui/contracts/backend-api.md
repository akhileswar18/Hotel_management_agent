# Backend API Contract: Modernized HMS UI

## Scope

This feature keeps all existing backend behavior intact and adds only the following contract changes:

1. `GET /api/audit/log`
2. `PATCH /api/sales/orders/{order_id}/kitchen-status`
3. `kitchen_status` added to order payloads returned by existing order-read endpoints

## 1. GET /api/audit/log

**Purpose**: Provide recent operational activity for the dashboard activity feed and AI event log.

**Request**:

- Method: `GET`
- Path: `/api/audit/log`
- Query params:
  - `limit` integer, optional, default `50`
  - `offset` integer, optional, default `0`

**Response**: `200 OK`

```json
[
  {
    "id": "string",
    "event_type": "order.created",
    "description": "Created order for table 5",
    "user_id": "string",
    "created_at": "2026-03-11T01:00:00Z",
    "metadata": {
      "entity_id": "string",
      "operation": "CREATE"
    }
  }
]
```

**Contract Rules**:

- Results are returned newest-first.
- `description` must be human-readable and safe for direct UI display.
- `event_type` is a normalized event family string derived from stored audit information.
- `metadata` is optional and may be empty when no extra display context exists.
- The endpoint is read-only and must not change audit persistence behavior.

## 2. PATCH /api/sales/orders/{order_id}/kitchen-status

**Purpose**: Persist kitchen workflow progression without altering the existing order business lifecycle.

**Request**:

- Method: `PATCH`
- Path: `/api/sales/orders/{order_id}/kitchen-status`
- Body:

```json
{
  "kitchen_status": "COOKING"
}
```

**Valid values**:

- `PENDING`
- `COOKING`
- `READY`
- `SERVED`

**Response**: `200 OK`

Returns the updated order payload using the same structure as current order responses, with `kitchen_status` included.

**Contract Rules**:

- Unknown order IDs return `404`.
- Invalid kitchen status values return `400`.
- Endpoint is available to logged-in operational users; no new role model is introduced by this feature.
- Updating `kitchen_status` must not mutate existing order totals, items, payment state, or current business `status`.

## 3. Existing Order Read Contract Extension

**Affected endpoints**:

- `GET /api/sales/orders`
- `GET /api/sales/orders/{order_id}`
- Any existing order mutation endpoint that returns the updated order payload

**Added field**:

```json
{
  "kitchen_status": "PENDING"
}
```

**Contract Rules**:

- Existing response fields remain unchanged.
- Legacy rows without an explicit value must surface as `PENDING`.
- `kitchen_status` is additive metadata and does not replace current order `status`.
