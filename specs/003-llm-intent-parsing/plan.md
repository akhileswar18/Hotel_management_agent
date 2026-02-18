# Implementation Plan: LLM-Based Intent Parsing + Bug Fixes

**Feature**: 003-llm-intent-parsing  
**Created**: 2026-02-15  
**Status**: Complete

## Architecture

### Two-Tier Parsing Strategy

```
User Input
    │
    ▼
┌──────────────┐      ┌──────────────────┐
│  LLM Parser  │─yes─▶│ Return LLM intent│──▶ Enrich item_ids from DB
│  (Groq/OAI)  │      └──────────────────┘
└──────┬───────┘
       │ no/fail
       ▼
┌──────────────┐      ┌──────────────────┐
│  Rule-Based  │─────▶│ Return rule intent│
│  (Keywords)  │      └──────────────────┘
└──────────────┘
```

### Components Modified

1. **`src/agents/llm_client.py`** — LLMClient  
   - Added Groq provider support (OpenAI-compatible API at api.groq.com)
   - Default models per provider (Groq: llama-3.3-70b-versatile)
   - `is_available` property for quick availability check
   - Provider-specific env var handling (GROQ_API_KEY)

2. **`src/voice/intent_parser.py`** — IntentParser  
   - `parse()`: Try LLM first → fallback to rule-based `_parse_rule_based()`
   - `_parse_with_llm()`: Sends text + catalog context to LLM with structured system prompt
   - `_enrich_item_ids()`: Matches LLM-returned item names against inventory DB
   - `_followup_with_llm()`: Uses LLM for follow-up context merging
   - `_get_catalog_hint()`: Provides menu item names for LLM context
   - All responses include `_parsed_by` marker ("llm" or "rules")

3. **`src/agents/insight_agent.py`** — InsightAgent  
   - `_handle_query()`: LLM first, then rule-based `_rule_based_answer()` fallback
   - `_analyze_trends()`: LLM first, then data summary fallback
   - `_suggest_upsell()`: LLM first, then popular-items-minus-order fallback
   - Never returns `insight.unavailable` — always provides useful data

4. **`src/api/app.py`** — Text-command endpoint  
   - `create_order`: Checks `result.event.type` for `workflow.failed`
   - All responses include `parsed_by` indicator
   - Insight query endpoint returns data even without LLM

5. **`src/agents/orchestrator_agent.py`** — OrchestratorAgent  
   - Added detailed logging for each workflow step
   - Logs step results, failures, and rollbacks

6. **`src/events/bus.py`** — EventBus  
   - Removed `order.created` from AUTO_REDISPATCH_TYPES (was noise)

## LLM Provider Configuration

```env
# Groq (recommended — fast, free tier)
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
LLM_MODEL=llama-3.3-70b-versatile

# OpenAI
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# Ollama (local, no API key)
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2
```

## Bug Fixes

1. **Orchestrator "no items" bug**: Text-command endpoint was returning "Order created successfully!" even when OrchestratorAgent returned `workflow.failed`. Fixed by checking `result.event.type`.

2. **"Insight unavailable" in Ask mode**: InsightAgent now always provides an answer via rule-based data summary when LLM is down. Never returns `insight.unavailable` for queries.

## Testing

- Both modes work without any LLM configured (100% rule-based)
- With Groq API key: LLM handles ambiguous commands, provides richer insights
- `[AI]` tag shown in UI when LLM processed the request
- `[Data]` tag shown when rule-based fallback was used
