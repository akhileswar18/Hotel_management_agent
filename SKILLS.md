# HMS Skills & Error Log

**Purpose**: Track errors encountered during development and their fixes for future reference.

**Last Updated**: 2026-03-11

---

## Error Log

### 1. UnicodeEncodeError: Windows Terminal Encoding Issue

**File**: `migrations/runner.py`, `scripts/seed_data.py`

**Error**:
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 0
```

**Root Cause**: Windows Command Prompt uses cp1252 encoding by default, which doesn't support Unicode characters like checkmark (✓), cross (✗), or rupee symbol (₹).

**Solution**:
- Replaced all Unicode characters with ASCII-safe alternatives:
  - ✓ → `[OK]`
  - ✗ → `[FAILED]`
  - ❌ → `[FAILED]`
  - ⚠️ → `[SKIP]`
  - ₹ → `Rs.`

**Files Modified**:
- migrations/runner.py (lines 54, 60, 62, 151)
- scripts/seed_data.py (lines 35, 43, 55, 81, 98, 106, 132, 140, 148, 165, 173, 180, 204, 213, 221)

**Prevention**: Always use ASCII characters when printing to Windows terminal. Avoid emoji and special Unicode symbols.

---

### 2. ModuleNotFoundError: Import Path Issue

**File**: `scripts/seed_data.py`

**Error**:
```
ModuleNotFoundError: No module named 'src'
```

**Root Cause**: When running `python scripts/seed_data.py` directly, the project root isn't in Python's sys.path, preventing imports of the `src` module.

**Solution**:
```python
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
```

**Files Modified**:
- scripts/seed_data.py (lines 13-21)

**Prevention**: Always add this pattern to scripts that need to import from the main project. Alternatively, use `python -m scripts.seed_data` instead of `python scripts/seed_data.py`.

---

### 3. sqlite3.IntegrityError: FOREIGN KEY Constraint Failed (Items)

**File**: `scripts/seed_data.py`, function `_seed_items()`

**Error**:
```
sqlite3.IntegrityError: FOREIGN KEY constraint failed
```

**Root Cause**: The `created_by` field was using a randomly generated UUID (`uuid4()`) that didn't exist in the `users` table, violating the foreign key constraint.

**Solution**:
```python
# Get actual users from database
user_repo = UserRepository()
all_users = user_repo.list()
if not all_users:
    return

system_user_id = all_users[0].id  # Use REAL user UUID

# Then use it:
created_by=system_user_id  # Instead of uuid4()
```

**Files Modified**:
- scripts/seed_data.py (lines 116-126, 151)

**Prevention**: Never use random IDs for foreign keys. Always fetch actual entities from the database and use their real IDs.

---

### 4. sqlite3.IntegrityError: FOREIGN KEY Constraint Failed (Stock Ledger)

**File**: `scripts/seed_data.py`, function `_seed_stock_ledger()`

**Error**:
```
sqlite3.IntegrityError: FOREIGN KEY constraint failed
```

**Root Cause**: Same as Error #3 - the `created_by` field used `uuid4()` instead of an actual user ID.

**Solution**:
```python
user_repo = UserRepository()
all_users = user_repo.list()
if not all_users:
    return

system_user = all_users[0].id  # Use REAL user UUID
```

**Files Modified**:
- scripts/seed_data.py (lines 190-215)

**Prevention**: Same as Error #3.

---

### 5. ImportError: Database Not in src.domain

**File**: `tests/conftest.py`

**Error**:
```
ImportError: cannot import name 'Database' from 'src.domain'
```

**Root Cause**: `Database` class is in `src.infrastructure`, not `src.domain`. The test configuration was importing from the wrong module.

**Solution**:
```python
# Wrong:
from src.domain import Database

# Correct:
from src.domain import (User, Item, Order, Role, Money, OrderStatus, OrderLineItem)
from src.infrastructure import Database
```

**Files Modified**:
- tests/conftest.py (lines 15-18)

**Prevention**: Always verify module structure before importing. Use IDE's "Go to Definition" feature to find correct locations.

---

### 6. TypeError: ButtonStyle Doesn't Accept text_style Parameter

**File**: `src/ui/components/ui_helpers.py`

**Error**:
```
TypeError: ButtonStyle.__init__() got an unexpected keyword argument 'text_style'
```

**Root Cause**: The Flet version being used doesn't support `text_style` parameter in `ButtonStyle`. Text styling must be done via direct button properties.

**Solution**:
```python
# Wrong:
style=ft.ButtonStyle(
    text_style=ft.TextStyle(size=20, weight="bold"),
    shape=ft.RoundedRectangleBorder(radius=8),
),

# Correct:
text_size=20,
style=ft.ButtonStyle(
    shape=ft.RoundedRectangleBorder(radius=8),
),
```

**Files Modified**:
- src/ui/components/ui_helpers.py:
  - HMSButton class (lines 46-58)
  - NumericKeypad._make_button() method (lines 154-165)

**Prevention**: Check Flet documentation for the specific version. Use simple properties (text_size) instead of complex nested style objects when possible.

---

### 7. UnicodeEncodeError in __main__.py (App Entry Point)

**File**: `src/__main__.py`

**Error**:
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 6: character maps to <undefined>
```

**Root Cause**: Same Windows cp1252 encoding issue as Error #1, but in the main entry point. The print statements used Unicode checkmark and cross symbols that crash on Windows terminal.

**Solution**:
- Replaced `print("      [OK] ...")` for success and `print("      [FAIL] ...")` for errors
- `[OK]` replaces checkmark, `[FAIL]` replaces cross

**Files Modified**:
- src/__main__.py (lines 40, 42, 49, 52, 58, 63)

**Prevention**: Same as Error #1. Always use ASCII in print/stdout on Windows.

---

### 8. asyncio.run() Conflicts with Flet Event Loop

**Files**: `src/ui/screens/auth_screen.py`, `pos_screen.py`, `products_screen.py`, `reports_screen.py`

**Error**:
App hangs silently or crashes with `RuntimeError: This event loop is already running`.

**Root Cause**: Flet runs its own asyncio event loop internally. Calling `asyncio.run()` inside a Flet callback or `__init__` creates a nested event loop conflict. All screen constructors and event handlers used `httpx.AsyncClient` with `asyncio.run()`.

**Solution**:
Replace all async HTTP calls with synchronous `httpx.Client`:
```python
# Wrong (crashes inside Flet):
async def _load_items(self):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
asyncio.run(self._load_items())

# Correct (works inside Flet):
def _load_items(self):
    with httpx.Client(timeout=5.0) as client:
        response = client.get(url)
```

**Files Modified**:
- src/ui/screens/auth_screen.py (login handler)
- src/ui/screens/pos_screen.py (load items, new order, add item, finalize)
- src/ui/screens/products_screen.py (load items)
- src/ui/screens/reports_screen.py (load reports, refresh)

**Prevention**: Never use `asyncio.run()` inside Flet apps. Use synchronous `httpx.Client` for HTTP calls in Flet event handlers and constructors.

---

### 9. Column.__init__() Got Unexpected Keyword Argument 'padding'

**Files**: All screen files (`auth_screen.py`, `pos_screen.py`, `products_screen.py`, `reports_screen.py`, `receipt_screen.py`)

**Error**:
```
Column.__init__() got an unexpected keyword argument 'padding'
```

**Root Cause**: In Flet 0.21.x, `ft.Column` does not accept a `padding` parameter. All screens extended `ft.Column` and passed `padding=20` to `super().__init__()`.

**Solution**:
Remove `padding` from Column init. If padding is needed, wrap in `ft.Container(padding=20)` instead.
```python
# Wrong:
super().__init__([...], spacing=10, padding=20, expand=True)

# Correct:
super().__init__([...], spacing=10, expand=True)
```

**Files Modified**:
- src/ui/screens/auth_screen.py
- src/ui/screens/pos_screen.py
- src/ui/screens/products_screen.py
- src/ui/screens/reports_screen.py
- src/ui/screens/receipt_screen.py

**Prevention**: Check Flet API docs for the installed version. `ft.Column` and `ft.Row` do not accept `padding` -- only `ft.Container` does.

---

### 10. Wrong NavigationDestination Class for NavigationRail

**File**: `src/ui/app.py`

**Error**: NavigationRail doesn't render correctly or throws runtime error.

**Root Cause**: `ft.NavigationRail` requires `ft.NavigationRailDestination`, not `ft.NavigationDestination`. The latter is for `ft.NavigationBar`.

**Solution**:
```python
# Wrong:
ft.NavigationRail(destinations=[ft.NavigationDestination(...)])

# Correct:
ft.NavigationRail(destinations=[ft.NavigationRailDestination(...)])
```

**Files Modified**:
- src/ui/app.py (3 destinations changed)

**Prevention**: Use `ft.NavigationRailDestination` for `NavigationRail` and `ft.NavigationDestination` for `NavigationBar`.

---

### 11. SyntaxError: unexpected indent in POS screen

**File**: `src/ui/screens/pos_screen.py`

**Error**:
```python
UI error: unexpected indent (pos_screen.py, line 449)
```

**Root Cause**: An extra leading space before `self._emit_kitchen_update(data)` broke Python block indentation inside payment finalization logic.

**Solution**:
```python
# Wrong (extra leading space):
 data = response.json()
  self._emit_kitchen_update(data)

# Correct:
data = response.json()
self._emit_kitchen_update(data)
```

**Files Modified**:
- src/ui/screens/pos_screen.py (line 449)

**Prevention**: Run a quick syntax check (`python -m py_compile`) after UI edits to catch indentation errors before launch.

---

### 12. Flet runtime error: Control must be added to the page first

**File**: `src/ui/screens/kitchen_screen.py`

**Error**:
```python
Kitchen: Control must be added to the page first.
```

**Root Cause**: Kitchen screen called `.update()` on child controls while detached from the page tree (during init / when Kitchen tab was not active).

**Solution**:
```python
# Use attachment-safe refresh
def _is_attached(self) -> bool:
    return getattr(self.order_list, "page", None) is not None

def _safe_refresh(self):
    if self._is_attached():
        self.update()
```

**Files Modified**:
- src/ui/screens/kitchen_screen.py
- src/ui/app.py

**Prevention**: Avoid calling `.update()` on screen child controls unless they are mounted; use a guarded refresh helper.

---

### 13. OSError [Errno 10048]: Port already in use on launcher restart

**File**: `src/launcher.py`

**Error**:
```python
ERROR: [Errno 10048] ... bind on address ('127.0.0.1', 8000)
ERROR: [Errno 10048] ... bind on address ('0.0.0.0', 8080)
```

**Root Cause**: `src/launcher.py` was run multiple times while an existing HMS process was already listening on ports `8000` and `8080`.

**Solution**:
- Added duplicate-instance guard in launcher startup:
  - Check API/UI ports first.
  - If both are already reachable, print existing instance info and exit cleanly.
  - Skip duplicate bind attempts instead of crashing.

**Files Modified**:
- src/launcher.py

**Prevention**:
- Before re-running launcher, stop existing HMS process or let launcher exit gracefully when existing instance is detected.

---

### 14. TypeError: Container.__init__() got unexpected keyword argument 'ignore_interactions'

**File**: `src/ui/screens/auth_screen.py`

**Error**:
```python
Container.__init__() got an unexpected keyword argument 'ignore_interactions'
```

**Root Cause**: The installed Flet build does not support `ignore_interactions` on `ft.Container` (API mismatch with examples from newer versions).

**Solution**:
- Removed unsupported `ignore_interactions` usage.
- Reordered `ft.Stack` children so the login card container is topmost and receives pointer events.

**Files Modified**:
- src/ui/screens/auth_screen.py

**Prevention**:
- Validate control constructor arguments against the installed Flet version before applying UI interaction props.

---

### 15. AttributeError: module 'flet' has no attribute 'Icons'

**Files**: `src/ui/app.py`, `src/ui/components/ui_helpers.py`, `src/ui/screens/pos_screen.py`, `src/ui/screens/products_screen.py`, `src/ui/screens/receipt_screen.py`

**Error**:
```python
module 'flet' has no attribute 'Icons'
```

**Root Cause**: Environment exposes `ft.icons` (lowercase) and does not provide `ft.Icons` (uppercase), so icon references using `ft.Icons.*` fail at runtime.

**Solution**:
- Reverted icon references from `ft.Icons.*` to `ft.icons.*` in all touched UI files.

**Files Modified**:
- src/ui/app.py
- src/ui/components/ui_helpers.py
- src/ui/screens/pos_screen.py
- src/ui/screens/products_screen.py
- src/ui/screens/receipt_screen.py

**Prevention**:
- Quick compatibility check before refactors:
```python
import flet as ft
print(hasattr(ft, "Icons"), hasattr(ft, "icons"))
```
- Use the namespace that actually exists in the installed runtime.

---

### 16. HMS UI regressions in sidenav, dashboard activity formatting, and KDS layout

**Error**:
```text
Sidebar AI entry missing, dashboard showed raw audit strings/UUID-heavy order titles, and Kitchen rendered as a plain history list instead of a KDS board.
```

**Root Cause**: The shell nav config and dashboard render paths were still using older placeholder layouts, and `order_history_screen.py` had not been rebuilt to the ticket-board design with safe refresh lifecycle handling.

**Solution**:
- Added the dedicated AI nav item with centered icon/label layout and special gradient styling.
- Reformatted dashboard stat values, activity feed entries, active-order titles, pending status colors, and quick-action icon boxes.
- Replaced the order history list with a dark KDS card grid, local bump ordering, ready action, auto-refresh timer, live clock, and cleanup hooks.

**Files Modified**:
- src/ui/app.py
- src/ui/screens/dashboard_screen.py
- src/ui/screens/order_history_screen.py

**Prevention**: When applying visual refactors in Flet, verify helper output assumptions, keep screen-specific formatting logic local, and add explicit `cleanup()`/`on_show()` hooks for timer-driven views.

---

### 17. Manager display name did not match requested operator name

**Error**:
```text
Dashboard greeted the manager as "Rajesh Kumar" instead of the requested "akhil".
```

**Root Cause**: `DashboardScreen.NAME_MAP` still mapped the `manager` role to the old placeholder display name.

**Solution**:
- Updated the `manager` entry in `DashboardScreen.NAME_MAP` to `akhil`.

**Files Modified**:
- src/ui/screens/dashboard_screen.py

**Prevention**: Keep role-to-display-name defaults aligned with the current operator/demo data before validating UI copy.

---

### 18. HMS sidenav spacing and icon-state polish drifted from target shell

**Error**:
```text
Sidenav items were not grouped/pinned correctly, hover state was missing, active accent treatment was inconsistent, and icon resolution needed runtime-safe fallback handling.
```

**Root Cause**: The shell was using a simpler nav builder with fixed item styling and direct icon references, which did not match the target layout or account for environments where `ft.Icons` is unavailable.

**Solution**:
- Rebuilt the sidenav item generation in `src/ui/app.py` with exact top/bottom grouping, active accent line, hover styling, low-stock badge placement, invoice route aliasing, and safe icon lookup that falls back to `ft.icons` / `CIRCLE_OUTLINED`.

**Files Modified**:
- src/ui/app.py

**Prevention**: For Flet shell navigation, resolve icon constants against the installed runtime first and rebuild the nav from current route state instead of mutating partial styling in place.

---

### 19. Sidenav width needed to increase after layout polish

**Error**:
```text
The left sidenav remained at 72px when the requested shell width was 90px.
```

**Root Cause**: The shell container width in `src/ui/app.py` was still hardcoded to the earlier compact width.

**Solution**:
- Updated the sidebar container width from `72` to `90`.

**Files Modified**:
- src/ui/app.py

**Prevention**: Keep shell dimensions centralized and re-check fixed container widths after layout change requests.

---

### 20. Sidenav labels disappeared after icon size increase

**Error**:
```text
Nav labels were no longer visible under the icons after enlarging the sidenav icon size and spacing.
```

**Root Cause**: The nav item still used a compact inner container while the icon size had been increased, so the icon consumed the available height and clipped the text.

**Solution**:
- Increased the sidenav nav-item box dimensions so both the enlarged icon and the label render inside the item.

**Files Modified**:
- src/ui/app.py

**Prevention**: When increasing icon size in stacked nav items, resize the containing box at the same time and verify text is not clipped.

---

### 21. Top header scale no longer matched widened sidenav

**Error**:
```text
The upper header bar and its text felt undersized after increasing the sidenav width.
```

**Root Cause**: `build_header()` in `src/ui/components/ui_helpers.py` was still using the earlier compact header height, padding, and text sizes.

**Solution**:
- Increased the shared header height, horizontal padding, and key text/chip sizes so the top bar better matches the widened shell.

**Files Modified**:
- src/ui/components/ui_helpers.py

**Prevention**: When changing major shell dimensions such as sidebar width, review the shared header scale in the same pass so the layout stays visually balanced.

---

### 22. Shared header height needed a final shell alignment increase

**Error**:
```text
The top header bar still needed to be taller after the shell layout adjustments.
```

**Root Cause**: `build_header()` was updated once already, but the final requested height target was higher than the current value.

**Solution**:
- Increased the shared header container height to `70`.

**Files Modified**:
- src/ui/components/ui_helpers.py

**Prevention**: After iterative shell tweaks, re-check final numeric size targets against the latest request instead of assuming the previous adjustment is enough.

---

### 23. Reports screen rendered a blank grey body due to brittle layout/data assumptions

**Error**:
```text
Reports screen showed a blank grey area instead of cards and charts.
```

**Root Cause**: The previous reports UI relied on an older layout structure and field names that did not line up cleanly with current report payloads, so empty/missing data paths left the screen visually broken.

**Solution**:
- Rebuilt `src/ui/screens/reports_screen.py` with a dark resilient layout, data normalization helpers for current API payloads, explicit empty states, and a full `_render_reports()` rebuild path.

**Files Modified**:
- src/ui/screens/reports_screen.py

**Prevention**: For dashboard-style Flet screens, normalize API payload variants at the screen boundary and always render explicit empty-state controls instead of assuming chart/list data exists.

---

### 24. KDS loaded the wrong order set and did not visually refresh after kitchen status updates

**Error**:
```text
Kitchen Display missed finalized tickets, used the wrong line item fields, and looked frozen after Start Cooking / Mark Ready / Served actions.
```

**Root Cause**: The KDS screen was querying `status=draft` instead of finalized kitchen tickets, and its status action handlers rebuilt state incompletely after PATCH calls.

**Solution**:
- Updated `order_history_screen.py` to load `status=finalized`, use `line_items.item_name` and `line_items.quantity`, switch footer buttons by `kitchen_status`, and fully rebuild/update the ticket grid after COOKING / READY / SERVED transitions.

**Files Modified**:
- src/ui/screens/order_history_screen.py

**Prevention**: For workflow boards driven by status metadata, align the query filter with the actual lifecycle stage and always rebind the rendered collection after successful PATCH transitions.

---

### 25. Inventory category dropdown broke after first selection due to stale hardcoded options

**Error**:
```text
Inventory category filter worked once, then dropdown state became inconsistent on later selections.
```

**Root Cause**: The category dropdown was initialized with a fixed option list that did not match real API category values, and its options were never rebuilt from fresh item data after load.

**Solution**:
- Updated `products_screen.py` to populate category options dynamically from `self.items`, keep `self.items` as the full inventory set, and apply category filtering client-side only for the displayed list.

**Files Modified**:
- src/ui/screens/products_screen.py

**Prevention**: For Flet dropdowns backed by API data, rebuild the full option set from the loaded dataset and validate the current selection before updating the control.

---

### 26. Inventory snapshot tiles were too large for the sidebar layout

**Error**:
```text
The inventory sidebar snapshot used oversized 2x2 tiles that consumed too much vertical space.
```

**Root Cause**: The snapshot section rendered four boxed metric tiles instead of a compact summary layout suited to the narrow sidebar.

**Solution**:
- Replaced the snapshot grid in `products_screen.py` with a compact `_build_snapshot()` text-row summary wired through `self.snapshot_container`.

**Files Modified**:
- src/ui/screens/products_screen.py

**Prevention**: In narrow sidebars, prefer stacked metric rows over card grids unless the available width and height were explicitly designed for tiled summaries.

---

### 27. Compact inventory snapshot still needed a smaller footprint

**Error**:
```text
The snapshot summary was converted to rows, but its container still occupied more space than desired.
```

**Root Cause**: The row-based snapshot layout was compact structurally, but the container padding and row spacing still left excess vertical space.

**Solution**:
- Reduced the snapshot container padding and tightened the snapshot row spacing in `products_screen.py`.

**Files Modified**:
- src/ui/screens/products_screen.py

**Prevention**: After replacing tile layouts with compact summaries, re-check container padding and inter-row spacing separately; the layout type change alone may not reduce footprint enough.

---

### 28. POS menu item cards were too tall for efficient browsing

**Error**:
```text
POS menu cards consumed too much vertical space, reducing the number of visible items in the menu grid.
```

**Root Cause**: The menu grid cards had no fixed compact height and used looser typography/spacing than needed for the available grid area.

**Solution**:
- Updated `pos_screen.py` to use a compact fixed-height menu card, tighter column spacing, slightly reduced typography, and a denser grid aspect ratio.

**Files Modified**:
- src/ui/screens/pos_screen.py

**Prevention**: For high-density POS grids, constrain card height explicitly and tune the grid aspect ratio together with text spacing so more items fit without clipping key metadata.

---

## Testing Results Summary

| Component | Status | Notes |
|-----------|--------|-------|
| **Unit Tests** | ✅ 22/22 PASSING | All domain logic tests pass |
| **Database Seeding** | ✅ COMPLETE | 4 users, 10 items, 8 tables, stock created |
| **API Server** | ✅ RUNNING | FastAPI on port 8000 |
| **Flet UI** | ✅ RUNNING | All screens load, login screen visible at http://localhost:8080 |
| **Flet UI Bugs Fixed** | ✅ FIXED | asyncio.run, Column padding, NavigationRailDestination, ButtonStyle, unexpected indent, detached-control update |
| **Integration Tests** | ⚠️ Mixed | Some file locking issues on Windows |
| **Smoke Tests** | ⚠️ Mixed | Same teardown issues |

---

## Key Learnings

1. **Windows Encoding**: Always test printing output on Windows. Use ASCII-safe alternatives for special characters.

2. **Path Management**: Add project root to sys.path in standalone scripts to ensure imports work from any location.

3. **Foreign Keys**: Always use real entity IDs from the database, never generate random IDs for foreign key fields.

4. **Import Locations**: Check module structure carefully. `Database` is in infrastructure, not domain.

5. **Framework Compatibility**: Different Flet versions have different APIs. Check documentation for the installed version.

6. **Flet Event Loop**: Never use `asyncio.run()` inside Flet apps. Use synchronous HTTP clients instead.

7. **Flet Column vs Container**: `ft.Column` does not accept `padding` -- wrap in `ft.Container` for padding.

8. **NavigationRail vs NavigationBar**: Use `NavigationRailDestination` for `NavigationRail`, `NavigationDestination` for `NavigationBar`.

9. **Python Indentation Discipline**: A single stray space can crash startup; run syntax checks for UI modules after manual edits.

10. **Flet Attachment Lifecycle**: Controls may exist but still be detached; defer or guard `.update()` calls until mounted.

---

## Prevention Best Practices

✅ Use ASCII characters in logging/printing
✅ Add sys.path manipulation to standalone scripts
✅ Fetch real entities before using their IDs
✅ Verify import paths before writing tests
✅ Check framework documentation for your version
✅ Test UI components early in development
✅ Never use asyncio.run() inside Flet (use sync httpx.Client)
✅ Use ft.Container for padding, not ft.Column
✅ Use NavigationRailDestination for NavigationRail
✅ Run `python -m py_compile src/ui/screens/pos_screen.py` after manual edits
✅ Guard `.update()` calls for off-screen/detached controls

---

## Next Phase (Phase 2)

- Implement voice/STT integration
- Add cloud sync infrastructure
- Complete stock-in workflow
- Add advanced reporting features
- Implement CSV/PDF export

All code is marked with `# TODO:` comments for Phase 2 work.

---

**Status**: ✅ All Phase 1.5 critical errors resolved (12 total) | App running: API on :8000, UI on :8080

---

## Troubleshooting Notes

29. **POS Card Images Not Rendering**:
   - Error: POS menu cards needed image backgrounds but the app was not serving item photos.
   - Root cause: Menu cards were plain `ft.Container` blocks, and `ft.app()` was not exposing the actual asset directory used by the repo.
   - Fix: Switched POS cards to `ft.Stack` image cards with gradient overlay, mapped real filenames from `src/assets/images`, and set `assets_dir="src/assets"` in the Flet entry point.
   - Files touched: `src/ui/screens/pos_screen.py`, `src/ui/app.py`.
   - Prevention: Verify the real asset folder path before wiring `ft.Image` sources, and always align `assets_dir` with the directory that actually exists on disk.

30. **Relative Flet Asset Paths Break on Alternate Launch CWD**:
   - Error: POS image URLs resolved to placeholders because the asset server root depended on the current working directory.
   - Root cause: `assets_dir="src/assets"` was relative, so launching the app from a different location could point Flet at the wrong folder.
   - Fix: Computed `ASSETS_DIR` with `os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))` and passed that absolute path into `ft.app(...)`.
   - Files touched: `src/ui/app.py`.
   - Prevention: Use absolute asset paths for Flet whenever the app can be started from more than one working directory.

31. **Inventory List Rows Needed Card Grid Rendering**:
   - Error: The inventory main panel still rendered long table-like rows instead of the image-backed card layout used elsewhere in the UI.
   - Root cause: `ProductsScreen._display_items()` built one row container per item and had no inventory card builder or quick stock-in entry point.
   - Fix: Added an `IMAGE_MAP`, introduced `_build_inv_card()`, rebuilt `_display_items()` as a 4-column card grid, and added `_handle_stock_in_for()` to preselect the clicked item in the stock-in dialog.
   - Files touched: `src/ui/screens/products_screen.py`.
   - Prevention: Keep renderer methods isolated by view mode so switching from list layouts to grid layouts only changes one display path.

32. **Inventory Grid Needed Fail-Safe Rendering Path**:
   - Error: The inventory main panel could go blank if one card build or grid refresh raised during `_display_items()`.
   - Root cause: The new image-card renderer had no outer exception boundary, and a single bad item could abort the full panel render without a visible fallback.
   - Fix: Wrapped `_display_items()` and `_build_inv_card()` in safe fallback handling and added `_update_snapshot()` so snapshot refresh is isolated from grid rendering.
   - Files touched: `src/ui/screens/products_screen.py`, `src/ui/app.py`.
   - Prevention: When replacing a full list renderer with card composition, give both the per-item builder and the top-level display method visible fallback states instead of silent failure.

33. **Billing Needed Draft-Order Selection Before Finalize**:
   - Error: The billing screen only handled previewing finalized invoices and had no table-based way to pick a pending draft order for payment.
   - Root cause: `ReceiptScreen` lacked draft-order state, selector chips, bill-summary hydration, and a finalize flow tied to the selected pending order.
   - Fix: Added draft-order loading, table/takeaway chips, pending bill summary, amount auto-fill, snack feedback, and API finalize logic that refreshes both recent invoices and draft table availability.
   - Files touched: `src/ui/screens/receipt_screen.py`.
   - Prevention: Separate "pick pending order" state from "preview finalized invoice" state whenever a billing screen needs to support both collection and reprint workflows.

34. **Flet 0.80.5 Text Does Not Support `letter_spacing`**:
   - Error: `Text.__init__() got an unexpected keyword argument 'letter_spacing'` on billing screen startup.
   - Root cause: A prompt-derived `ft.Text(...)` used `letter_spacing`, but that parameter is not supported by the Flet version in this repo.
   - Fix: Removed the unsupported `letter_spacing` argument from the billing screen's "SELECT ORDER" label.
   - Files touched: `src/ui/screens/receipt_screen.py`.
   - Prevention: When applying UI prompts to Flet, cross-check text style parameters against the repo's installed Flet version before patching.

35. **Flet 0.80.5 Uses `ft.icons`, Not `ft.Icons`**:
   - Error: `module 'flet' has no attribute 'Icons'` after login when newly patched screens were instantiated.
   - Root cause: Prompt-derived code used `ft.Icons.*`, but this repo's Flet version exposes icon constants via `ft.icons.*`.
   - Fix: Replaced the new `ft.Icons` usages in billing and inventory with `ft.icons`.
   - Files touched: `src/ui/screens/receipt_screen.py`, `src/ui/screens/products_screen.py`.
   - Prevention: Match icon enum casing to the installed Flet API before introducing new icon constants.

36. **Billing Left Panel Needed Flet-Safe Control Props**:
   - Error: The billing selector patch could blank the left panel during initialization under Flet 0.80.5.
   - Root cause: The new flow relied on unsupported/fragile control patterns such as `disabled` on `ft.ElevatedButton`, `tooltip` on `ft.Container`, and eager state changes during init.
   - Fix: Moved draft-order loading to the safe post-layout sequence, removed the container tooltip, and replaced button disabling with an `on_click`/color-based `_set_confirm_enabled()` helper.
   - Files touched: `src/ui/screens/receipt_screen.py`.
   - Prevention: For Flet 0.80.5, prefer explicit click-handler toggling and post-`super().__init__()` data hydration over unsupported widget-state props.

37. **Avoid `expand=True` Inside Tight Billing Columns**:
   - Error: The billing left panel could render as an empty area after the selector patch even though the screen itself mounted.
   - Root cause: The new confirm button was set to `expand=True` inside a `Column(tight=True)`, which creates an unstable flex layout in Flet.
   - Fix: Reverted the confirm button to a fixed width/height button in the billing form.
   - Files touched: `src/ui/screens/receipt_screen.py`.
   - Prevention: In Flet, avoid mixing `expand=True` with `tight=True` in the same vertical form layout unless the parent column is explicitly designed for flex sizing.

38. **Billing Recent Invoices Need a Bounded Scroll Region**:
   - Error: The recent invoice cards extended past the visible billing panel with no way to scroll through the full list.
   - Root cause: The invoice list was rendered in an unconstrained column, so content height kept growing instead of becoming a scrollable region.
   - Fix: Enabled scrolling on `recent_list` and wrapped it in a fixed-height container inside the billing card.
   - Files touched: `src/ui/screens/receipt_screen.py`.
   - Prevention: When rendering long record lists in Flet side panels, give the list an explicit scroll mode and a bounded height.

39. **Card Images Should Not Depend on Runtime Asset URLs**:
   - Error: POS and inventory cards still fell back to the placeholder art even though `/images/...` returned `200 image/jpeg` from the running app.
   - Root cause: The card renderer depended on runtime URL-based `ft.Image(src=...)` resolution, which remained brittle in the current Flet web flow despite the asset endpoint being healthy.
   - Fix: Centralized menu image loading in `src/ui/image_assets.py` and switched card images to cached local `src_base64` data, removing the HTTP asset-path dependency for these UI cards.
   - Files touched: `src/ui/image_assets.py`, `src/ui/screens/pos_screen.py`, `src/ui/screens/products_screen.py`.
   - Prevention: For frequently reused local UI assets, prefer a validated base64/image helper over per-screen URL strings so rendering does not rely on web asset routing.
