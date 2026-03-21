# Phase 0 Research: HMA Production Stabilization & OpenRouter LLM Integration

## Decision: Route OpenRouter through the existing OpenAI-compatible client path

**Rationale**: OpenRouter uses OpenAI-compatible chat completion semantics. Reusing the existing compatible query flow minimizes regression risk and keeps changes localized to provider routing, base URL, and required provider headers.

**Alternatives considered**:

- Implement a separate OpenRouter query method: rejected due duplicated request/response logic and increased maintenance surface.
- Replace current providers with OpenRouter-only: rejected because it weakens fallback flexibility.

## Decision: Use verify-first patching for all previously attempted fixes

**Rationale**: Prior fix notes exist but may not match current source state. Verifying file-by-file before edits prevents duplicate or conflicting patches and reduces accidental regressions.

**Alternatives considered**:

- Re-apply all historical fixes blindly: rejected because it can overwrite valid code and introduce new breakage.
- Skip verification and rely on runtime only: rejected because root-cause isolation becomes slower.

## Decision: Resolve icon API compatibility by runtime capability check, then enforce one casing consistently

**Rationale**: Flet 0.80.5 builds can expose `ft.Icons`, `ft.icons`, or both. Runtime detection avoids assumptions and allows deterministic code normalization.

**Alternatives considered**:

- Hardcode one icon namespace globally: rejected due environment-dependent breakage risk.
- Leave mixed usage as-is: rejected due inconsistent runtime behavior across screens.

## Decision: Preserve redesigned billing UX and remove only incompatibility triggers

**Rationale**: The redesigned billing flow aligns with intended UX. Stabilization should target crash vectors (unsupported parameters and init-order issues) without reverting screen behavior.

**Alternatives considered**:

- Full file rollback to pre-modernization billing: rejected because it discards approved UI improvements.
- Partial selective revert with ad-hoc patches: rejected because it increases merge complexity.

## Decision: Validate production readiness via deterministic end-to-end checklist, not visual spot checks

**Rationale**: This feature is stabilization-focused with explicit screen/workflow success criteria. A repeatable checklist with expected outcomes ensures confidence and catches silent failures.

**Alternatives considered**:

- Ad-hoc manual exploration: rejected as non-repeatable and prone to missed regressions.
- Automated-only validation: rejected because UI/runtime incompatibilities require interactive confirmation in this stack.

## Decision: Keep outage behavior explicit for AI flows

**Rationale**: Agent-first value requires live AI when available, but operations must continue when unavailable. Explicit degraded response expectations avoid hidden coupling between LLM reachability and operational continuity.

**Alternatives considered**:

- Fail closed when provider is down: rejected because it violates offline-first operational reliability.
- Silent fallback without user-visible status: rejected because it reduces operator trust and observability.

## Runtime Findings (2026-03-21)

## Decision: Keep command-mode validation blocked on real authenticated user context

**Rationale**: Direct API command tests with empty `user_id` can fail with foreign-key errors even when command parsing is valid. Using a real manager `user_id` validates actual execution path used by UI sessions.

**Alternatives considered**:

- Treat empty-`user_id` API failure as command regression: rejected because UI always supplies authenticated user context.

## Decision: Flag Ask-mode SQL failure as external blocker to full US1 acceptance

**Rationale**: `POST /api/insights/query` currently returns `no such column: p.payment_method`, indicating a backend query issue outside allowed modification scope for this stabilization pass.

**Alternatives considered**:

- Patch frozen backend/reporting logic in this pass: rejected due explicit frozen-layer constraints.
