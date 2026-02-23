---
name: flet-fastapi-windows-debugging
description: Diagnose and fix common errors in Flet + FastAPI apps running on Windows. Covers Unicode encoding crashes, asyncio event loop conflicts, Flet API version mismatches, Column/Container parameter issues, NavigationRail height errors, self.page property conflicts in ft.Column subclasses, and agent/EventBus debugging. Use when the app fails to start, the Flet UI shows errors, or when debugging runtime issues in this HMS project.
---

# Flet + FastAPI Debugging on Windows

Known issues and fixes for running this HMS project (Flet 0.80.x + FastAPI) on Windows.

## Debugging Checklist

When the app fails to start or the UI shows errors:

```
- [ ] Check for Unicode characters in print/log statements (cp1252 crash)
- [ ] Check for asyncio.run() calls inside Flet event handlers or constructors
- [ ] Check for unsupported kwargs on Flet controls (e.g. padding on Column)
- [ ] Check NavigationRail uses NavigationRailDestination (not NavigationDestination)
- [ ] Check NavigationRail has bounded height (not wrapped in unbounded Column)
- [ ] Check ft.Column subclasses use self._page, NOT self.page (Flet property conflict)
- [ ] Check icon references use ft.icons.X (lowercase module), NOT ft.Icons.X (may not exist in venv/older versions)
- [ ] Check nested dialog callbacks for variable shadowing (use nonlocal + distinct names)
- [ ] Check IntentParser priority order — compound phrases before broad keywords (Error 11)
- [ ] Check text-command endpoint checks result.event.type for workflow.failed (Error 12)
- [ ] Check OrderAgent uses event.user_id (not just payload.user_id) to avoid FK violation (Error 13)
- [ ] Check ElevatedButton/TextButton use positional text arg, NOT text= keyword (0.80.x)
- [ ] Check ports 8000/8080 are not already occupied by stale processes
- [ ] (Agents) Check event_log table for recent events if event-driven behavior is missing
- [ ] (Agents) Verify agents are registered and subscribed in API startup (AgentRegistry)
```

---

## Error 1: UnicodeEncodeError on Windows Terminal

**Symptom**: App crashes immediately with:
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'
```

**Cause**: Windows terminal defaults to `cp1252` encoding, which cannot render Unicode symbols like `✓`, `✗`, `⌫`, `₹`, `╔`, `║`, etc.

**Fix**: Replace Unicode symbols with ASCII alternatives in all `print()` statements and log output:

| Bad | Good |
|-----|------|
| `✓` | `[OK]` |
| `✗` | `[FAIL]` |
| `⌫` | `[DEL]` |

**Note**: Unicode in Flet UI controls (rendered in browser) is fine. Only `print()`/`sys.stdout` output is affected.

---

## Error 2: asyncio.run() Inside Flet Event Loop

**Symptom**: App hangs silently or crashes with `RuntimeError: This event loop is already running`.

**Cause**: Flet runs its own asyncio event loop. Calling `asyncio.run()` inside a Flet callback or `__init__` creates a nested loop conflict.

**Locations to check**: Screen constructors and button click handlers that use `httpx.AsyncClient`.

**Fix**: Replace `httpx.AsyncClient` (async) with `httpx.Client` (sync):

```python
# BAD - crashes inside Flet
async def _load_items(self):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
asyncio.run(self._load_items())

# GOOD - works inside Flet
def _load_items(self):
    with httpx.Client(timeout=5.0) as client:
        response = client.get(url)
```

For constructors that call API on init, silently catch connection errors (API may not be running yet):

```python
def __init__(self, ...):
    ...
    self._load_items()

def _load_items(self):
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{self.api_base}/api/inventory/items")
            if response.status_code == 200:
                self.items = response.json()
    except Exception:
        pass  # API may not be running yet
```

---

## Error 3: Column.__init__() Unexpected Keyword 'padding'

**Symptom**: Flet UI shows:
```
Column.__init__() got an unexpected keyword argument 'padding'
```

**Cause**: In Flet 0.21.x, `ft.Column` does not accept `padding`. Only `ft.Container` supports it.

**Fix**: Remove `padding` from any `ft.Column(...)` or `super().__init__(...)` call in Column subclasses:

```python
# BAD
super().__init__(
    [...controls...],
    spacing=10,
    padding=20,   # Not supported on Column
    expand=True,
)

# GOOD
super().__init__(
    [...controls...],
    spacing=10,
    expand=True,
)
```

If padding is needed, wrap the Column in a Container:
```python
ft.Container(
    content=ft.Column([...], spacing=10, expand=True),
    padding=20,
)
```

---

## Error 4: Wrong NavigationRail Destination Class

**Symptom**: Runtime error or navigation rail doesn't render.

**Cause**: `ft.NavigationRail` requires `ft.NavigationRailDestination`, not `ft.NavigationDestination` (which is for `ft.NavigationBar`).

**Fix**:
```python
# BAD
ft.NavigationRail(
    destinations=[
        ft.NavigationDestination(icon=ft.icons.HOME, label="Home"),
    ],
)

# GOOD
ft.NavigationRail(
    destinations=[
        ft.NavigationRailDestination(icon=ft.icons.HOME, label="Home"),
    ],
)
```

---

## Error 5: Port Already in Use

**Symptom**: `[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)`

**Fix** (PowerShell):
```powershell
# Find PID on the port
netstat -ano | Select-String ":8000.*LISTENING"

# Kill it
taskkill /PID <pid> /T /F
```

---

## Running the App

The app has two processes that must run separately:

1. **API backend** (port 8000): `python -m src`
2. **Flet UI** (port 8080): `python -m src.ui.app`

Start the API first, then the UI. The Flet process produces no console output -- verify it by checking `netstat -ano | Select-String ":8080"`.

---

## Error 6: `'NoneType' object has no attribute 'on_keyboard_event'` (or any page attribute)

**Symptom**: Login or navigation crashes with:
```
'NoneType' object has no attribute 'on_keyboard_event'
```
or similar `'NoneType' object has no attribute 'dialog'`, `'NoneType' object has no attribute 'update'`, etc.

**Cause**: `ft.Column` (and all Flet controls) has a built-in **read-only `page` property** that returns `None` until the control is mounted on the page. When a screen class does `self.page = page` in `__init__`, Flet's internal property overrides the assignment, so `self.page` returns `None`.

**Fix**: Store the page reference as `self._page` (private attribute) to avoid the naming conflict:

```python
# BAD — Flet's internal .page property overrides this
class POSScreen(ft.Column):
    def __init__(self, page: ft.Page, ...):
        self.page = page          # IGNORED by Flet's property!
        ...
        self.page.dialog = dlg    # NoneType error!

# GOOD — use private name to avoid conflict
class POSScreen(ft.Column):
    def __init__(self, page: ft.Page, ...):
        self._page = page         # Safe — no conflict
        ...
        self._page.dialog = dlg   # Works!
```

**Applies to ALL screen classes** that extend `ft.Column`, `ft.Row`, `ft.Container`, or any Flet control:
- `pos_screen.py` → `self._page`
- `products_screen.py` → `self._page`
- `reports_screen.py` → `self._page`
- `order_history_screen.py` → `self._page`
- `user_mgmt_screen.py` → `self._page`
- `receipt_screen.py` → `self._page`
- `auth_screen.py` → already uses `self._page` (reference pattern)

---

## Error 7: `module 'flet' has no attribute 'Icons'` or `module 'flet.controls.material.icons' has no attribute 'X'` (icon API version mismatch)

**Symptom**: App crashes with:
```
AttributeError: module 'flet' has no attribute 'Icons'
```
or
```
AttributeError: module 'flet.controls.material.icons' has no attribute 'ERROR'
```

**Cause**: Different Flet versions use different icon APIs:
- **venv/older versions**: Use `ft.icons.X` (lowercase module with constants)
- **Some environments**: May have `ft.Icons.X` (capitalized class proxy)
- **Version mismatch**: Code written for one API fails in another environment

**Fix**: Always use `ft.icons.ICON_NAME` (lowercase `icons` module) for maximum compatibility:

```python
# BAD — May not exist in venv/older versions
ft.Icons.SHOPPING_CART
ft.Icons.DARK_MODE
ft.Icons.ERROR

# GOOD — Works across Flet versions
ft.icons.SHOPPING_CART
ft.icons.DARK_MODE
ft.icons.ERROR
```

To find and fix all instances:
```powershell
rg "ft\.Icons\." src/ --files-with-matches
# Then replace ft.Icons. with ft.icons. in each file
```

**Note**: If you see `ft.Icons` working in one environment but not another, check Flet versions:
```python
import flet as ft
print(hasattr(ft, 'Icons'))  # May be False in venv
print(hasattr(ft, 'icons'))  # Should be True
print(hasattr(ft.icons, 'ERROR'))  # Should be True
```

---

## Error 8: NavigationRail "Control's height is unbounded"

**Symptom**: Red error overlay in UI:
```
Error displaying NavigationRail
Control's height is unbounded. Either set "expand" property,
set a fixed "height" or nest NavigationRail inside another
control with a fixed height.
```

**Cause**: `ft.NavigationRail` requires a bounded height. Wrapping it in an `ft.Column` without a fixed height causes this error because Column doesn't propagate height constraints.

**Fix**: Place the NavigationRail **directly in the main `ft.Row`** (which gets bounded height from `expand=True` on the Row). Do NOT wrap it in a Column or Container:

```python
# BAD — Column has unbounded height → NavigationRail error
nav_column = ft.Column([nav_rail, some_button], expand=True)
main_layout = ft.Row([nav_column, content], expand=True)

# BAD — Container with expand=True shares space equally
nav_container = ft.Container(content=nav_column, width=80, expand=True)

# GOOD — NavigationRail directly in Row, use trailing for extra widgets
nav_rail = ft.NavigationRail(
    destinations=[...],
    trailing=dark_mode_toggle,  # Use trailing slot for extra buttons
)
main_layout = ft.Row(
    [nav_rail, ft.VerticalDivider(width=1), content_area],
    spacing=0,
    expand=True,
    vertical_alignment=ft.CrossAxisAlignment.START,
)
```

**Key rule**: NavigationRail's `trailing` property is the correct place to add widgets (like a dark mode toggle) below the destination icons. Never wrap the rail in a Column.

---

## Error 9: POS screen duplicated (two layouts stacked)

**Symptom**: After login, the POS screen appears twice — two full layouts stacked vertically.

**Cause**: Flet 0.80.x rendering issue with `page.clean()` + `page.add()` combined with default page scrolling and nested `expand=True` layouts.

**Fix**:
1. Disable page-level scrolling: `self.page.scroll = None`
2. Replace `page.clean()` + `page.add(...)` with direct assignment:

```python
# BAD — can cause duplication in Flet 0.80.x
self.page.clean()
self.page.add(main_layout)

# GOOD — direct assignment prevents duplication
self.page.controls = [main_layout]
self.page.update()
```

---

## Running the App

The app can be launched two ways:

### Option 1: Unified launcher (recommended)
```powershell
python -m src.launcher
```
Starts both API (port 8000) and Flet UI (port 8080) in one process.

### Option 2: Separate processes
1. **API backend** (port 8000): `python -m src`
2. **Flet UI** (port 8080): `python -m src.ui.app`

Start the API first, then the UI.

---

## Project-Specific Notes

- Flet version: **0.80.5** (check with `python -c "import flet; print(flet.__version__)"`)
- Flet UI runs in `WEB_BROWSER` mode on port 8080
- All screens extend `ft.Column` — **always use `self._page` not `self.page`**
- Icon constants: **always `ft.icons.X`** (lowercase module) for maximum compatibility across Flet versions
- NavigationRail: **always place directly in Row**, use `trailing` for extra widgets
- Screens make HTTP calls to the FastAPI backend — use sync `httpx.Client`, never `asyncio.run()`
- Page transitions: use `page.controls = [...]` + `page.update()`, never `page.clean()` + `page.add()`

---

## Error 10: `UnboundLocalError: cannot access local variable 'dlg'` in nested dialog callbacks

**Symptom**: Clicking a button inside a dialog (e.g. "Confirm Payment") does nothing. Terminal shows:
```
UnboundLocalError: cannot access local variable 'dlg' where it is not associated with a value
```

**Cause**: Python 3.11+ scoping conflict. When an inner function both **reads** an outer variable (e.g. `dlg.open = False` to close the current dialog) AND **assigns** to the same name later (e.g. `dlg = ft.AlertDialog(...)` to create a follow-up dialog), Python treats the variable as local throughout the entire function. The first read fails because the local hasn't been assigned yet.

**Example** (the HMS "Confirm Payment → Receipt" flow):
```python
def _handle_finalize(self, e):
    ...
    def confirm_payment(e):
        dlg.open = False      # READ — Python thinks dlg is local (because of line below)
        ...
        dlg = ft.AlertDialog(  # ASSIGN — causes Python to treat dlg as local everywhere
            title=ft.Text("Receipt"),
            ...
        )
    
    dlg = ft.AlertDialog(      # This is the OUTER dialog (payment)
        title=ft.Text("Finalize"),
        actions=[ft.ElevatedButton("Confirm", on_click=confirm_payment)],
    )
```

**Fix**: Use `nonlocal dlg` AND rename the inner dialog to avoid shadowing:

```python
def confirm_payment(e):
    nonlocal dlg              # Tells Python: dlg is from outer scope
    dlg.open = False          # Now works — refers to outer payment dialog
    ...
    receipt_dlg = ft.AlertDialog(  # Different name — no shadowing
        title=ft.Text("Receipt"),
        ...
    )
    self._page.dialog = receipt_dlg
    receipt_dlg.open = True
    self._page.update()
```

**General rule**: In Flet dialog chains where one dialog opens another, always:
1. Add `nonlocal dlg` if the callback needs to close the outer dialog
2. Use distinct variable names for each dialog (`dlg`, `receipt_dlg`, `confirm_dlg`, etc.)

---

## Error 11: IntentParser routes "order ... pay cash" to `finalize_order` instead of `create_order`

**Symptom**: In Command mode, typing "order 3 biryani for table 7 pay cash" returns "Cannot finalize order with no items" instead of creating an order.

**Cause**: The `IntentParser.parse()` method checked for finalize keywords (`"pay "`, `"finalize"`, `"checkout"`) **before** order keywords. Since "pay" appears in "order 3 biryani for table 7 **pay** cash", it matched the finalize branch first and never reached the order-creation logic.

**Fix**: Restructure the intent priority in `src/voice/intent_parser.py`:

1. **Specific compound phrases first** — void, hold, create-product, stock-in, report (these have unambiguous keywords)
2. **Item-name matching** — if text mentions actual inventory product names (biryani, coke, etc.), always route to `create_order` even if "pay" is present
3. **Finalize-leading only** — `finalize_order` only when no item names or order-creation context is present
4. **Generic order keywords** — fallback for "create order", "order for table 5", etc.

```python
# Priority order (abbreviated):
# 1. void / hold / create-product / stock-in / report  (compound phrases)
# 2. has_item_names → create_order  (even with "pay" keyword)
# 3. finalize_kw AND NOT order_kw → finalize_order
# 4. order_kw → create_order  (generic, may need follow-up)
# 5. finalize_kw fallback → finalize_order
```

**General rule**: When adding new intents, always check that broader keyword matches (like "pay", "add", "order") don't shadow more specific intents. Test with compound sentences like "order X pay cash", "add 50 biryani to stock", "new product at 250".

---

## Agent & EventBus Debugging

When agent-driven behavior is missing (e.g. no audit entries, no low-stock alerts, no print on finalize):

### Verify event flow (event_log table)

Events are persisted to the `event_log` table (migration `003_add_event_log.sql`). Use this to confirm that the API is publishing events and that the store is writing them.

```sql
-- Recent events (SQLite)
SELECT id, event_type, payload, created_at
FROM event_log
ORDER BY created_at DESC
LIMIT 20;
```

If no rows appear after an action (e.g. order finalized), the middleware may not be publishing, or the EventStore may not be wired.

### EventBus debugging tips

1. **Events not firing**: Ensure the FastAPI app uses the event middleware and that services call `event_bus.publish(event)` (or equivalent) for the relevant actions. Check `src/events/middleware.py` and the places that publish.
2. **Handlers not called**: Subscriptions are registered at startup. Ensure `AgentRegistry` is populated and that each agent’s `subscribe()` is invoked during app startup (e.g. in `src/api/app.py` or wherever the bus and agents are wired).
3. **Order of initialization**: EventBus → EventStore → register agents → then start handling requests. If the bus or store is `None` when publishing, you’ll get attribute errors or silent no-ops.

### Common agent registration issues

- **Agent not in registry**: Every agent that should react to events must be registered with `AgentRegistry.subscribe(event_type, handler)`. If an agent is instantiated but never subscribed, it will never receive events.
- **Wrong event type**: Handler is subscribed to a different `event_type` than the one being published (e.g. subscribing to `order.created` but publishing `OrderCreated`). Ensure event type strings match exactly.
- **Handler raises**: If one handler raises, the bus may stop dispatching to other handlers or the request may fail. Check logs for tracebacks from agent handlers; fix or catch exceptions so one failing agent doesn’t break others.
- **Async vs sync**: If the bus or handlers are async, ensure they are awaited correctly from the request path. If handlers are sync but the bus runs in an async context, ensure the bus doesn’t deadlock (e.g. use `run_in_executor` or sync dispatch as appropriate).

---

## Error 12: Text-command endpoint returns success even when workflow failed

**Symptom**: User types "create order for table 5 with 3 coke", gets "Order created!" but the order has no items. Then "finalize" fails with "Cannot finalize order with no items."

**Cause**: The text-command endpoint checked `result.success` (EventBus dispatch success) but NOT `result.event.type`. The orchestrator returned `workflow.failed` but the endpoint treated ANY event as success.

**Fix**: In `src/api/app.py`, after `result = event_bus.publish_sync(event)`, check `result.event.type == "workflow.failed"` or `.endswith(".error")` before declaring success.

---

## Error 13: OrderAgent fails with FOREIGN KEY constraint on empty user_id

**Symptom**: `order.create` step fails with "FOREIGN KEY constraint failed" when `user_id` is empty.

**Cause**: `OrderAgent._handle_create` read `user_id` from `event.payload` but the OrchestratorAgent did not always set it. The `event.user_id` field (set by the API from the logged-in session) was the correct source.

**Fix**: In `src/agents/order_agent.py`, use `event.user_id or event.payload.get("user_id", "")` to prefer the event-level user_id.
