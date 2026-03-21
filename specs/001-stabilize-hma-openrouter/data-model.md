# Data Model: HMA Production Stabilization & OpenRouter LLM Integration

## Overview

This feature introduces no new business entities or schema changes. It formalizes operational view models and interaction records used for stabilization validation.

## Entities

### ScreenRenderState

**Purpose**: Tracks whether each primary screen loads successfully and is interactive.

**Fields**:

- `screen_name`: one of login, dashboard, pos, inventory, billing, reports, kitchen, chat
- `render_status`: loaded, empty_state, failed
- `error_signature`: optional runtime error identifier
- `checked_at`: timestamp of verification

**Validation Rules**:

- `screen_name` must map to a supported primary screen.
- `render_status` cannot be `failed` for production-ready acceptance.

### WorkflowExecutionRecord

**Purpose**: Captures outcome of a core operational workflow run during verification.

**Fields**:

- `workflow_name`: login, pos_finalize, billing_payment, kitchen_status_update, report_view, chat_ask, chat_command
- `result`: success, degraded_success, failed
- `duration_seconds`: measured completion time
- `notes`: optional context

**Validation Rules**:

- `duration_seconds` must be non-negative.
- `result` must be one of allowed values.
- `degraded_success` is valid only for AI-related flows when provider is unavailable.

### LLMProviderStatus

**Purpose**: Represents runtime AI provider state shown to operators.

**Fields**:

- `provider_name`: configured provider label
- `model_name`: active model identifier
- `connectivity`: reachable, unreachable
- `fallback_mode`: enabled, disabled
- `last_checked_at`: timestamp

**Validation Rules**:

- `provider_name` and `model_name` must be displayed in chat screen metadata.
- `fallback_mode` must be enabled when `connectivity` is `unreachable`.

### AgentHealthIndicator

**Purpose**: User-visible health snapshot for participating operational agents.

**Fields**:

- `agent_name`
- `health_state`: healthy, degraded, unavailable
- `last_activity_at`

**Validation Rules**:

- Every displayed agent must have a non-empty health state.
- Health state transitions must be reflected without crashing chat screen rendering.

### AssetResolutionState

**Purpose**: Tracks whether catalog images resolve for POS/Inventory display.

**Fields**:

- `asset_path`
- `resolution_state`: resolved, fallback_used, missing
- `checked_at`

**Validation Rules**:

- Missing assets must map to `fallback_used` or `missing` without blocking screen rendering.

## Relationships

- One `ScreenRenderState` entry exists per screen verification pass.
- One `WorkflowExecutionRecord` is linked to one or more `ScreenRenderState` entries.
- `LLMProviderStatus` and `AgentHealthIndicator` are displayed together within chat workflow verification.
- `AssetResolutionState` influences POS and Inventory `ScreenRenderState` outcomes.
