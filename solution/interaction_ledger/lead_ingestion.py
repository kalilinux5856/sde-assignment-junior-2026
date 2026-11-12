
import json
from pathlib import Path
from interaction_ledger.normalization import (
    normalize_header,
    normalize_phone,
    normalize_date,
    normalize_decimal,
    normalize_enum,
)

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
