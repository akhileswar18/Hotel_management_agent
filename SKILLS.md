# HMS Skills & Error Log

**Purpose**: Track errors encountered during development and their fixes for future reference.

**Last Updated**: 2026-02-11

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

## Testing Results Summary

| Component | Status | Notes |
|-----------|--------|-------|
| **Unit Tests** | ✅ 22/22 PASSING | All domain logic tests pass |
| **Database Seeding** | ✅ COMPLETE | 4 users, 10 items, 8 tables, stock created |
| **API Server** | ✅ RUNNING | FastAPI on port 8000 |
| **Flet UI** | ✅ RUNNING | All screens load, login screen visible at http://localhost:8080 |
| **Flet UI Bugs Fixed** | ✅ FIXED | asyncio.run, Column padding, NavigationRailDestination, ButtonStyle |
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

---

## Next Phase (Phase 2)

- Implement voice/STT integration
- Add cloud sync infrastructure
- Complete stock-in workflow
- Add advanced reporting features
- Implement CSV/PDF export

All code is marked with `# TODO:` comments for Phase 2 work.

---

**Status**: ✅ All Phase 1.5 critical errors resolved (10 total) | App running: API on :8000, UI on :8080
