# Quickstart: HMA Production Stabilization & OpenRouter LLM Integration

## Prerequisites

- Repository root: `C:\Users\akhil\Hotel_management_agent`
- Existing environment dependencies installed
- Valid runtime config file with OpenRouter variables present for online AI validation

## Launch and Restart Discipline

Use full restart for validation cycles:

```powershell
python src/launcher.py
```

Expected runtime:

- FastAPI: `http://127.0.0.1:8000`
- Flet UI: `http://127.0.0.1:8080`

## Verification Sequence

1. Start application and confirm no startup traceback in terminal.
2. Log in with manager credentials and confirm dashboard render.
3. Navigate through POS, Inventory, Billing, Reports, Kitchen, and Chat; confirm each renders.
4. On Billing, confirm left panel is visible and payment flow is interactive.
5. On POS, create and finalize an order.
6. On Inventory, confirm item grid visibility and non-crashing image fallback behavior.
7. On Reports, confirm daily report visibility and date interaction.
8. On Kitchen, confirm order status controls work.
9. On Chat Ask mode, submit a business question and confirm response.
10. On Chat Command mode, submit an order command and confirm operational effect.
11. Confirm chat shows agent health plus provider/model metadata.
12. Simulate provider unavailability and confirm degraded AI responses while core operations still work.

## Asset Validation

- Check an expected asset URL path from the running app.
- If image route does not resolve to image content, re-verify app asset path configuration and perform full restart.

## Regression Guardrails

- No changes outside approved file scope.
- No new dependency installation.
- No runtime `AttributeError` or `TypeError` during normal navigation/workflows.

## Validation Run Notes (2026-03-21)

- Icon API runtime check: `Icons=False`, `icons=True`.
- ElevatedButton constructor check: positional argument works (`OK`).
- Asset URL check: `http://localhost:8080/images/paneer_tikka.jpg` returned `200` with `image/jpeg`.
- API smoke check: `http://127.0.0.1:8000/docs` returned `200`.
- Command workflow check: `/api/voice/text-command` successfully created orders with manager `user_id`.
- Ask workflow status: `/api/insights/query` returns backend error message `no such column: p.payment_method` (existing backend issue outside UI/llm_client scope).
- Outage behavior check: with invalid `OPENROUTER_API_KEY`, command workflow still succeeded (graceful fallback path remained operational).
