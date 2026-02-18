# HMS — Known Errors & TODO

## Untested Fixes (applied but not runtime-verified)

### 1. Flet 0.80.5 icon API migration (`ft.icons.X` → `ft.Icons.X`)
- **Error**: `AttributeError: module 'flet.controls.material.icons' has no attribute 'ERROR'`
- **Root cause**: Flet 0.80.5 moved icon constants from bare `ft.icons` module to `ft.Icons` class.
- **Fix applied**: Replaced `ft.icons.X` with `ft.Icons.X` in all 9 UI files.
- **Files changed**:
  - `src/ui/app.py`
  - `src/ui/components/ui_helpers.py`
  - `src/ui/screens/pos_screen.py`
  - `src/ui/screens/products_screen.py`
  - `src/ui/screens/chat_screen.py`
  - `src/ui/screens/order_history_screen.py`
  - `src/ui/screens/reports_screen.py`
  - `src/ui/screens/receipt_screen.py`
  - `src/ui/screens/user_mgmt_screen.py`
- **Status**: Import-level test passed; full runtime test pending.

### 2. ElevatedButton `text=` keyword removed in Flet 0.80.5
- **Error**: `TypeError: Button.__init__() got an unexpected keyword argument 'text'`
- **Root cause**: `ElevatedButton` is deprecated → maps to `Button` which doesn't accept `text` as a keyword arg.
- **Fix applied**: Changed `text=text` to positional `text` in `HMSButton.__init__` and `NumericKeypad._make_button`.
- **Files changed**:
  - `src/ui/components/ui_helpers.py` (lines 49, 156)
- **Status**: Import-level test passed; full runtime test pending.

## Potential Further Issues

- `ElevatedButton` itself is deprecated in 0.80.x; may need full migration to `ft.Button` if deprecation warnings cause problems.
- `Receive loop error: 'bytes'` WebSocket error from `flet_web` — appears to be a transient Flet-internal issue, not blocking.
- Port 8000/8080 stale processes must be killed before relaunch (`netstat -ano | Select-String ":8000.*LISTENING"`).

## Next Steps

- [ ] Kill stale processes on ports 8000/8080 and relaunch `python -m src.launcher`
- [ ] Verify login screen renders correctly in browser
- [ ] Verify navigation and all screens load without icon/button errors
- [ ] Consider migrating `ft.ElevatedButton` → `ft.Button` globally to silence deprecation warnings
