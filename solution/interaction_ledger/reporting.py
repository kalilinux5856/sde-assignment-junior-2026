
import csv
from pathlib import Path

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
