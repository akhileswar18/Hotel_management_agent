# Progress

Updated: 2026-03-21

## Partial Completion Summary

- Feature branch status is **partial completion with blockers** for `001-stabilize-hma-openrouter`.
- Task progress in `specs/001-stabilize-hma-openrouter/tasks.md`: **37 / 51 complete**.
- Core stabilization and OpenRouter wiring work has been applied, with remaining items primarily in manual UI verification and frozen-layer backend/test blockers.

## Completed in This Pass

- Added OpenRouter provider support in `src/agents/llm_client.py`:
  - provider defaults
  - API key routing
  - base URL routing
  - availability checks
  - query dispatch
  - OpenRouter headers (`HTTP-Referer`, `X-Title`)
- Updated AI provider/model card to dynamic env-driven values in `src/ui/screens/chat_screen.py`.
- Fixed remaining Flet compatibility issues found in scope:
  - removed unsupported `letter_spacing` usage in `src/ui/screens/products_screen.py`
  - migrated deprecated `ft.ElevatedButton(text=...)` call in `src/ui/screens/receipt_screen.py` to positional arg
  - stabilized route/sidebar update lifecycle in `src/ui/app.py`
  - guarded toast updates during remount timing in `src/ui/components/ui_helpers.py`
- Updated runtime config compatibility:
  - `.env` OpenRouter entries set
  - `VOICE_FALLBACK_LANGUAGES` JSON format corrected
  - `src/config/settings.py` switched to tolerant settings parsing (`extra="ignore"`)
- Verified runtime checks:
  - `http://127.0.0.1:8000/docs` returns `200`
  - `http://localhost:8080/images/paneer_tikka.jpg` returns `200` and `image/jpeg`
  - command-mode API path (`/api/voice/text-command`) executes successfully with valid manager user id
- Updated docs and troubleshooting:
  - `SKILLS.md` updated with concise error/root-cause/fix/prevention notes
  - feature run notes added to `specs/001-stabilize-hma-openrouter/quickstart.md` and `research.md`

## Verified Blockers

- **Ask-mode insight endpoint blocker (frozen layer)**:
  - `POST /api/insights/query` currently returns `no such column: p.payment_method`
  - This prevents full completion of Ask-mode acceptance tasks without backend/query fixes outside in-scope UI/LLM file set.
- **Regression suite blocker**:
  - `pytest tests/ -x -q` currently fails at:
    - `tests/contract/test_agent_contracts.py::TestAgentContracts::test_payment_agent_writes_to_db_does_not_use_llm`
    - observed assertion: `PaymentAgent.writes_to_db is False` (expected True)
  - This is not introduced by current in-scope UI/LLM changes and requires agent-layer contract remediation.
- **Manual UI verification still pending**:
  - several screen-by-screen click-through tasks remain open in `tasks.md` and require interactive browser confirmation.

## Remaining Open Tasks (High Level)

- Manual foundational/UI verification tasks: `T027`, `T035-T042`, `T048`
- Ask-mode verification tasks blocked by insight SQL error: `T032`, `T034`
- Full regression completion blocked by failing contract test: `T049`
- Final progress closeout after blockers clear: `T051`

## Next Action (No Code Changes Requested)

- Keep implementation code as-is for now.
- Resolve or approve exceptions for frozen-layer blockers (insight query + failing contract test), then complete remaining manual verification and closeout tasks.
