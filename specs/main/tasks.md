# Tasks: HMS Phase 2 — Enhanced Features & Deployment

**Input**: Design documents from `/specs/main/`
**Prerequisites**: plan.md, Phase 1 completion checklist
**Updated**: 2026-02-11

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1 — COMPLETE (carried forward)

All Phase 1 tasks are marked [X] in `specs/main/checklists/phase1-completion.md`.

**Test Results**: 70/70 passing (22 unit + 41 integration + 8 smoke)

### Completed Phase 2 Tasks (from prior work)

- [x] T001 [P] [US1] Add date range filter to reports screen in src/ui/screens/reports_screen.py
- [x] T002 [P] [US1] Implement CSV export for daily sales report in src/ui/screens/reports_screen.py
- [x] T003 [P] [US1] Implement CSV export for inventory snapshot in src/ui/screens/reports_screen.py
- [x] T004 [P] [US2] Add Edit Product dialog (update price, reorder level) in src/ui/screens/products_screen.py
- [x] T005 [P] [US2] Add PATCH /api/inventory/items/{id} endpoint in src/api/app.py
- [x] T006 [P] [US2] Add ItemRepository.update_item() in src/infrastructure/repositories.py
- [x] T007 [P] [US3] Add order item removal (remove line item) in src/ui/screens/pos_screen.py
- [x] T008 [P] [US3] Add DELETE /api/sales/orders/{id}/items/{lid} endpoint in src/api/app.py
- [x] T009 [US4] Add role-based UI visibility (hide void/discount for waiters) in src/ui/screens/pos_screen.py

---

## Phase 2: Deployment & DevOps (Priority: P1) ✅ COMPLETE

**Goal**: Package the app for distribution, containerize, and set up automated CI/CD so every commit is tested.

**Independent Test**: Build the PyInstaller exe, run the Docker container, push a commit and verify CI passes.

### Implementation

- [x] T010 [P] [US5] Create PyInstaller .spec configuration file in hms.spec
- [x] T011 [US5] Create build script for Windows executable in scripts/build_exe.ps1
- [x] T012 [US5] Test PyInstaller executable runs standalone (API + UI launch) — unified launcher created in src/launcher.py
- [x] T013 [P] [US6] Create Dockerfile for HMS app in Dockerfile
- [x] T014 [P] [US6] Create docker-compose.yml with API + UI services in docker-compose.yml
- [x] T015 [US6] Add .dockerignore to exclude dev artifacts in .dockerignore
- [x] T016 [US6] Docker entrypoint script created in scripts/docker-entrypoint.sh
- [x] T017 [P] [US7] Create GitHub Actions CI workflow (lint + test on push) in .github/workflows/ci.yml
- [x] T018 [US7] Add code coverage reporting with pytest-cov (target: 80%+) in .github/workflows/ci.yml
- [x] T019 [P] [US7] Write RELEASE_NOTES_v1.0.md in RELEASE_NOTES_v1.0.md
- [x] T020 [P] [US7] Write DEPLOYMENT.md (installation guide for all 3 methods) in DEPLOYMENT.md

**Checkpoint**: App is distributable as .exe, Docker image, and every push runs CI tests.

---

## Phase 3: Order Enhancements (Priority: P2) COMPLETE

**Goal**: Improve order workflow — edit quantities, hold/resume orders, view order history.

**Independent Test**: Create order, edit qty, hold it, resume, finalize. View in order history.

### Implementation

- [x] T021 [US8] Add order item quantity editing (change qty on existing line item) in src/ui/screens/pos_screen.py
- [x] T022 [US8] Add PATCH /api/sales/orders/{id}/items/{lid} endpoint for qty update in src/api/app.py
- [x] T023 [US8] Add SalesService.update_item_quantity() in src/application/services.py
- [x] T024 [P] [US9] Add hold/resume order functionality — set order status to "held" in src/application/services.py
- [x] T025 [US9] Add hold/resume buttons and UI flow in src/ui/screens/pos_screen.py
- [x] T026 [US9] Add POST /api/sales/orders/{id}/hold and /resume endpoints in src/api/app.py
- [x] T027 [P] [US10] Add order history screen (past orders with search) in src/ui/screens/order_history_screen.py
- [x] T028 [US10] Add GET /api/sales/orders?status=&date= search endpoint in src/api/app.py
- [x] T029 [US10] Wire order history screen into NavigationRail in src/ui/app.py

**Checkpoint**: Full order lifecycle works — create, edit qty, hold, resume, finalize, view history.

---

## Phase 4: Product & Inventory Enhancements (Priority: P2) COMPLETE

**Goal**: Better product management — soft delete, category search, stock adjustments with approval.

**Independent Test**: Archive a product, search by category, submit and approve a stock adjustment.

### Implementation

- [x] T030 [P] [US11] Add Delete/Archive product (soft delete — is_active flag) in src/infrastructure/repositories.py
- [x] T031 [US11] Add PATCH /api/inventory/items/{id}/archive endpoint in src/api/app.py
- [x] T032 [US11] Add archive button to products screen in src/ui/screens/products_screen.py
- [x] T033 [P] [US12] Add product search/filter by category on products screen in src/ui/screens/products_screen.py
- [x] T034 [US12] Add GET /api/inventory/items?category= query param in src/api/app.py
- [ ] T035 [P] [US13] Add Stock Adjustment UI with manager approval flow in src/ui/screens/products_screen.py
- [ ] T036 [US13] Add stock adjustment approval service logic in src/application/services.py
- [x] T037 [US13] Add is_active column for soft-delete (schema migration 002) in migrations/002_add_is_active.sql

**Checkpoint**: Products can be archived and filtered. Stock adjustment approval deferred to Phase 6.

---

## Phase 5: Advanced Reporting (Priority: P2) COMPLETE

**Goal**: Transaction search, payment method filters, and category-based reports.

**Independent Test**: Search transactions by date range and payment method, filter reports by category.

### Implementation

- [x] T038 [P] [US14] Add transaction search endpoint GET /api/reports/transactions in src/api/app.py
- [x] T039 [US14] Add ReportingService.search_transactions() in src/application/services.py
- [x] T040 [US14] Wire transaction search UI to reports screen in src/ui/screens/reports_screen.py
- [x] T041 [P] [US15] Add payment method filter to daily sales report in src/ui/screens/reports_screen.py
- [x] T042 [P] [US15] Add item category filter to reports in src/ui/screens/reports_screen.py

**Checkpoint**: Reports are fully filterable by date, payment method, and category.

---

## Phase 6: Auth & Session Management (Priority: P3)

**Goal**: Server-side sessions with timeout, user management screen for managers.

**Independent Test**: Login, wait 30 min, verify session expires. Create/edit/deactivate users from manager screen.

### Implementation

- [ ] T043 [US16] Implement server-side session store (sessions table) in src/infrastructure/repositories.py
- [ ] T044 [US16] Add session expiry (30 min inactivity timeout) in src/application/services.py
- [ ] T045 [US16] Add session validation middleware to API in src/api/app.py
- [ ] T046 [P] [US17] Add user management screen (CRUD for users, manager only) in src/ui/screens/user_mgmt_screen.py
- [ ] T047 [US17] Add user CRUD API endpoints in src/api/app.py
- [ ] T048 [US17] Wire user management into NavigationRail (manager only) in src/ui/app.py

**Checkpoint**: Sessions expire after inactivity, managers can create/edit users from the UI.

---

## Phase 7: UI Polish & Accessibility (Priority: P3)

**Goal**: Dark mode, keyboard shortcuts, toast notifications, accessibility improvements.

**Independent Test**: Toggle dark mode, use keyboard shortcuts for New Order / Finalize, see toast instead of dialog.

### Implementation

- [ ] T049 [P] [US18] Add dark mode toggle in src/ui/app.py
- [ ] T050 [P] [US18] Add keyboard shortcuts for common actions in src/ui/screens/pos_screen.py
- [ ] T051 [US18] Add notification/toast system (replace AlertDialogs) in src/ui/components/ui_helpers.py
- [ ] T052 [P] [US18] Add error overlay banner (global error display) in src/ui/app.py
- [ ] T053 [US19] Improve WCAG AAA compliance (contrast, labels) across src/ui/

**Checkpoint**: App feels polished — dark mode, keyboard-driven, non-blocking feedback.

---

## Phase 8: Receipt & Printing (Priority: P4)

**Goal**: Thermal printer support, email receipts, receipt reprint.

**Independent Test**: Print a receipt to ESC/POS printer, email a receipt, reprint from history.

### Implementation

- [ ] T054 [P] [US20] Integrate with ESC/POS thermal printer protocol in src/infrastructure/printer.py
- [ ] T055 [US20] Add print receipt button to finalize flow in src/ui/screens/pos_screen.py
- [ ] T056 [P] [US21] Add receipt email functionality (SMTP) in src/infrastructure/email_sender.py
- [ ] T057 [US21] Add email receipt button to receipt screen in src/ui/screens/receipt_screen.py
- [ ] T058 [US22] Add receipt reprint from order history in src/ui/screens/order_history_screen.py
- [ ] T059 [P] [US22] Add digital receipt (QR code link) in src/ui/screens/receipt_screen.py

**Checkpoint**: Receipts can be printed, emailed, reprinted, and shared via QR.

---

## Phase 9: Data & Performance (Priority: P4)

**Goal**: Database backup/restore, better seed data, performance benchmarks.

**Independent Test**: Backup DB, restore from backup, run 1000 txn benchmark.

### Implementation

- [ ] T060 [P] [US23] Add database backup/restore functionality in src/infrastructure/database.py
- [ ] T061 [P] [US23] Add backup/restore CLI commands in scripts/backup.py
- [ ] T062 [US24] Add data seed script improvements (realistic sample data) in scripts/seed_data.py
- [ ] T063 [US24] Add performance benchmarks (1000 transactions/day target) in tests/performance/test_benchmarks.py
- [ ] T064 [P] [US24] Add database vacuuming scheduled task in src/infrastructure/database.py

**Checkpoint**: DB can be backed up and restored, performance meets 1000 txn/day target.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup affecting multiple areas

- [ ] T065 [P] Update IMPLEMENTATION_SUMMARY.md with Phase 2 status
- [ ] T066 [P] Update specs/main/checklists/ with Phase 2 completion status
- [ ] T067 Code cleanup and refactoring across src/
- [ ] T068 [P] Add multi-language support i18n framework in src/ui/
- [ ] T069 Security hardening (input validation, CSRF, rate limiting) in src/api/app.py
- [ ] T070 Run full regression test suite and validate 80%+ coverage

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: COMPLETE — no action needed
- **Phase 2 (Deployment)**: HIGH PRIORITY — can start immediately, no blockers
- **Phase 3 (Orders)**: Can start in parallel with Phase 2 (different files)
- **Phase 4 (Products)**: Can start in parallel with Phase 2, 3 (different files)
- **Phase 5 (Reporting)**: Can start in parallel with Phase 2, 3, 4 (different files)
- **Phase 6 (Auth)**: Depends on existing auth infrastructure (already complete)
- **Phase 7 (UI Polish)**: Can start after Phase 3-5 features are stable
- **Phase 8 (Receipts)**: Depends on Phase 3 (order history) for reprint
- **Phase 9 (Data)**: Independent — can start anytime
- **Phase 10 (Polish)**: Depends on all desired phases being complete

### Within Phase 2 (Deployment)

```
T010 → T011 → T012   (PyInstaller: spec → build script → test)
T013 + T014 → T015 → T016   (Docker: Dockerfile + compose → ignore → test)
T017 → T018   (CI/CD: workflow → coverage)
T019, T020 [P]   (Docs: parallel, independent)
```

### Parallel Opportunities

- **Phase 2**: T010, T013, T017, T019, T020 can all start in parallel (different files)
- **Phase 3**: T021, T024, T027 can start in parallel (different features)
- **Phase 4**: T030, T033, T035 can start in parallel (different features)
- **Phase 5**: T038, T041, T042 can start in parallel (different features)
- **Phases 2-5**: Can all proceed in parallel as they touch different file areas

---

## Implementation Strategy

### Recommended Order (Deployment First)

1. **Phase 2: Deployment** — Package, containerize, CI/CD (HIGH PRIORITY, user requested)
2. **Phase 3: Orders** — Most user-facing value (edit qty, hold/resume, history)
3. **Phase 4: Products** — Completes inventory management
4. **Phase 5: Reporting** — Adds search and filters
5. **Phase 6: Auth** — Session security
6. **Phase 7: UI Polish** — Dark mode, keyboard, toasts
7. **Phase 8: Receipts** — Printer/email integration
8. **Phase 9: Data** — Backup, benchmarks
9. **Phase 10: Polish** — Final cleanup

### Task Summary

| Phase | Area | Tasks | Status |
|-------|------|-------|--------|
| 1 | Setup (P1) | 46/48 | COMPLETE |
| — | Prior P2 work | 9 | COMPLETE |
| 2 | Deployment & DevOps | 11 (T010-T020) | COMPLETE |
| 3 | Order Enhancements | 9 (T021-T029) | **COMPLETE** |
| 4 | Product & Inventory | 6/8 (T030-T037) | **COMPLETE** (2 deferred) |
| 5 | Advanced Reporting | 5 (T038-T042) | **COMPLETE** |
| 6 | Auth & Sessions | 6 (T043-T048) | Pending |
| 7 | UI Polish | 5 (T049-T053) | Pending |
| 8 | Receipt & Printing | 6 (T054-T059) | Pending |
| 9 | Data & Performance | 5 (T060-T064) | Pending |
| 10 | Polish & Cross-Cut | 6 (T065-T070) | Pending |
| **Total** | | **70 tasks** | **42 done, 28 remaining** |

---

## Notes

- [P] tasks = different files, no dependencies — can run in parallel
- [Story] label maps task to specific user story for traceability
- Each phase is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- Phase 2 (Deployment) elevated to HIGH PRIORITY per user request (was previously Week 5+)
