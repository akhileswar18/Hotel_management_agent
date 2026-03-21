# Contract: LLM Interaction Behavior

## Scope
Defines expected behavior for AI Agent Ask/Command interactions after OpenRouter provider integration.

## Inputs
- Interaction mode: `ask` or `command`
- User prompt text
- Active provider configuration

## Behavioral Contract
1. System MUST accept Ask-mode and Command-mode inputs from AI Agent screen.
2. When provider is available and credentials are valid, system MUST return a user-visible response.
3. Command-mode responses MUST produce either:
   - successful workflow execution outcome, or
   - explicit user-visible clarification/degraded message.
4. System MUST show provider identifier and model identifier in AI Agent UI state.
5. If provider is unavailable, system MUST return degraded non-blocking responses.
6. Provider failure MUST NOT prevent core non-AI workflows (POS, Billing, Inventory, Kitchen, Reports).

## Error/Degradation Contract
- Provider timeout/error -> response state `degraded`; no application crash.
- Invalid credentials/rate limits -> user-visible degraded response; retry remains possible.

## Acceptance Signals
- Ask-mode success rate and Command-mode execution metrics align with spec success criteria.
- No blocking runtime exceptions during AI interactions.
