---
name: flet-fastapi-windows-debugging
description: Diagnose and fix common errors in Flet + FastAPI apps running on Windows. Covers Unicode encoding crashes, asyncio event loop conflicts, Flet API version mismatches, and Column/Container parameter issues. Use when the app fails to start, the Flet UI shows errors, or when debugging runtime issues in this HMS project.
---

# Flet + FastAPI Debugging on Windows

Known issues and fixes for running this HMS project (Flet 0.21.x + FastAPI) on Windows.

## Debugging Checklist

When the app fails to start or the UI shows errors:

```
- [ ] Check for Unicode characters in print/log statements (cp1252 crash)
- [ ] Check for asyncio.run() calls inside Flet event handlers or constructors
- [ ] Check for unsupported kwargs on Flet controls (e.g. padding on Column)
- [ ] Check NavigationRail uses NavigationRailDestination (not NavigationDestination)
- [ ] Check ports 8000/8080 are not already occupied by stale processes
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

## Project-Specific Notes

- Flet version pinned at **0.21.2** in `requirements.txt`
- Flet UI runs in `WEB_BROWSER` mode on port 8080
- All screens (`auth_screen`, `pos_screen`, `products_screen`, `reports_screen`, `receipt_screen`) extend `ft.Column`
- Screens make HTTP calls to the FastAPI backend -- use sync `httpx.Client`, never `asyncio.run()`
