import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib

from interaction_ledger.database import get_connection
from interaction_ledger.normalization import normalize_phone
from interaction_ledger.security import hash_phone
from interaction_ledger.lead_ingestion import calculate_file_hash
import json

VALID_EVENT_TYPES = {
    "call.initiated",
    "call.connected",
    "call.ended",
    "call.telephony_failed",
    "disposition.set",
    "disposition.override",
}


def parse_event_line(raw_line: str, dispositions: dict):
    """
    Parse and validate one JSONL record.

    Returns:
        (event, phone, outcome)

    outcome can be:
        valid
        malformed
        unknown_disposition
    """

    try:
        event = json.loads(raw_line)
    except json.JSONDecodeError:
        return None, None, "malformed"

    # Each JSONL record must be a JSON object.
    if not isinstance(event, dict):
        return None, None, "malformed"

    # An event without an ID cannot be tracked or deduplicated.
    event_id = event.get("event_id")

    if not isinstance(event_id, str) or not event_id.strip():
        return None, None, "malformed"

    event["event_id"] = event_id.strip()

    if event.get("event_type") not in VALID_EVENT_TYPES:
        return None, None, "malformed"

    # Validate disposition codes against their workflow.
    if event["event_type"] in {
        "disposition.set",
        "disposition.override",
    }:
        workflow_id = event.get("workflow_id")
        disposition_code = event.get("payload", {}).get(
            "disposition_code"
        ) if isinstance(event.get("payload"), dict) else None

        valid_codes = dispositions.get(workflow_id, set())

        if disposition_code not in valid_codes:
            return None, None, "unknown_disposition"

    # Extract the phone separately so it never enters payload_json.
    phone = event.pop("phone", None)

    return event, phone, "valid"

def store_event(
    connection,
    event: dict,
    phone: str | None,
    source_file_id: int,
    line_number: int,
):
    """
    Store one valid event in the append-only events table.

    Returns:
        inserted
        duplicate
    """

    event_id = event["event_id"]

    existing = connection.execute(
        "SELECT event_id FROM events WHERE event_id = ?",
        (event_id,),
    ).fetchone()

    if existing:
        return "duplicate"

    phone_hash = None

    if phone:
        try:
            canonical_phone = normalize_phone(phone)
            phone_hash = hash_phone(canonical_phone)

        except ValueError:
            # Invalid phone does not invalidate the event.
            # Store the event without a phone hash.
            phone_hash = None

    occurred_at = normalize_event_timestamp(event["occurred_at"])

    connection.execute(
        """
        INSERT INTO events (
            event_id,
            workflow_id,
            call_id,
            event_type,
            occurred_at,
            phone_hash,
            payload_json,
            source_file_id,
            source_line_number
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            event["workflow_id"],
            event["call_id"],
            event["event_type"],
            occurred_at,
            phone_hash,
            json.dumps(event),
            source_file_id,
            line_number,
        ),
    )

    return "inserted"

def ingest_event_file(file_path: Path) -> dict:
    """
    Ingest one JSONL event file.

    Supports resuming an interrupted file ingestion by
    checking ingestion_records for previously processed lines.
    """

    file_path = file_path.resolve()
    content_hash = calculate_file_hash(file_path)
    source_path = str(file_path)

    stats = {
        "events_total": 0,
        "stored": 0,
        "malformed": 0,
        "unknown_disposition": 0,
        "duplicate": 0,
        "skipped": 0,
    }

    dispositions = load_dispositions()

    # Step 1: Register the source file.
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO ingestion_files (
                source_path,
                file_type,
                content_sha256,
                status
            )
            VALUES (?, 'events', ?, 'processing')
            """,
            (source_path, content_hash),
        )

        file_record = connection.execute(
            """
            SELECT id, status, content_sha256
            FROM ingestion_files
            WHERE source_path = ?
            """,
            (source_path,),
        ).fetchone()

        source_file_id = file_record["id"]

        if file_record["content_sha256"] != content_hash:
            raise ValueError(
                f"Source file changed after registration: {file_path}"
            )

        if file_record["status"] == "processed":
            return {"status": "already_processed", **stats}

    # Step 2: Process each non-empty line.
    for line_number, event, phone, outcome in read_event_file(
        file_path, dispositions
    ):
        stats["events_total"] += 1

        with get_connection() as connection:

            # Have we already processed this exact source line?
            previous_record = connection.execute(
                """
                SELECT id
                FROM ingestion_records
                WHERE source_file_id = ?
                  AND record_type = 'event'
                  AND record_number = ?
                """,
                (source_file_id, line_number),
            ).fetchone()

            if previous_record:
                stats["skipped"] += 1
                continue

            reason = None

            if outcome == "malformed":
                stats["malformed"] += 1
                reason = "malformed_event"

            elif outcome == "unknown_disposition":
                stats["unknown_disposition"] += 1
                reason = "unknown_disposition"

            else:
                try:
                    result = store_event(
                        connection,
                        event,
                        phone,
                        source_file_id,
                        line_number,
                    )

                    if result == "duplicate":
                        outcome = "duplicate"
                        stats["duplicate"] += 1
                        reason = "duplicate_event_id"
                    else:
                        outcome = "stored"
                        stats["stored"] += 1

                except (ValueError, KeyError, TypeError):
                    outcome = "malformed"
                    stats["malformed"] += 1
                    reason = "invalid_event_fields"

            # Record the processing result.
            connection.execute(
                """
                INSERT INTO ingestion_records (
                    source_file_id,
                    record_type,
                    record_number,
                    outcome,
                    reason
                )
                VALUES (?, 'event', ?, ?, ?)
                """,
                (
                    source_file_id,
                    line_number,
                    outcome,
                    reason,
                ),
            )

    # Step 3: Mark the file as completely processed.
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE ingestion_files
            SET status = 'processed',
                processed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (source_file_id,),
        )

    return {"status": "processed", **stats}

def read_event_file(file_path: Path, dispositions: dict):
    """
    Read a JSONL file one non-empty line at a time.

    Yields:
        (physical_line_number, event, phone, outcome)
    """

    with file_path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):

            # Blank lines do not count as event records.
            if not raw_line.strip():
                continue

            event, phone, outcome = parse_event_line(
                raw_line, dispositions
            )

            yield line_number, event, phone, outcome


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DISPOSITIONS_PATH = (
    PROJECT_ROOT
    / "assignment-a-data"
    / "schemas"
    / "dispositions.csv"
)

IST = timezone(timedelta(hours=5, minutes=30))


def normalize_event_timestamp(value: str) -> str:
    """
    Convert an event timestamp into UTC.

    Naive timestamps are interpreted as IST.
    """

    if not value or not value.strip():
        raise ValueError("Invalid event timestamp")

    value = value.strip()

    # Convert the Z suffix into an explicit UTC offset.
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    parsed = datetime.fromisoformat(value)

    # Assignment rule: timestamps without timezone mean IST.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)

    # Convert everything into UTC.
    utc_time = parsed.astimezone(timezone.utc)

    return utc_time.isoformat()


def load_dispositions() -> dict:
    """
    Load valid disposition codes for each workflow.
    """

    dispositions = {}

    with DISPOSITIONS_PATH.open(
        "r", encoding="utf-8", newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            workflow_id = row["workflow_id"]
            code = row["code"]

            dispositions.setdefault(workflow_id, set()).add(code)

    return dispositions

