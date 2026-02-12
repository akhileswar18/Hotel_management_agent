-- Migration 002: Add is_active column to items for soft-delete
ALTER TABLE items ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1;
