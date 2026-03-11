# JS to Flet UI Migration Plan

Migration of the JS/Gemini AI Studio demo UI into the existing Python/Flet project: chat-order flow with confirmation, dark theme, new screens, LLM provider config, and deployment restructure.

**See also**: [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) for WatchdogAgent and parse failure path in the architecture.

---

## 1. Scope

- **Reference**: [legacy/JS_UI/](../legacy/JS_UI/) — CommandCenter (chat), POSSystem, OrderHistory, ProductManagement; dark theme (emerald/zinc), glass-panel styling.
- **Target**: Flet screens under [src/ui/](src/ui/), all backend via FastAPI; single start: `python src/launcher.py`.
- **LLM**: Temporary paid API (OpenAI/Groq); switch to Ollama via `LLM_PROVIDER=ollama` (one-line config).

---

## 2. Backend: Parse-Only and Execute-From-Intent

- **`POST /api/voice/parse`** — Body: `{ "text", "pending_intent" }`. Returns `{ intent, parsed_by, missing_fields, message }` only (no execution). Used by ChatOrderScreen before showing confirmation.
- **`POST /api/orders/from-intent`** — Body: `{ "intent", "user_id" }`. Validates `create_order`, publishes `workflow.multi_step`, returns order result. Used after user confirms on OrderConfirmationScreen.
- **Optional**: `POST /api/reports/close-day` for Daily Summary / Close Register.

---

## 3. Flet Screens

| Screen | Purpose |
|--------|---------|
| **ChatOrderScreen** | Natural-language order input; calls parse → on complete intent navigates to OrderConfirmationScreen. |
| **OrderConfirmationScreen** | Shows parsed items/table; Confirm → `POST /api/orders/from-intent`; Edit/Cancel. |
| **POSScreen** | Restyle to dark/emerald; categories, cart, table, 18% GST, Process Checkout. |
| **MenuManagementScreen** | Add/edit/delete menu items (refactor Products screen); all via existing API. |
| **DailySummaryScreen** | Daily summary + “Close Day” (call close-day or export). |

Theme: dark background, emerald accent, touch-friendly (min 48dp), high contrast.

---

## 4. Parse Failure Path and ChatOrderScreen Error Message

When the parse step fails (LLM timeout, garbage, or error), the flow is:

1. **API** receives parse request → **IntentParser.parse(text)**.
2. **LLM** fails (timeout / garbage / error) → **fallback** to **rule-based** parser.
3. If **rule-based returns valid intent** → return intent (`_parsed_by="rules"`).
4. If **rule-based also fails** (e.g. `action="unknown"`) → API returns `{ status: "error", message: "..." }`.
5. **ChatOrderScreen** (or Chat screen) **on error** shows:
   - **"Sorry, couldn't understand. Try again or use the menu buttons."**

No AI in the failure path — explicit fallback and a single, clear user-facing message.

---

## 5. WatchdogAgent (Add to Migration)

Implement **WatchdogAgent** as part of the migration so the app has explicit recovery for known failure modes.

- **File**: `src/agents/watchdog_agent.py`.
- **Role**: Monitor and auto-recover; rule-based only (no LLM).

| Failure mode | Recovery |
|--------------|----------|
| **API timeout** (LLM) | Retry up to 3 times → fallback to rule-based parsing (IntentParser already supports this; Watchdog can trigger retries or log). |
| **Printer failure** | Queue the bill; retry when printer reconnects (health check or `system.printer_ready`). |
| **Agent crash** | Auto-restart the agent (re-register with EventBus). |
| **Database lock** | Wait and retry with backoff (e.g. 3 retries: 100ms, 500ms, 2s). |

- **Events** (subscription map): `watchdog.check`, `system.printer_failed`, `system.agent_unhealthy`, `system.db_lock`.
- **Wire** in [src/api/app.py](src/api/app.py) with other agents; add to registry and EventBus.
- **File structure**: Add `watchdog_agent.py` under `src/agents/`.

---

## 6. Restructure and Deployment

- **Single start**: `python src/launcher.py` — DB init, FastAPI in background, Flet UI.
- **Legacy**: JS_UI moved to `legacy/JS_UI/`.
- **LLM default**: `LLM_PROVIDER=openai` or `groq` for paid API; document `LLM_PROVIDER=ollama` for later switch.
- All Flet screens call FastAPI only; no external JS or Gemini in the app.

---

## 7. File-Level Checklist

| Action | Path |
|--------|------|
| Create | `src/ui/screens/chat_order_screen.py` |
| Create | `src/ui/screens/order_confirmation_screen.py` |
| Create | `src/ui/screens/daily_summary_screen.py` |
| Create | `src/agents/watchdog_agent.py` |
| Add | `POST /api/voice/parse`, `POST /api/orders/from-intent` (optional `POST /api/reports/close-day`) in `src/api/app.py` |
| Update | `src/ui/screens/pos_screen.py` (dark theme, layout) |
| Update | `src/ui/screens/products_screen.py` → MenuManagementScreen |
| Update | `src/ui/app.py` (theme, routes, ChatOrder → OrderConfirmation flow, **error message**: "Sorry, couldn't understand. Try again or use the menu buttons.") |
| Update | `src/ui/components/ui_helpers.py` (dark palette, touch targets) |
| Update | `src/agents/llm_client.py` (default provider for paid API) |
| Wire | WatchdogAgent in `src/api/app.py` and AgentRegistry |
| Done | `JS_UI/` → `legacy/JS_UI/` |

---

## 8. End-to-End Flows

- **Order**: ChatOrderScreen → parse → OrderConfirmationScreen → confirm → `POST /api/orders/from-intent` → EventBus → agents (audit, inventory, print).
- **Billing**: POS finalize with 18% GST and discounts; display total; print (or queue via WatchdogAgent on printer failure).
- **Menu**: MenuManagementScreen CRUD via API → SQLite; reflected in POS and chat.
- **Close register**: DailySummaryScreen → daily summary → “Close Day” → persist/export.
- **Parse failure**: LLM fails → rule-based fallback → if both fail → API error → ChatOrderScreen shows “Sorry, couldn't understand. Try again or use the menu buttons.”
