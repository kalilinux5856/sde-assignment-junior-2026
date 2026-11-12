
PRAGMA foreign_keys = ON;

-- 1. Keep track of files received by our application.
CREATE TABLE IF NOT EXISTS ingestion_files (
    id INTEGER PRIMARY KEY,
    source_path TEXT NOT NULL UNIQUE,
    file_type TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'processed',
    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Keep track of uploaded lead batches.
CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    batch_name TEXT NOT NULL,
    source_file_id INTEGER NOT NULL,

    UNIQUE (workflow_id, batch_name),

    FOREIGN KEY (source_file_id)
        REFERENCES ingestion_files(id)
);

-- 3. Store one unique lead per workflow and phone hash.
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    phone_hash TEXT NOT NULL,
    pii_encrypted BLOB NOT NULL,
    lead_data_json TEXT NOT NULL,
    batch_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (workflow_id, phone_hash),

    FOREIGN KEY (batch_id)
        REFERENCES batches(id)
);

-- 4. Store the original interaction events.
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    call_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    phone_hash TEXT,
    payload_json TEXT NOT NULL,
    source_file_id INTEGER NOT NULL,
    source_line_number INTEGER NOT NULL,
    received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (source_file_id)
        REFERENCES ingestion_files(id)
);

-- 5. Associate events with leads separately.
CREATE TABLE IF NOT EXISTS event_lead_links (
    event_id TEXT PRIMARY KEY,
    lead_id INTEGER NOT NULL,
    linked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (event_id)
        REFERENCES events(event_id),

    FOREIGN KEY (lead_id)
        REFERENCES leads(id)
);

-- 6. Store rejected lead rows.
CREATE TABLE IF NOT EXISTS rejections (
    id INTEGER PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    batch_id INTEGER NOT NULL,
    row_number INTEGER NOT NULL,
    reason TEXT NOT NULL,

    UNIQUE (batch_id, row_number),

    FOREIGN KEY (batch_id)
        REFERENCES batches(id)
);

-- Indexes for frequently used lookups.
CREATE INDEX IF NOT EXISTS idx_leads_workflow
    ON leads(workflow_id);

CREATE INDEX IF NOT EXISTS idx_events_call
    ON events(workflow_id, call_id);

CREATE INDEX IF NOT EXISTS idx_events_timestamp
    ON events(workflow_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_events_phone
    ON events(workflow_id, phone_hash);

CREATE INDEX IF NOT EXISTS idx_event_lead_links_lead
    ON event_lead_links(lead_id);

-- Prevent modification or deletion of original events.
CREATE TRIGGER IF NOT EXISTS prevent_event_update
BEFORE UPDATE ON events
BEGIN
    SELECT RAISE(ABORT, 'Events are append-only');
END;

CREATE TRIGGER IF NOT EXISTS prevent_event_delete
BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'Events are append-only');
END;
