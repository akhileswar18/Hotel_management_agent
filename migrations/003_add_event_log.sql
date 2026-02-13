-- Event log table for agent-based architecture
-- Append-only: events are never modified or deleted
CREATE TABLE IF NOT EXISTS event_log (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    source TEXT NOT NULL,
    correlation_id TEXT,
    user_id TEXT,
    payload TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_event_log_type ON event_log(type);
CREATE INDEX IF NOT EXISTS idx_event_log_correlation ON event_log(correlation_id);
CREATE INDEX IF NOT EXISTS idx_event_log_created ON event_log(created_at);
