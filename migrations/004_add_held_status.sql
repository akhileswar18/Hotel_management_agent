-- Migration 004: Add 'held' to orders.status CHECK constraint
-- SQLite doesn't support ALTER COLUMN, so we recreate the table.

PRAGMA foreign_keys=OFF;

-- 1. Create new table with updated CHECK constraint
CREATE TABLE orders_new (
    id TEXT PRIMARY KEY,
    table_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('draft', 'finalized', 'voided', 'held')),
    subtotal_cents INTEGER NOT NULL,
    discount_cents INTEGER DEFAULT 0,
    tax_cents INTEGER NOT NULL,
    total_cents INTEGER NOT NULL,
    receipt_number TEXT UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_by TEXT,
    finalized_at TEXT,
    finalized_by TEXT,
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (finalized_by) REFERENCES users(id)
);

-- 2. Copy all existing data
INSERT INTO orders_new SELECT * FROM orders;

-- 3. Drop old table
DROP TABLE orders;

-- 4. Rename new table
ALTER TABLE orders_new RENAME TO orders;

PRAGMA foreign_keys=ON;
