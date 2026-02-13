# Release Notes — HMS v2.0.0

**Release Date**: February 13, 2026
**Status**: Feature-complete
**Platform**: Windows 10/11 (primary), Linux/macOS (Docker)

---

## What's New in v2.0

### Phase 6: Auth & Session Management
- Server-side session store with 30-minute inactivity timeout
- Session validation on API calls with auto-refresh
- User management screen (create, edit roles, reset PINs) — manager only
- User CRUD API endpoints (GET/POST/PATCH /api/users)
- "Users" tab in nav rail visible only to managers/admins

### Phase 7: UI Polish & Accessibility
- Dark mode toggle (moon/sun icon in nav rail)
- Keyboard shortcuts: F2=New Order, F5=Finalize, F8=Hold, F9=Resume, Esc=Void
- Toast/snackbar notification system (non-blocking feedback)
- Global error banner overlay with dismiss button
- WCAG AAA color contrast (all colors upgraded to 7:1+ ratio)

### Phase 8: Receipt & Printing
- ESC/POS thermal printer driver (src/infrastructure/printer.py)
- Print receipt dialog after order finalization
- Text file receipt backup in receipts/ folder
- Email receipt via SMTP (HTML + plain text, src/infrastructure/email_sender.py)
- Email dialog on receipt screen with address input
- Reprint button on finalized orders in Order History
- Digital receipt URL with copy-to-clipboard
- Receipt API endpoint: GET /api/receipts/{receipt_number}

### Phase 9: Data & Performance
- Database backup/restore (Database.backup(), Database.restore())
- Backup CLI: python scripts/backup.py [backup|restore|list|vacuum]
- Expanded seed data: 24 menu items, sample orders (finalized, held, voided)
- Performance benchmarks: order creation, finalization, stock query, report gen
- DB vacuum for space reclamation

### Phase 10: Polish & Cross-Cutting
- Updated all documentation to reflect full completion
- Cleaned up TODO comments and Phase 1/2 stubs
- i18n framework with English + Hindi translations (src/ui/i18n.py)
- Security hardening: rate limiting (100 req/min), security headers, input validation
- Full regression: 73 tests passing (70+ unit/integration/smoke/performance)

### Bug Fixes
- Fixed stock validation: prevents adding more items than available stock
- Fixed NavigationRail "height is unbounded" error
- Fixed self.page property conflict in ft.Column subclasses (use self._page)
- Fixed ft.Icons capitalization (must be ft.icons in Flet 0.80.x)
- Fixed POS screen duplication on login

---

## Upgrade from v1.0

No database migration needed — v2.0 uses the same schema with one additional migration (002_add_is_active.sql) that runs automatically.

```bash
# Update code
git pull origin main

# Install any new dependencies
pip install -r requirements.txt

# Run (migrations apply automatically)
python -m src.launcher
```

---

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
