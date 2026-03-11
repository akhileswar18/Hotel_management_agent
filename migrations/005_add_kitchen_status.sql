-- Migration 005: Add kitchen_status to orders for KDS progression

ALTER TABLE orders
ADD COLUMN kitchen_status TEXT DEFAULT 'PENDING'
CHECK (kitchen_status IN ('PENDING', 'COOKING', 'READY', 'SERVED'));

