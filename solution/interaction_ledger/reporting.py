
import csv
from pathlib import Path
from datetime import datetime, timedelta, timezone
IST = timezone(timedelta(hours=5, minutes=30))
import json
from interaction_ledger.lead_ingestion import load_workflow_schema
from interaction_ledger.security import decrypt_pii
from interaction_ledger.call_reconstruction import classify_all_leads


REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def generate_batch_summary(connection):
    """
    Generate batch_summary.csv.

    Groups leads by workflow and their original ingestion batch,
    then counts how many leads belong to each classification bucket.
    """

    # Step 1: Classify every lead.
    classifications = classify_all_leads(connection)

    # Create a lookup:
    # lead_id -> classification bucket
    bucket_by_lead = {
        lead["lead_id"]: lead["bucket"]
        for lead in classifications
    }

    # Step 2: Fetch each lead's original batch.
    leads = connection.execute("""
        SELECT
            l.id AS lead_id,
            l.workflow_id,
            b.batch_name
        FROM leads AS l
        JOIN batches AS b
            ON l.batch_id = b.id
        ORDER BY l.workflow_id, b.batch_name
    """).fetchall()

    # Step 3: Prepare counters for every workflow/batch combination.
    summary = {}

    for lead in leads:
        key = (lead["workflow_id"], lead["batch_name"])

        if key not in summary:
            summary[key] = {
                "total_leads": 0,
                "yet_to_reach_out": 0,
                "in_progress_telephony_failed": 0,
                "in_progress_dialed": 0,
                "completed": 0
            }

        # Step 4: Count this lead in its batch and bucket.
        bucket = bucket_by_lead[lead["lead_id"]]

        summary[key]["total_leads"] += 1
        summary[key][bucket] += 1

    # Step 5: Write the CSV.
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = REPORTS_DIR / "batch_summary.csv"

    fieldnames = [
        "workflow_id",
        "batch_id",
        "total_leads",
        "yet_to_reach_out",
        "in_progress_telephony_failed",
        "in_progress_dialed",
        "completed"
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for (workflow_id, batch_name), counts in sorted(summary.items()):
            writer.writerow({
                "workflow_id": workflow_id,
                "batch_id": batch_name,
                **counts
            })

    print(f"Generated: {output_path}")

    return output_path


def generate_daily_overview(connection):
    """
    Generate daily_overview.csv.

    Groups reconstructed calls by workflow and IST date.
    """

    from interaction_ledger.call_reconstruction import (
        fetch_linked_events,
        group_events_into_calls,
        reconstruct_call,
        load_disposition_rules
    )

    disposition_rules = load_disposition_rules()

    # Retrieve linked events and group them into calls.
    events = fetch_linked_events(connection)
    event_groups = group_events_into_calls(events)

    # Reconstruct calls.
    calls = []

    for call_key, call_events in event_groups.items():
        call = reconstruct_call(call_key, call_events)

        if call is not None:
            calls.append(call)

    # Aggregate calls by workflow and IST date.
    summary = {}

    for call in calls:
        timestamp = datetime.fromisoformat(call["initiated_at"])
        ist_timestamp = timestamp.astimezone(IST)
        call_date = ist_timestamp.date().isoformat()

        key = (call["workflow_id"], call_date)

        if key not in summary:
            summary[key] = {
                "total_calls": 0,
                "connected_calls": 0,
                "success_leads": set()
            }

        summary[key]["total_calls"] += 1

        if call["connected"]:
            summary[key]["connected_calls"] += 1

        disposition = call["effective_disposition"]

        if disposition:
            rule = disposition_rules[call["workflow_id"]].get(
                disposition
            )

            if rule and rule["is_success"]:
                summary[key]["success_leads"].add(call["lead_id"])

    # Write the CSV.
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = REPORTS_DIR / "daily_overview.csv"

    fieldnames = [
        "workflow_id",
        "date",
        "total_calls",
        "connected_calls",
        "connectivity_rate",
        "success_leads"
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for (workflow_id, call_date), counts in sorted(summary.items()):
            total = counts["total_calls"]
            connected = counts["connected_calls"]

            writer.writerow({
                "workflow_id": workflow_id,
                "date": call_date,
                "total_calls": total,
                "connected_calls": connected,
                "connectivity_rate": f"{connected / total:.4f}",
                "success_leads": len(counts["success_leads"])
            })

    print(f"Generated: {output_path}")

    return output_path


def generate_lead_report(connection):
    """
    Generate lead_report.csv with one row per unique lead.
    """

    from interaction_ledger.call_reconstruction import (
        fetch_linked_events,
        group_events_into_calls,
        reconstruct_call,
        load_disposition_rules
    )

    disposition_rules = load_disposition_rules()

    # Step 1: Reconstruct all calls.
    events = fetch_linked_events(connection)
    event_groups = group_events_into_calls(events)

    calls = []

    for call_key, call_events in event_groups.items():
        call = reconstruct_call(call_key, call_events)

        if call is not None:
            calls.append(call)

    # Step 2: Group calls by lead.
    calls_by_lead = {}

    for call in calls:
        calls_by_lead.setdefault(call["lead_id"], []).append(call)

    # Step 3: Classify every lead.
    classifications = classify_all_leads(connection)

    bucket_by_lead = {
        lead["lead_id"]: lead["bucket"]
        for lead in classifications
    }

    # Step 4: Retrieve all leads and their original batches.
    leads = connection.execute("""
        SELECT
            l.id,
            l.workflow_id,
            l.phone_hash,
            l.pii_encrypted,
            l.lead_data_json,
            b.batch_name
        FROM leads AS l
        JOIN batches AS b
            ON l.batch_id = b.id
        ORDER BY l.workflow_id, l.id
    """).fetchall()

    # Step 5: Generate one report row per lead.
    report_rows = []

    for lead in leads:
        lead_id = lead["id"]
        workflow_id = lead["workflow_id"]

        business_data = json.loads(lead["lead_data_json"])

        # Find the external reference field from the workflow schema.
        schema = load_workflow_schema(workflow_id)

        reference_field = next(
            field["name"]
            for field in schema["fields"]
            if field.get("reference") is True
        )

        external_ref = business_data.get(reference_field)

        # Decrypt PII and mask the phone number.
        pii_data = json.loads(decrypt_pii(lead["pii_encrypted"]))
        phone = pii_data["phone"]

        phone_masked = phone[:3] + "******" + phone[-4:]

        lead_calls = calls_by_lead.get(lead_id, [])

        # Count calls and connected calls.
        total_calls = len(lead_calls)

        connected_calls = sum(
            1 for call in lead_calls if call["connected"]
        )

        # Find the latest call by initiation time.
        sorted_calls = sorted(
            lead_calls,
            key=lambda call: call["initiated_at"],
            reverse=True
        )

        last_call_at = ""

        if sorted_calls:
            timestamp = datetime.fromisoformat(
                sorted_calls[0]["initiated_at"]
            )

            last_call_at = timestamp.astimezone(IST).isoformat()

        # Find the effective disposition of the most recent
        # call that has a disposition.
        current_disposition = ""

        for call in sorted_calls:
            if call["effective_disposition"]:
                current_disposition = call["effective_disposition"]
                break

        # Check whether any call ever had a successful disposition.
        ever_success = any(
            call["effective_disposition"]
            and disposition_rules[workflow_id].get(
                call["effective_disposition"], {}
            ).get("is_success", False)
            for call in lead_calls
        )

        report_rows.append({
            "workflow_id": workflow_id,
            "external_ref": external_ref or "",
            "batch_id": lead["batch_name"],
            "phone_masked": phone_masked,
            "bucket": bucket_by_lead[lead_id],
            "total_calls": total_calls,
            "connected_calls": connected_calls,
            "last_call_at": last_call_at,
            "current_disposition": current_disposition,
            "ever_success": str(ever_success).lower()
        })

    # Step 6: Write the CSV.
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = REPORTS_DIR / "lead_report.csv"

    fieldnames = [
        "workflow_id",
        "external_ref",
        "batch_id",
        "phone_masked",
        "bucket",
        "total_calls",
        "connected_calls",
        "last_call_at",
        "current_disposition",
        "ever_success"
    ]

    report_rows.sort(
        key=lambda row: (row["workflow_id"], row["external_ref"])
    )

    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)

    print(f"Generated: {output_path}")

    return output_path


def generate_rejections_report(connection):
    """
    Generate rejections.csv containing rejected lead rows.
    No PII is included.
    """

    rows = connection.execute("""
        SELECT
            r.workflow_id,
            b.batch_name,
            r.row_number,
            r.reason
        FROM rejections AS r
        JOIN batches AS b
            ON r.batch_id = b.id
        ORDER BY
            r.workflow_id,
            b.batch_name,
            r.row_number
    """).fetchall()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = REPORTS_DIR / "rejections.csv"

    fieldnames = [
        "workflow_id",
        "batch_id",
        "row_number",
        "reason"
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow({
                "workflow_id": row["workflow_id"],
                "batch_id": row["batch_name"],
                "row_number": row["row_number"],
                "reason": row["reason"]
            })

    print(f"Generated: {output_path}")

    return output_path

def generate_data_quality_report(connection):
    """
    Generate data_quality.json with overall ingestion statistics.
    """

    # Step 1: Count lead ingestion outcomes.
    lead_counts = connection.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN outcome = 'rejected' THEN 1 ELSE 0 END)
                AS rejected,
            SUM(CASE WHEN outcome = 'merged' THEN 1 ELSE 0 END)
                AS merged
        FROM ingestion_records
        WHERE record_type = 'lead'
    """).fetchone()

    # Step 2: Count rejection reasons.
    rejection_rows = connection.execute("""
        SELECT reason, COUNT(*) AS total
        FROM rejections
        GROUP BY reason
        ORDER BY reason
    """).fetchall()

    rejections_by_reason = {
        row["reason"]: row["total"]
        for row in rejection_rows
    }

    # Step 3: Count warnings for individual fields.
    warning_rows = connection.execute("""
        SELECT warnings_json
        FROM ingestion_records
        WHERE record_type = 'lead'
          AND warnings_json != '[]'
    """).fetchall()

    field_warnings = {}

    for row in warning_rows:
        warnings = json.loads(row["warnings_json"])

        for field in warnings:
            field_warnings[field] = field_warnings.get(field, 0) + 1

    # Step 4: Count event ingestion outcomes.
    event_counts = connection.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN outcome = 'malformed' THEN 1 ELSE 0 END)
                AS malformed,
            SUM(CASE WHEN outcome = 'duplicate' THEN 1 ELSE 0 END)
                AS duplicate,
            SUM(CASE WHEN outcome = 'unknown_disposition' THEN 1 ELSE 0 END)
                AS unknown_disposition
        FROM ingestion_records
        WHERE record_type = 'event'
    """).fetchone()

    # Step 5: Count events that remain unlinked.
    orphan_count = connection.execute("""
        SELECT COUNT(*)
        FROM events AS e
        LEFT JOIN event_lead_links AS l
            ON e.event_id = l.event_id
        WHERE l.event_id IS NULL
    """).fetchone()[0]

    # Step 6: Assemble the final report.
    report = {
        "lead_rows_total": lead_counts["total"],
        "lead_rows_rejected": lead_counts["rejected"] or 0,
        "rejections_by_reason": rejections_by_reason,
        "duplicate_lead_rows_merged": lead_counts["merged"] or 0,
        "field_warnings": field_warnings,
        "events_total": event_counts["total"],
        "malformed_events": event_counts["malformed"] or 0,
        "duplicate_events_dropped": event_counts["duplicate"] or 0,
        "orphan_events": orphan_count,
        "unknown_disposition_events":
            event_counts["unknown_disposition"] or 0
    }

    # Step 7: Write the JSON file.
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = REPORTS_DIR / "data_quality.json"

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print(f"Generated: {output_path}")

    return output_path
