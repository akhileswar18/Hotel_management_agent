# Screen Reference Screenshots

## Current UI (folder: current/)
These are screenshots of the EXISTING running app at localhost:8080.
They show what the UI looks like TODAY — what we are replacing.

| File | Screen | Route |
|------|--------|-------|
| 01_login.png | Login / PIN entry | /login |
| 02_pos.png | POS Order Entry | /pos |
| 03_menu_management.png | Inventory/Menu Management | /products |
| 04_order_history.png | Order History | /orders |
| 05_reports.png | Reports | /reports |
| 06_kitchen_queue.png | Kitchen Queue | /kitchen |

## Target UI (folder: target/)
These are screenshots taken from hms_figma_prototype.html — the design target.
When implementing each screen, open the corresponding target screenshot
and match it as closely as possible using Flet primitives.

| File | Screen | Key changes from current |
|------|--------|--------------------------|
| 01_login.png | Login | Dark bg, brand mark, role chips, animated PIN dots |
| 02_dashboard.png | Dashboard (NEW) | New screen — doesn't exist yet |
| 03_pos.png | POS | Menu card grid, category tabs, dark panels |
| 04_inventory.png | Inventory | Alert sidebar, stock bars, ledger section |
| 05_invoice.png | Invoice/Receipt | Split layout, receipt preview, payment cards |
| 06_reports.png | Reports | Bar chart, donut, top-5 ranking |
| 07_kitchen.png | Kitchen Display | Ticket cards, countdown timers, dark theme |
| 08_ai_agent.png | AI Agent | 3-panel layout, pipeline trace, EventBus log |

## How to use these in your prompts
When implementing a screen, reference the screenshots like this:
"Implement pos_screen.py to match .specify/screens/target/03_pos.png.
The current implementation looks like .specify/screens/current/02_pos.png."
```

### How to get the target screenshots:
1. Open `hms_figma_prototype.html` in Chrome
2. Click each screen tab
3. Press `Ctrl+Shift+P` → "Capture full size screenshot" (Chrome DevTools)
4. Save each to `.specify/screens/target/`

That's it. The agent can now read both folders when implementing.

---

## Updated `/speckit.plan` Prompt (with backend additions + screenshot references)
```
/speckit.plan

The application is already built and running. This plan covers UI layer changes 
plus 2 small backend additions required to support new screens. All other backend 
logic, domain rules, agents, and database schema remain completely unchanged.

EXISTING TECH STACK (do not change):
- Runtime: Python 3.11+
- UI Framework: Flet 0.80.5 (Python Flutter wrapper, runs as web app at localhost:8080)
- Backend: FastAPI (runs at localhost:8000, all existing endpoints remain untouched)
- Database: SQLite via custom repository pattern (src/infrastructure/)
- HTTP client inside UI: httpx in synchronous mode only (httpx.Client, NOT async)
- AI/LLM: Groq API (llama-3.3-70b) with rule-based fallback via OrchestratorAgent

VISUAL REFERENCE SCREENSHOTS:
All screen designs are available as reference images in .specify/screens/.
- .specify/screens/current/ → existing running UI (what we are replacing)
- .specify/screens/target/  → target design from hms_figma_prototype.html
When implementing each screen, always open both the current and target screenshots 
to understand what is changing. The HTML prototype at hms_figma_prototype.html in 
the project root is the interactive reference — open it in a browser to see all 
8 screens with hover states and interactions.

EXISTING FILE STRUCTURE:
src/
├── api/app.py                     ← ONLY add 2 endpoints (see below), nothing else
├── domain/                        ← DO NOT TOUCH
├── application/services.py        ← DO NOT TOUCH
├── infrastructure/                ← DO NOT TOUCH
├── agents/                        ← DO NOT TOUCH (11 agents)
├── voice/                         ← DO NOT TOUCH (STT, TTS, IntentParser)
└── ui/
    ├── app.py                     ← MODIFY (theme, sidenav, header)
    ├── components/
    │   └── ui_helpers.py          ← MODIFY (HMSColors, components, helpers)
    └── screens/
        ├── auth_screen.py         ← MODIFY
        ├── pos_screen.py          ← MODIFY (highest priority)
        ├── products_screen.py     ← MODIFY (inventory)
        ├── reports_screen.py      ← MODIFY
        ├── receipt_screen.py      ← MODIFY (invoice/billing)
        ├── order_history_screen.py← MODIFY → repurpose as Kitchen Display
        ├── chat_screen.py         ← MODIFY → AI Agent 3-panel layout
        └── dashboard_screen.py    ← CREATE NEW FILE


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION A: MINIMAL BACKEND ADDITIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Only 2 backend changes are needed. Add both to src/api/app.py only.
Do not touch any service, repository, domain, or agent file.

ADDITION 1 — Expose Audit Log (needed by: Dashboard activity feed + AI Agent EventBus panel)
The AuditAgent already writes events to the database. We just need a GET endpoint to read them.

  Endpoint: GET /api/audit/log
  Query params: limit (int, default 50), offset (int, default 0)
  Response: list of {
    id: str,
    event_type: str,        (e.g. "order.created", "payment.completed", "inventory.deducted")
    description: str,       (human-readable summary)
    user_id: str,
    created_at: datetime,
    metadata: dict          (optional extra context)
  }
  Implementation: Query the existing audit log table via the existing repository.
  No new table, no schema change.

ADDITION 2 — Kitchen Status on Orders (needed by: Dashboard active orders + Kitchen Display)
Orders currently have status DRAFT or FINALIZED. Kitchen staff need to mark 
progression through cooking stages. Add a kitchen_status field to the order model.

  Schema change: Add kitchen_status column to orders table
    kitchen_status VARCHAR default "PENDING"
    valid values: "PENDING" | "COOKING" | "READY" | "SERVED"

  Endpoint: PATCH /api/sales/orders/{order_id}/kitchen-status
  Request body: { "kitchen_status": "COOKING" }
  Response: updated order object
  Permission: any authenticated user (kitchen staff, manager)

  Also: include kitchen_status in the response of GET /api/sales/orders
  so the Dashboard and Kitchen Display can show it without extra calls.

These 2 additions are the ONLY backend changes. Everything else in src/api/app.py 
remains exactly as written. All 25+ existing endpoints stay unchanged.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION B: DESIGN SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Replace the HMSColors class in ui_helpers.py with this dark palette.
This is the single source of truth — all screens import only from HMSColors.

  BG          = "#0E1117"    # Page background
  SURFACE     = "#161B27"    # Cards, panels
  SURFACE2    = "#1E2535"    # Input fields, nested sections
  BORDER      = "#2A3349"    # All borders and dividers
  ACCENT      = "#FF6B35"    # Primary action (buttons, active nav)
  ACCENT2     = "#FFB347"    # Prices, totals, amber highlights
  SUCCESS     = "#22C55E"    # In stock, paid, confirmed
  WARNING     = "#EAB308"    # Low stock, held orders
  ERROR       = "#EF4444"    # Out of stock, void, critical
  BLUE        = "#3B82F6"    # Card payment, info, AI agents
  TEXT_PRIMARY    = "#F0F4FF"
  TEXT_SECONDARY  = "#8B96B0"
  TEXT_MUTED      = "#4B5675"
  TEXT_LIGHT      = "#FFFFFF"
  BG_PRIMARY      = "#0E1117"    # keep for backward compatibility
  BG_SECONDARY    = "#161B27"    # keep for backward compatibility


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION C: ARCHITECTURE DECISIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. THEME
   In app.py __init__:
     self.page.theme_mode = ft.ThemeMode.DARK
     self.page.bgcolor = "#0E1117"
     self.page.padding = 0

2. NAVIGATION SIDEBAR
   Replace existing NavigationRail with a custom fixed 72px sidebar:
   ft.Container(width=72, bgcolor="#0A0D14") containing ft.Column of nav items.
   Each nav item: ft.IconButton in ft.Container(border_radius=10).
   Active item: bgcolor=ACCENT, icon_color=WHITE.
   Red dot badge overlay (ft.Stack) on Inventory icon when low stock count > 0.
   Nav order: Dashboard → POS → Inventory → Invoice → Reports → [spacer] 
              → Kitchen → AI Agent → Logout.

3. SHARED HEADER
   Add build_header(screen_title, current_user) to ui_helpers.py.
   Returns ft.Container(height=56) containing ft.Row with:
   - Left: "HMS" in orange bold + screen title in grey
   - Center: empty expand
   - Right: green dot + "OFFLINE READY" badge, clock text, user avatar chip
   Used on every screen except Kitchen (which is fullscreen dark).

4. DATA LOADING PATTERN
   Keep the exact existing pattern — synchronous httpx.Client in __init__ and 
   in _load_data() refresh method. Never introduce asyncio.run(). 
   On API error: show a ft.Text("Could not load data") placeholder, do not crash.

5. REUSABLE COMPONENTS (add to ui_helpers.py)
   stat_card(icon, value, label, color) → ft.Container
     Dark surface card with colored icon, large bold value, small label.
   status_tag(text, color) → ft.Container
     Pill-shaped badge with colored background and white text.
   stock_bar(current, max_stock, color) → ft.Container
     Horizontal bar: grey track + colored fill proportional to current/max_stock.
   tag_chip(text, bg_color, text_color=WHITE) → ft.Container
     Small rounded chip used for role tags, category filters, payment methods.
   section_header(title, action_widget=None) → ft.Row
     Section label left + optional action button right.
   activity_item(event_type, description, timestamp, color) → ft.Container
     Used in Dashboard activity feed and AI Agent EventBus log.

6. CHARTS (reports screen — no new libraries)
   Bar chart: ft.Row of ft.Column items. Each column = 
     ft.Container(height=calculated_height, bgcolor=color, border_radius=4) 
     + ft.Text(label) below. Heights are proportional to max value in dataset.
   Progress bars: ft.Stack with grey base Container + colored overlay Container 
     whose width = (value / total) * available_width.

7. KITCHEN TIMERS
   Calculate elapsed = datetime.now() - order["created_at"]
   Color logic:
     < 5 min  → SUCCESS (green)
     5-15 min → WARNING (yellow)  
     > 15 min → ERROR (red) + blink effect using ft.AnimatedSwitcher
   Refresh: ft.threading.Timer(30, _refresh) pattern already used in chat_screen.py.
   Reference: .specify/screens/target/07_kitchen.png

8. AI AGENT 3-PANEL LAYOUT
   ft.Row(expand=True) with three children:
   - Left:   ft.Container(width=260, bgcolor=SURFACE)
             Contains: agent status list (11 agents), LLM info, example command chips
   - Center: ft.Container(expand=True)
             Contains: mode tabs (Ask/Command/Voice), message list, input row
             Each assistant message has an ft.ExpansionTile for pipeline trace
   - Right:  ft.Container(width=280, bgcolor=SURFACE)
             Contains: EventBus log from GET /api/audit/log, color-coded by event_type
   Reference: .specify/screens/target/08_ai_agent.png

9. ROLE-BASED VISIBILITY (POS screen)
   Read role from current_user dict passed to screen constructor.
   In build_action_bar() method:
     discount_btn.visible = role in ["MANAGER", "CASHIER", "ADMIN"]
     void_btn.visible = role in ["MANAGER", "ADMIN"]
   No API change needed — role is already in the auth response.

10. DASHBOARD DATA SOURCES
    Load on __init__ using existing endpoints + new audit log endpoint:
    - Revenue / transactions / avg_order: GET /api/reports/daily-sales?date=today
    - Active orders with kitchen_status: GET /api/sales/orders?status=draft
    - Low stock count: GET /api/inventory/items → filter stock_on_hand < reorder_level
    - Activity feed: GET /api/audit/log?limit=10
    Graceful fallback: if any call fails, show "—" in that card, do not block render.
    Reference: .specify/screens/target/02_dashboard.png


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION D: SCREEN IMPLEMENTATION ORDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Implement in this exact order (each step is independently testable):

1. ui_helpers.py — HMSColors + all 5 reusable components + build_header()
   Test: python -c "from src.ui.components.ui_helpers import HMSColors; print('ok')"

2. api/app.py — add audit log endpoint + kitchen_status field + PATCH endpoint
   Test: GET localhost:8000/api/audit/log returns list without error

3. app.py — dark theme + custom sidenav + add dashboard route
   Test: app starts, dark background visible, sidenav shows correct icons

4. dashboard_screen.py (NEW) — stat cards + quick actions + active orders + feed
   Reference: .specify/screens/target/02_dashboard.png
   Test: screen loads without API errors, stat cards show values or "—"

5. pos_screen.py — menu card grid + category tabs + styled order panel
   Reference: .specify/screens/current/02_pos.png → target/03_pos.png
   Test: can create order, add items, see running total, finalize payment

6. order_history_screen.py → Kitchen Display — ticket card grid + timers
   Reference: .specify/screens/current/06_kitchen_queue.png → target/07_kitchen.png
   Test: orders appear as cards, timer color changes based on elapsed time

7. chat_screen.py → AI Agent — 3-panel layout + pipeline trace + EventBus log
   Reference: .specify/screens/target/08_ai_agent.png
   Test: send a command, see pipeline trace expand, EventBus log updates

8. reports_screen.py — bar chart + payment bars + top-5 + inventory grid
   Reference: .specify/screens/current/05_reports.png → target/06_reports.png
   Test: charts render with sample data, date picker works, CSV export triggers

9. products_screen.py — alert sidebar + stock table with bars + ledger section
   Reference: .specify/screens/current/03_menu_management.png → target/04_inventory.png
   Test: low stock items appear in sidebar, stock bars show correct fill level

10. auth_screen.py — brand mark + role chips + animated PIN dots + dark gradient
    Reference: .specify/screens/target/01_login.png
    Test: login flow works end-to-end with PIN entry

11. receipt_screen.py — split layout + payment method cards + receipt preview
    Reference: .specify/screens/target/05_invoice.png
    Test: payment method selection highlights card, receipt preview updates


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION E: HARD CONSTRAINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Zero new pip dependencies. Flet, httpx, fastapi, sqlalchemy, pydantic only.
- All tests in tests/ must still pass after all changes.
- Maintain keyboard shortcuts in POS: F2=New, F5=Finalize, F8=Hold, F9=Resume, Esc=Void.
- All interactive elements minimum 48px height (touch-friendly).
- Charts built with Flet primitives only (ft.Container, ft.Stack, ft.Row).

FLET 0.80.5 RULES (already fixed — do not reintroduce these bugs):
- ft.Icons.X not ft.icons.X (capital I in Icons)
- Button text as positional arg, not text= keyword
- No padding= on ft.Column or ft.Row — use ft.Container(padding=...) instead
- No asyncio.run() anywhere in UI code
- ft.ThemeMode.DARK not string "dark"