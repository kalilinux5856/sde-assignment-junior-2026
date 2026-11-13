import csv
import hashlib
import json
from pathlib import Path
from interaction_ledger.normalization import (
    normalize_header,
    normalize_phone,
    normalize_date,
    normalize_decimal,
    normalize_enum,
)
from interaction_ledger.database import get_connection
from interaction_ledger.security import hash_phone, encrypt_pii, decrypt_pii

SCHEMA_DIR = (
    Path(__file__).resolve().parents[2]
    / "assignment-a-data"
    / "schemas"
)


def load_workflow_schema(workflow_id: str) -> dict:
    """
    Load the JSON schema for a workflow.
    """
    schema_path = SCHEMA_DIR / f"{workflow_id}.json"

    if not schema_path.exists():
        raise ValueError(f"Unknown workflow: {workflow_id}")

    with schema_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_header_mapping(schema: dict, csv_headers: list[str]) -> dict:
    """
    Map incoming CSV headers to canonical schema field names.
    """
    alias_mapping = {}

    for field in schema["fields"]:
        canonical_name = field["name"]

        possible_names = [
            canonical_name,
            *field.get("aliases", []),
        ]

        for name in possible_names:
            normalized_name = normalize_header(name)
            alias_mapping[normalized_name] = canonical_name

    header_mapping = {}

    for csv_header in csv_headers:
        normalized_header = normalize_header(csv_header)

        canonical_name = alias_mapping.get(normalized_header)

        if canonical_name:
            header_mapping[csv_header] = canonical_name

    return header_mapping


def validate_and_normalize_row(
    raw_row: dict,
    schema: dict,
    header_mapping: dict,
) -> tuple[dict | None, str | None, list[str]]:
    """
    Validate and normalize one CSV row.

    Returns:
        normalized_data, rejection_reason, warnings
    """

    # Convert incoming CSV column names to canonical field names.
    mapped_row = {}

    for incoming_header, value in raw_row.items():
        canonical_name = header_mapping.get(incoming_header)

        if canonical_name:
            mapped_row[canonical_name] = value

    normalized_data = {}
    warnings = []

    # Process fields in the exact order defined by the schema.
    for field in schema["fields"]:
        field_name = field["name"]
        field_type = field["type"]
        required = field.get("required", False)

        raw_value = mapped_row.get(field_name)

        # Convert empty strings and whitespace-only strings to None.
        if raw_value is not None:
            raw_value = raw_value.strip() or None

        # Required field missing: reject immediately.
        if required and raw_value is None:
            return None, f"missing_required:{field_name}", []

        # Optional field missing: store None.
        if raw_value is None:
            normalized_data[field_name] = None
            continue

        try:
            if field_type == "string":
                value = raw_value

            elif field_type == "phone":
                value = normalize_phone(raw_value)

            elif field_type == "date":
                value = normalize_date(raw_value)

            elif field_type == "decimal":
                value = normalize_decimal(raw_value)

            elif field_type == "enum":
                value = normalize_enum(
                    raw_value,
                    field.get("values", []),
                )

            else:
                raise ValueError(f"unsupported_field_type:{field_type}")

            normalized_data[field_name] = value

        except ValueError as error:
            # Invalid required field: reject the row.
            if required:
                return None, str(error), []

            # Invalid optional field: preserve the row, but record warning.
            normalized_data[field_name] = None
            warnings.append(field_name)

    return normalized_data, None, warnings



def upsert_lead(connection, workflow_id, normalized_data, schema, batch_id):
    phone = normalized_data["phone"]
    phone_hash = hash_phone(phone)

    # Separate sensitive information from ordinary business data.
    pii_fields = {
        field["name"]
        for field in schema["fields"]
        if field.get("pii", False)
    }

    pii_data = {
        key: value
        for key, value in normalized_data.items()
        if key in pii_fields and value is not None
    }

    business_data = {
        key: value
        for key, value in normalized_data.items()
        if key not in pii_fields and value is not None
    }

    existing_lead = connection.execute(
        """
        SELECT id, pii_encrypted, lead_data_json, batch_id
        FROM leads
        WHERE workflow_id = ? AND phone_hash = ?
        """,
        (workflow_id, phone_hash),
    ).fetchone()

    if existing_lead is None:
        encrypted_pii = encrypt_pii(json.dumps(pii_data))

        connection.execute(
            """
            INSERT INTO leads (
                workflow_id, phone_hash, pii_encrypted,
                lead_data_json, batch_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                workflow_id,
                phone_hash,
                encrypted_pii,
                json.dumps(business_data),
                batch_id,
            ),
        )

        return "inserted"

    # Existing lead: merge only non-null incoming values.
    old_pii = json.loads(
        decrypt_pii(existing_lead["pii_encrypted"])
    )

    old_business = json.loads(existing_lead["lead_data_json"])

    old_pii.update(pii_data)
    old_business.update(business_data)

    encrypted_pii = encrypt_pii(json.dumps(old_pii))

    connection.execute(
        """
        UPDATE leads
        SET pii_encrypted = ?,
            lead_data_json = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            encrypted_pii,
            json.dumps(old_business),
            existing_lead["id"],
        ),
    )

    return "merged"

def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 of a file's contents."""

    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)

    return digest.hexdigest()


def ingest_lead_file(file_path: Path) -> dict:
    """
    Process one CSV file and store its valid leads.
    """

    workflow_id = file_path.parent.name
    batch_name = file_path.stem
    file_hash = calculate_file_hash(file_path)
    source_path = str(file_path.resolve())

    schema = load_workflow_schema(workflow_id)

    stats = {
        "rows_total": 0,
        "rows_rejected": 0,
        "duplicates_merged": 0,
        "inserted": 0,
        "field_warnings": {},
        "skipped": False,
    }

    # Register the source file and retrieve its batch.
    with get_connection() as connection:

        existing_file = connection.execute(
            """
            SELECT id, content_sha256, status
            FROM ingestion_files
            WHERE source_path = ?
            """,
            (source_path,),
        ).fetchone()

        if existing_file:
            if existing_file["content_sha256"] != file_hash:
                raise ValueError(
                    f"File contents changed after registration: {source_path}"
                )

            if existing_file["status"] == "processed":
                stats["skipped"] = True
                return stats

            source_file_id = existing_file["id"]

        else:
            cursor = connection.execute(
                """
                INSERT INTO ingestion_files (
                    source_path,
                    file_type,
                    content_sha256,
                    status
                )
                VALUES (?, 'leads', ?, 'processing')
                """,
                (source_path, file_hash),
            )

            source_file_id = cursor.lastrowid

        connection.execute(
            """
            INSERT OR IGNORE INTO batches (
                workflow_id,
                batch_name,
                source_file_id
            )
            VALUES (?, ?, ?)
            """,
            (workflow_id, batch_name, source_file_id),
        )

        batch = connection.execute(
            """
            SELECT id FROM batches
            WHERE workflow_id = ? AND batch_name = ?
            """,
            (workflow_id, batch_name),
        ).fetchone()

        batch_id = batch["id"]

    # Read and process the CSV.
    with file_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        reader = csv.DictReader(file)

        header_mapping = build_header_mapping(
            schema,
            reader.fieldnames or [],
        )

        
        for raw_row in reader:
            # Ignore completely blank rows.
            if all(value is None or not value.strip()
                for value in raw_row.values()):
                continue

            stats["rows_total"] += 1
            row_number = stats["rows_total"]

            # Check whether this row was processed previously.
            with get_connection() as connection:
                existing_record = connection.execute(
                    """
                    SELECT outcome
                    FROM ingestion_records
                    WHERE source_file_id = ?
                    AND record_type = 'lead'
                    AND record_number = ?
                    """,
                    (source_file_id, row_number),
                ).fetchone()

            if existing_record:
                continue

            normalized, rejection, warnings = validate_and_normalize_row(
                raw_row, schema, header_mapping
            )

            # Process this row and its ingestion record atomically.
            with get_connection() as connection:

                if rejection:
                    connection.execute(
                        """
                        INSERT INTO rejections (
                            workflow_id, batch_id, row_number, reason
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (workflow_id, batch_id, row_number, rejection),
                    )

                    connection.execute(
                        """
                        INSERT INTO ingestion_records (
                            source_file_id, record_type, record_number,
                            outcome, reason
                        )
                        VALUES (?, 'lead', ?, 'rejected', ?)
                        """,
                        (source_file_id, row_number, rejection),
                    )

                    stats["rows_rejected"] += 1
                    continue

                result = upsert_lead(
                    connection, workflow_id, normalized, schema, batch_id
                )

                connection.execute(
                    """
                    INSERT INTO ingestion_records (
                        source_file_id, record_type, record_number,
                        outcome, warnings_json
                    )
                    VALUES (?, 'lead', ?, ?, ?)
                    """,
                    (
                        source_file_id,
                        row_number,
                        result,
                        json.dumps(warnings),
                    ),
                )

            if result == "inserted":
                stats["inserted"] += 1
            elif result == "merged":
                stats["duplicates_merged"] += 1

            for warning in warnings:
                stats["field_warnings"][warning] = (
                    stats["field_warnings"].get(warning, 0) + 1
                )

    # Mark the file as fully processed.
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE ingestion_files
            SET status = 'processed'
            WHERE id = ?
            """,
            (source_file_id,),
        )

    return stats
