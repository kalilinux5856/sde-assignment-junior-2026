# Submission — Assignment A: Interaction Ledger & Reporting Pipeline

## Candidate

- **Name:** PRANEETH YANDAMURI
- **Assignment chosen:** A — Data
- **Time spent:** 9-10 HRS

## How to run

Run these commands from the repository root.

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Assignment A dependencies
pip install -r solution/requirements.txt

# Configure PII encryption
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the generated key into a `.env` file in the repository root:

```env
PII_ENCRYPTION_KEY=your_generated_key
```

Protect the file:

```bash
chmod 600 .env
```

Run the pipeline:

```bash
PYTHONPATH=solution python -m interaction_ledger.main
```

Run the tests:

```bash
PYTHONPATH=solution pytest -v
```

The pipeline reads generated input data from `data/` and writes five reports into `solution/reports/`.

## Design and architecture

The solution uses Python and SQLite to implement an ingestion, event-processing, and reporting pipeline.

### Processing flow

1. Initialize the SQLite database and create the required tables and indexes.
2. Process each data drop in order.
3. Ingest lead CSV files, map headers using workflow schemas, validate fields, normalize values, and reject invalid rows.
4. Merge duplicate leads using workflow ID and a deterministic phone hash as the identity.
5. Ingest JSONL interaction events, discard malformed and duplicate events, and retain valid events in an append-only ledger.
6. Link events to leads using workflow ID and phone hash. Events that cannot initially be linked remain pending and can be linked after later lead ingestion.
7. Reconstruct calls from their events, determine effective dispositions, and classify leads.
8. Generate the five required reports.

### Database design

SQLite contains seven tables:

- `ingestion_files`: tracks source files, hashes, processing status, and ingestion metadata.
- `batches`: identifies lead batches and their source files.
- `leads`: stores unique leads, encrypted PII, non-PII business data, and original batch identity.
- `events`: stores interaction events with event IDs, timestamps, payloads, and source references.
- `event_lead_links`: maps events to leads without modifying the event records.
- `rejections`: records invalid lead rows and their rejection reasons.
- `ingestion_records`: records individual lead/event processing outcomes to support idempotency and data-quality reporting.

Indexes support common lookups by workflow, phone hash, call ID, timestamp, lead ID, and ingestion outcome.

The `events` table is protected by SQLite triggers that reject UPDATE and DELETE operations.

### PII protection

Fields marked `pii: true` in workflow schemas are stored in a Fernet-encrypted JSON object in `leads.pii_encrypted`.

Phone numbers are normalized before matching and stored as SHA-256 hashes in `phone_hash`. Raw phone numbers are removed from event payloads before storage.

Non-PII business fields are stored separately in `lead_data_json`.

The encryption key is loaded from the root `.env` file and is excluded from Git.

## Decisions and assumptions

| Decision                               | Why                                                                                     | Alternative considered              |
| -------------------------------------- | --------------------------------------------------------------------------------------- | ----------------------------------- |
| SQLite instead of PostgreSQL           | The assignment permits SQLite and it simplifies local setup and reproducibility         | PostgreSQL                          |
| Separate ingestion and linking modules | Events can arrive before their corresponding leads                                      | Linking only during event ingestion |
| Append-only event ledger               | Preserves the historical interaction record, including disposition overrides            | Updating previous event records     |
| SHA-256 phone hash                     | Enables deterministic matching without storing raw phone numbers in the matching column | Plaintext phone matching            |
| Fernet encryption for PII              | Provides authenticated encryption for sensitive lead fields                             | Plaintext or reversible encoding    |
| Persist ingestion outcomes             | Supports re-runs and data-quality reporting                                             | Reprocessing every row on every run |
| UTC event timestamps                   | Provides a consistent timestamp representation across input formats                     | Storing mixed local timestamps      |

## Failure modes considered

- Invalid or missing required lead fields are rejected with a reason.
- Invalid optional fields are stored as null and recorded as field warnings.
- Duplicate leads are merged using workflow ID and normalized phone identity.
- Duplicate event IDs are dropped.
- Malformed JSONL records are counted and skipped.
- Unknown disposition codes are counted and excluded from event storage.
- Events without a matching lead are retained as unlinked events and can be linked later.
- Database transactions protect individual ingestion operations from partial commits.
- Re-running already processed files does not duplicate their records.
- Event UPDATE and DELETE operations are blocked by database triggers.

### Known limitations

- Phone hashes currently use unkeyed SHA-256. Because the valid phone-number space is limited, production deployment should use HMAC-SHA256 with a separate secret key.
- SQLite is suitable for this assignment but may not be appropriate for high-concurrency production workloads.
- The encryption key is supplied through an environment file; production deployment should use a managed secret store or KMS and a key-rotation strategy.
- File-level processing and record-level outcomes are persisted, but recovery from every possible process crash during file registration and processing has not been exhaustively tested.
- The solution has not been benchmarked against the largest generated dataset.

## Testing

The test suite contains 43 passing tests covering:

- Phone normalization and validation.
- Date normalization.
- Decimal normalization.
- Enum validation.
- Call reconstruction.
- Disposition and override precedence.
- Lead classification and classification priority.

Manual verification also covered:

- Lead and event ingestion.
- Duplicate lead merging and event deduplication.
- Event-to-lead linking and orphan counts.
- PII encryption and decryption.
- Absence of raw phone fields in event payloads.
- Append-only event update/delete protections.
- Database idempotency.
- Byte-for-byte report reproducibility.

## Results

Using the generated small dataset:

- Lead input rows: 2,057
- Rejected lead rows: 108
- Duplicate lead rows merged: 57
- Unique leads: 1,892
- Event lines read: 8,745
- Stored events: 8,481
- Malformed events: 8
- Duplicate events dropped: 235
- Unknown disposition events: 21
- Remaining unlinked events: 461
- Reconstructed calls: 2,536
- Connected calls: 1,467

Five reports are generated:

1. `batch_summary.csv`
2. `daily_overview.csv`
3. `lead_report.csv`
4. `rejections.csv`
5. `data_quality.json`

The database record counts remained unchanged after a full pipeline re-run. The five report files also produced identical SHA-256 hashes before and after a subsequent re-run.

## If I had another day

1. Replace unkeyed phone hashing with HMAC-SHA256 using a dedicated secret.
2. Add integration tests for crash recovery, orphan relinking, and full pipeline idempotency.
3. Benchmark the large generated dataset and optimize database operations if needed.
4. Add stronger transaction and file-resumption guarantees.
5. Evaluate PostgreSQL for a concurrent production ingestion workload.
