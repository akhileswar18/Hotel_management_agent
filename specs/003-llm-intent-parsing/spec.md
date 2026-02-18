# Feature Specification: LLM-Based Intent Parsing + Orchestrator Bug Fix

**Feature Branch**: `003-llm-intent-parsing`  
**Created**: 2026-02-15  
**Status**: Implementation

## Summary

Use LLM (Groq/OpenAI/Ollama) for understanding user inputs in both Ask/Insights and Command modes in the Chat screen. Keep rule-based IntentParser as fallback when LLM is unavailable. Also fix the orchestrator bug where items are not being added to orders via the EventBus workflow.

## User Stories

### US1: LLM-powered command parsing (P1)
As a cashier, I want the Command mode to use an LLM to understand my natural language commands so that I don't have to use exact keywords.

### US2: LLM-powered insights (P1)
As a manager, I want the Ask/Insights mode to use an LLM to answer questions about sales, inventory, and operations using real data.

### US3: Orchestrator bug fix (P0 - Critical)
As a user, I want "create order for table 5 with 3 coke" followed by "finalize order pay cash" to work correctly end-to-end.

## Root Cause Analysis — Orchestrator Bug

Two bugs identified:

1. **Text-command endpoint doesn't check workflow result type**: Returns "Order created successfully!" even when the orchestrator returns `workflow.failed`. The endpoint checks `result.success` (EventBus dispatch success) but not `result.event.type` (workflow outcome).

2. **`order.created` in AUTO_REDISPATCH_TYPES is unnecessary noise**: Auto re-dispatching `order.created` doesn't trigger any useful downstream agent. Only AuditAgent handles it via wildcard, creating duplicate audit entries.

## Functional Requirements

- FR-001: LLM parses natural language into structured intent JSON (same format as rule-based IntentParser)
- FR-002: Rule-based IntentParser remains as fallback when LLM is unavailable
- FR-003: LLM provider configurable via environment variables (GROQ, OpenAI, Ollama)
- FR-004: Ask/Insights mode uses LLM to answer questions with real DB data
- FR-005: Command mode uses LLM to parse commands into actionable intents
- FR-006: Text-command endpoint correctly reports workflow failures
- FR-007: Orchestrator properly adds items to orders during multi-step workflows

## Success Criteria

- SC-001: "create order for table 5 with 3 coke" creates an order WITH items
- SC-002: "finalize order pay cash" correctly finalizes the most recent draft order
- SC-003: Ask/Insights returns meaningful answers (not "Insight unavailable") when LLM is configured
- SC-004: System works 100% without LLM (falls back to rule-based parsing)
