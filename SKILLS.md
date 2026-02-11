# HMS Skills & Error Log

**Purpose**: Track errors encountered during development and their fixes for future reference.

**Last Updated**: 2026-02-10

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

## Testing Results Summary

| Component | Status | Notes |
|-----------|--------|-------|
| **Unit Tests** | ✅ 22/22 PASSING | All domain logic tests pass |
| **Database Seeding** | ✅ COMPLETE | 4 users, 10 items, 8 tables, stock created |
| **API Server** | ✅ RUNNING | FastAPI on port 8000 |
| **Flet UI** | ✅ FIXED | ButtonStyle issue resolved |
| **Integration Tests** | ⚠️ Mixed | Some file locking issues on Windows |
| **Smoke Tests** | ⚠️ Mixed | Same teardown issues |

---

## Key Learnings

1. **Windows Encoding**: Always test printing output on Windows. Use ASCII-safe alternatives for special characters.

2. **Path Management**: Add project root to sys.path in standalone scripts to ensure imports work from any location.

3. **Foreign Keys**: Always use real entity IDs from the database, never generate random IDs for foreign key fields.

4. **Import Locations**: Check module structure carefully. `Database` is in infrastructure, not domain.

5. **Framework Compatibility**: Different Flet versions have different APIs. Check documentation for the installed version.

---

## Prevention Best Practices

✅ Use ASCII characters in logging/printing
✅ Add sys.path manipulation to standalone scripts
✅ Fetch real entities before using their IDs
✅ Verify import paths before writing tests
✅ Check framework documentation for your version
✅ Test UI components early in development

---

## Next Phase (Phase 2)

- Implement voice/STT integration
- Add cloud sync infrastructure
- Complete stock-in workflow
- Add advanced reporting features
- Implement CSV/PDF export

All code is marked with `# TODO:` comments for Phase 2 work.

---

**Status**: ✅ All Phase 1.5 critical errors resolved | Ready for production testing
