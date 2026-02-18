# Tasks: LLM Intent Parsing + Orchestrator Bug Fix

## Phase 1: Critical Bug Fixes (P0)

- [x] T001 Fix text-command endpoint to check `result.event.type` for `workflow.failed` vs `workflow.completed` — `src/api/app.py`
- [x] T002 Remove `order.created` from AUTO_REDISPATCH_TYPES (unnecessary noise) — `src/events/bus.py`
- [x] T003 Add logging to OrchestratorAgent._execute_steps for each step result — `src/agents/orchestrator_agent.py`
- [x] T004 Smoke test: verify "create order with items" → "finalize" works end-to-end

## Phase 2: LLM Client Enhancement (Foundation)

- [x] T005 Add Groq provider support to LLMClient (OpenAI-compatible API at api.groq.com) — `src/agents/llm_client.py`
- [x] T006 Add `GROQ_API_KEY` / provider config to `.env.example` — `.env.example`
- [x] T007 Add `parse_with_llm()` method to IntentParser — `src/voice/intent_parser.py`
- [x] T008 Create LLM system prompt for command parsing (returns JSON intent) — `src/voice/intent_parser.py`
- [x] T009 Implement try-LLM-then-fallback-to-rules flow in IntentParser.parse() — `src/voice/intent_parser.py`

## Phase 3: Insight Mode Fix

- [x] T010 Fix InsightAgent to build data-enriched prompts with rule-based fallback — `src/agents/insight_agent.py`
- [x] T011 Fix InsightAgent fallback: always return useful rule-based answers when LLM unavailable — `src/agents/insight_agent.py`

## Phase 4: Integration + Polish

- [x] T012 Update ChatScreen to show "[AI]" or "[Data]" indicator in responses — `src/ui/screens/chat_screen.py`
- [x] T013 Update plan.md with LLM integration details — `specs/003-llm-intent-parsing/plan.md`
- [x] T014 End-to-end test: Command mode with LLM parsing
- [x] T015 End-to-end test: Ask mode with LLM answering
