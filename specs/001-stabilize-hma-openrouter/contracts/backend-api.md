# Contract: Backend and Provider Interaction Expectations

## Scope

Defines externally observable behavior relied on by stabilization work, without introducing new backend endpoints.

## Existing Service Contracts to Preserve

- Authentication/login flow remains unchanged and must still permit manager access.
- Order creation/finalization and payment completion flows remain unchanged in endpoint shape and semantics.
- Reporting retrieval flow remains unchanged and must continue supporting date-based queries.

## LLM Provider Contract (OpenRouter via existing LLM client)

- Provider selection must accept OpenRouter as a valid configured provider.
- Ask mode requests must return a structured assistant response or a degraded fallback response.
- Command mode requests must return execution intent outcome or a degraded fallback response.
- Provider metadata returned/displayed to UI must include active provider and model name.
- If provider connectivity fails, the system must return a user-visible degraded response and preserve non-AI operations.

## Failure Behavior Contract

- Runtime provider failures must not crash the chat screen.
- Runtime provider failures must not block POS, inventory, billing, reports, or kitchen workflows.
- Missing/invalid provider configuration must surface as degraded AI behavior, not application startup failure.
