# Quickstart: Modernized HMS UI

## Purpose

Use this guide to validate the redesign incrementally while keeping the existing application stack and workflows intact.

## Prerequisites

- Repository root: `C:\Users\akhil\Hotel_management_agent`
- Python environment with the existing project dependencies installed
- No additional packages installed for this feature

## Launch

From `C:\Users\akhil\Hotel_management_agent`:

```powershell
python src/launcher.py
```

Expected runtime:

- FastAPI available on `http://127.0.0.1:8000`
- Flet UI available on `http://127.0.0.1:8080`

## Incremental Validation Sequence

1. **Design foundation**
   Confirm `ui_helpers.py` imports cleanly and shared builders render without startup errors.

2. **Backend additions**
   Verify `GET /api/audit/log` returns a list and `PATCH /api/sales/orders/{id}/kitchen-status` updates only kitchen workflow metadata.

3. **App shell**
   Confirm dark background, custom side navigation, shared header, and dashboard-first login flow.

4. **Dashboard**
   Confirm greeting, summary cards, active orders, recent activity, and payment breakdown render with live or fallback data.

5. **POS**
   Confirm category tabs filter menu items, out-of-stock items cannot be added, and existing keyboard shortcuts still work.

6. **Kitchen display**
   Confirm ticket urgency states, timer refresh, individual item completion, and order-ready transitions update `kitchen_status`.

7. **AI Agent screen**
   Confirm three-panel layout, mode switching, command trace display, clarification chips, and live activity feed.

8. **Reports**
   Confirm hourly bars, payment bars, top-item ranking, inventory snapshot, and CSV exports.

9. **Inventory**
   Confirm alert sidebar, stock table, status badges, stock bars, and ledger section.

10. **Login**
    Confirm role chips, PIN dots, offline-ready badge, and dashboard redirect after successful login.

11. **Billing**
    Confirm payment-method selection, change calculation, receipt preview, and invoice reprint access.

## Regression Checks

- Run the existing test suite relevant to touched areas.
- Confirm no domain, service, repository, agent, or voice module behavior changed.
- Confirm POS shortcuts remain: `F2`, `F5`, `F8`, `F9`, `Esc`.
- Confirm all primary interactive controls remain at least 48px high.
