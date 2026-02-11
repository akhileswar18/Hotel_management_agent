-- HMS Phase 1 SQLite Schema
-- Initial schema creation for core tables
-- All monetary values stored as INTEGER (cents, not paise)
-- All timestamps in UTC
-- All IDs are UUIDs (stored as TEXT)

-- USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    pin_hash TEXT NOT NULL,  -- bcrypt hashed PIN
    role TEXT NOT NULL CHECK (role IN ('WAITER', 'CASHIER', 'MANAGER', 'CLERK', 'ADMIN')),
    created_at TEXT NOT NULL,  -- ISO 8601 UTC
    updated_at TEXT NOT NULL,
    created_by TEXT,  -- FK users.id
    updated_by TEXT
);

-- SESSIONS TABLE (for offline login caching, Phase 2+)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    login_at TEXT NOT NULL,
    logout_at TEXT,
    device_id TEXT,
    expires_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- ITEMS/PRODUCTS TABLE
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price_cents INTEGER NOT NULL,  -- in paisa: 15000 = ₹150.00
    reorder_level INTEGER DEFAULT 10,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (created_by) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);

-- TABLES (Seating/Covers)
CREATE TABLE IF NOT EXISTS tables_seating (
    id TEXT PRIMARY KEY,
    table_number TEXT NOT NULL UNIQUE,
    capacity INTEGER DEFAULT 4,
    status TEXT DEFAULT 'available' CHECK (status IN ('available', 'occupied', 'reserved')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- ORDERS TABLE (Bills/Invoices)
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    table_id TEXT,  -- FK tables_seating.id (or guest name)
    status TEXT NOT NULL CHECK (status IN ('draft', 'finalized', 'voided')),
    subtotal_cents INTEGER NOT NULL,  -- Sum of line items before discount
    discount_cents INTEGER DEFAULT 0,  -- Total discount applied
    tax_cents INTEGER NOT NULL,  -- Calculated tax amount
    total_cents INTEGER NOT NULL,  -- subtotal - discount + tax
    receipt_number TEXT UNIQUE,  -- Immutable once finalized
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_by TEXT,
    finalized_at TEXT,  -- When order was paid & finalized
    finalized_by TEXT,  -- User who finalized
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (finalized_by) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_table_id ON orders(table_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_receipt_number ON orders(receipt_number);

-- ORDER LINE ITEMS TABLE
CREATE TABLE IF NOT EXISTS order_line_items (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    item_name TEXT NOT NULL,  -- Snapshot of item name at time of order
    quantity INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL,  -- Price at time of order
    discount_cents INTEGER DEFAULT 0,  -- Line-level discount
    tax_cents INTEGER NOT NULL,  -- Tax on this line
    total_cents INTEGER NOT NULL,  -- (quantity * unit_price) - discount + tax
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (item_id) REFERENCES items(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_order_line_items_order_id ON order_line_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_line_items_item_id ON order_line_items(item_id);

-- PAYMENTS TABLE
CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL UNIQUE,  -- One payment per order (refunds create new order)
    amount_cents INTEGER NOT NULL,  -- Amount tendered
    method TEXT NOT NULL CHECK (method IN ('CASH', 'CARD', 'VOUCHER')),
    reference TEXT,  -- Card ref, voucher code, check number
    finalized_at TEXT NOT NULL,
    finalized_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (finalized_by) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_finalized_at ON payments(finalized_at);

-- STOCK LEDGER TABLE (Append-Only)
-- Never update existing entries. Stock-on-hand computed as SUM(quantity_change)
CREATE TABLE IF NOT EXISTS stock_ledger (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('PURCHASE', 'SALE', 'ADJUSTMENT', 'WASTAGE', 'RETURN')),
    quantity_change INTEGER NOT NULL,  -- Positive for stock-in, negative for deduction
    reason TEXT NOT NULL,  -- "Sale ORD-123", "Inventory recount", "Damaged goods", etc.
    reference_id TEXT,  -- order_id, PO_id, or null for manual adjustments
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES items(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_stock_ledger_item_id ON stock_ledger(item_id);
CREATE INDEX IF NOT EXISTS idx_stock_ledger_created_at ON stock_ledger(created_at);

-- VOID RECORDS TABLE (Never delete original orders)
CREATE TABLE IF NOT EXISTS void_records (
    id TEXT PRIMARY KEY,
    original_order_id TEXT NOT NULL,
    void_reason TEXT NOT NULL,
    voided_at TEXT NOT NULL,
    voided_by TEXT NOT NULL,
    approved_by TEXT,  -- Manager approval for voids
    created_at TEXT NOT NULL,
    FOREIGN KEY (original_order_id) REFERENCES orders(id),
    FOREIGN KEY (voided_by) REFERENCES users(id),
    FOREIGN KEY (approved_by) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_void_records_order_id ON void_records(original_order_id);

-- AUDIT LOG TABLE (Immutable, append-only)
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,  -- "Order", "Payment", "StockLedger", "User"
    entity_id TEXT NOT NULL,
    operation TEXT NOT NULL,  -- "CREATE", "UPDATE", "VOID", "FINALIZE", "DELETE"
    user_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,  -- ISO 8601 UTC
    old_state TEXT,  -- JSON string (for update operations)
    new_state TEXT,  -- JSON string
    reason TEXT,  -- Why the change was made
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);

-- SYSTEM LOG TABLE (Queryable logs)
CREATE TABLE IF NOT EXISTS system_log (
    id TEXT PRIMARY KEY,
    level TEXT NOT NULL,  -- DEBUG, INFO, WARN, ERROR
    category TEXT NOT NULL,  -- sales.billing, inventory.stock, auth.login, system.error
    user_id TEXT,
    action TEXT,  -- Specific action that occurred
    entity_type TEXT,  -- Type of entity affected
    entity_id TEXT,
    timestamp TEXT NOT NULL,  -- ISO 8601 UTC
    message TEXT,
    details TEXT  -- JSON details
);
CREATE INDEX IF NOT EXISTS idx_system_log_timestamp ON system_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_log_category ON system_log(category, timestamp);
CREATE INDEX IF NOT EXISTS idx_system_log_user ON system_log(user_id, timestamp);

-- MIGRATIONS TRACKING
CREATE TABLE IF NOT EXISTS migrations_applied (
    migration_name TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    rolled_back_at TEXT
);
