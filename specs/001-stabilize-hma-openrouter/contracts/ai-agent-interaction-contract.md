# Contract: AI Agent Interaction

## Scope
Defines externally visible behavior of the AI Agent screen for Ask and Command modes.

## Inputs
- mode: `ask` or `command`
- user_text: non-empty natural language input
- session_context: authenticated manager session

## Behavioral Contract
1. Ask mode must return a user-readable answer grounded in available operational data.
2. Command mode must attempt intent interpretation and execute mapped operational workflow when valid.
3. If external provider is unreachable, system must return degraded but user-visible response and keep application operational.
4. Response must include outcome classification: success, partial, failed, or degraded.

## Output Expectations
- user_response_text: always present
- provider_metadata: present when online provider is used
- execution_effect: present for command mode (created/updated/no-op/failed)
- error_visibility: failures must be surfaced to user, not silent

## Non-Goals
- No new command categories beyond existing supported workflows.
- No changes to backend endpoint surface.
