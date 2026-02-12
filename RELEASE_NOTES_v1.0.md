# Release Notes — HMS v1.0.0

**Release Date**: February 11, 2026
**Status**: Production-ready MVP
**Platform**: Windows 10/11 (primary), Linux/macOS (Docker)

---

## What's New

### Hotel Management System v1.0.0 — First Release

This is the first production release of the Hotel Management System (HMS), an offline-first, touch-friendly Point of Sale system designed for hotel restaurants and retail counters.

---

## Features

### Point of Sale (POS)
- Create and manage orders with table assignment
- Add items from product catalog with quantity selection
- Real-time order total calculation (subtotal, tax at 18%, discount, grand total)
- Apply percentage or absolute discounts (up to 50%)
- Finalize orders with Cash, Card, or Voucher payment methods
- Void orders with mandatory reason and manager approval
- Remove individual line items from draft orders
- Formatted receipt display with unique receipt numbers (REC-YYYY-MMDD-######)

### Inventory Management
- Product catalog with name, category, price, and reorder level
- Record stock-in (purchases) with reference tracking
- Real-time stock-on-hand computed from append-only ledger
- Low-stock alerts (yellow warning when below reorder level, red when out of stock)
- Edit product details (price, reorder level)
- Stock adjustment with manager approval

### Reporting
- Daily sales summary: total revenue, transaction count, average order value
- Payment method breakdown (Cash, Card, Voucher)
- Top 5 selling items by quantity
- Inventory snapshot with total items and low-stock count
- Date range filter for historical reports
- CSV export for daily sales and inventory reports

### Authentication & Security
- PIN-based authentication (bcrypt-hashed, never stored in plaintext)
- Role-based access control: Waiter, Cashier, Manager, Clerk, Admin
- Role-based UI visibility (discount/void buttons hidden for unauthorized roles)
- Immutable audit trail for every state change
- Structured logging to database and rotating log files

### Architecture & Quality
- Offline-first: all operations work without internet
- Local SQLite database with WAL mode and foreign key enforcement
- Money stored as integer cents (no floating-point errors)
- Append-only stock ledger (immutable transaction history)
- 70 automated tests (22 unit + 41 integration + 8 smoke)
- FastAPI REST backend with 16+ endpoints
- Flet touch-first UI with 5 screens

---

## Deployment Options

### 1. Python (Development)
```bash
pip install -r requirements.txt
python -m src          # API server (port 8000)
python -m src.ui.app   # Flet UI (port 8080)
```

### 2. Windows Executable
```powershell
.\scripts\build_exe.ps1
.\dist\HMS.exe         # Starts API + UI together
```

### 3. Docker
```bash
docker compose up      # API on :8000, UI on :8080
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

---

## System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 / Ubuntu 20.04 | Windows 11 / Ubuntu 22.04 |
| Python | 3.11 | 3.11+ |
| RAM | 512 MB | 1 GB |
| Disk | 200 MB | 500 MB |
| Screen | 1024x768 | 1280x800+ |
| Browser | Chrome/Edge (for Flet UI) | Latest Chrome/Edge |

---

## Known Limitations

1. **Single-user database**: SQLite supports one write at a time; for high-concurrency deployments, consider PostgreSQL migration (Phase 3+)
2. **No cloud sync**: All data is local. Cloud backup/sync planned for future releases.
3. **No thermal printer**: Print button shows "Print sent" stub. ESC/POS integration planned.
4. **No email receipts**: Receipt sharing via email/QR planned for future release.
5. **No dark mode**: Light theme only. Dark mode toggle planned for Phase 3.
6. **Session timeout**: Sessions do not auto-expire; manual logout required.
7. **No multi-language**: English only. i18n framework planned for future release.

---

## API Documentation

When the API server is running, interactive documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Test Results

```
tests/unit/          — 22 passed
tests/integration/   — 41 passed
tests/smoke/         —  8 passed
─────────────────────────────────
Total                — 70 passed, 0 failed
```

---

## Upgrade Notes

This is the initial release. No upgrade path needed.

For future upgrades:
1. Back up `hms.db` before upgrading
2. New migrations will apply automatically on first run
3. Check release notes for breaking changes

---

## Contributors

- HMS Development Team

---

## License

See [LICENSE](LICENSE) for details.
