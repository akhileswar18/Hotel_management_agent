> **UPDATE (Feb 13, 2026)**: HMS v2.0 is now feature-complete. For the latest quick start, see README.md. Use `python -m src.launcher` for the unified launcher.

# Phase 1.5 Quick Start Guide

## Get Running in 3 Minutes

### Step 1: Seed Sample Data
```bash
python scripts/seed_data.py
```

Output:
```
[OK] Seeding complete!

Sample users created:
  - Username: waiter   | PIN: 1234  | Role: WAITER
  - Username: cashier  | PIN: 1234  | Role: CASHIER
  - Username: manager  | PIN: 1234  | Role: MANAGER
  - Username: clerk    | PIN: 1234  | Role: CLERK
```

### Step 2: Start API Server
```bash
python -m src
```

Wait for:
```
[OK] Starting on http://127.0.0.1:8000
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Step 3: Start Flet UI (in a separate terminal)
```bash
python -m src.ui.app
```

This produces no console output. Verify it's running:
```powershell
# Windows PowerShell
netstat -ano | Select-String ":8080"
```

Open in browser: **http://localhost:8080**

### Step 4: Run Tests (Optional but Recommended)
```bash
# In new terminal
pytest tests/ -v

# Or just integration tests
pytest tests/integration/ -v
pytest tests/smoke/ -v
```

---

## 🎯 What You Can Do Now

### Test via Swagger UI (Web Browser)
```
http://127.0.0.1:8000/docs
```

Try:
1. **Login**: POST /api/auth/login
   ```json
   {
     "username": "waiter",
     "pin": "1234"
   }
   ```

2. **Create Order**: POST /api/sales/orders
   ```json
   {
     "table_id": "1"
   }
   ```

3. **List Products**: GET /api/inventory/items

4. **Add Item to Order**: POST /api/sales/orders/{order_id}/items
   ```json
   {
     "item_id": "...",
     "quantity": 2
   }
   ```

5. **Finalize**: POST /api/sales/orders/{order_id}/finalize
   ```json
   {
     "payment_method": "CASH",
     "paid_amount": 750.00
   }
   ```

### Run Unit Tests
```bash
pytest tests/unit/ -v
```

### Run Full Test Suite with Coverage
```bash
pytest tests/ -v --cov=src --cov-report=html
open htmlcov/index.html
```

---

## 📋 What's Implemented

### Complete
- FastAPI Backend (Phase 1) -- running on http://127.0.0.1:8000
- Flet UI Screens (Phase 1.5) -- running on http://localhost:8080
  - Login screen with PIN keypad
  - POS order entry screen
  - Products/inventory screen
  - Daily reports screen
  - Receipt display screen
- Sample data generation
- Full test suite (unit + integration + smoke)
- Offline operation verified
- All startup bugs fixed (Unicode, asyncio, Flet API compat)

### 🚧 Ready for Phase 2
- Voice/chat assistant (code structure in place)
- Stock-in workflow (UI ready, logic TODO)
- Advanced reporting features
- Cloud sync infrastructure

---

## 📊 Sample Users

All with PIN: **1234**

| Username | Role | Permissions |
|----------|------|-------------|
| waiter | WAITER | Create orders, add items |
| cashier | CASHIER | All waiter + finalize payment |
| manager | MANAGER | All + void, discounts, stock adjustments |
| clerk | CLERK | Inventory management only |

---

## Troubleshooting

### Error: `Port 8000 already in use`
```powershell
# Find and kill the process (Windows)
netstat -ano | Select-String ":8000.*LISTENING"
taskkill /PID <pid> /T /F
```

### Error: `Port 8080 already in use` (Flet UI)
```powershell
netstat -ano | Select-String ":8080.*LISTENING"
taskkill /PID <pid> /T /F
```

### Error: `database is locked`
```bash
rm hms.db-shm hms.db-wal
python scripts/seed_data.py
python -m src
```

### Error: `ModuleNotFoundError`
Ensure venv is activated:
```bash
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows
```

### Flet UI shows no output in terminal
This is normal. Flet 0.21.x in WEB_BROWSER mode doesn't print to console. Verify via `netstat` and open http://localhost:8080.

### See also
Full error log with all bugs and fixes: **SKILLS.md**

---

## 📚 Documentation

- **README.md** - Full quick start & overview
- **TESTING.md** - Test strategy & setup
- **PHASE_1_5_SUMMARY.md** - Phase 1.5 implementation details
- **constitution.md** - Design principles
- **specification.md** - Requirements

---

## ✨ Next Steps

### To Add New Features
1. Update API endpoints in `src/api/app.py`
2. Update service logic in `src/application/services.py`
3. Add tests in `tests/integration/` or `tests/unit/`
4. Run `pytest tests/ -v` to verify

### To Enhance UI (Phase 2)
1. Edit screen files in `src/ui/screens/`
2. Add components in `src/ui/components/`
3. Test manually via Swagger UI or with pytest

---

**Version**: Phase 1.5 MVP | **Status**: App Running (API :8000 + UI :8080) | **Last Updated**: 2026-02-11
