from pathlib import Path

from interaction_ledger.database import (
    initialize_database,
    get_connection,
)

from interaction_ledger.lead_ingestion import ingest_lead_file
from interaction_ledger.event_ingestion import ingest_event_file
from interaction_ledger.event_linking import link_pending_events

from interaction_ledger.reporting import (
    generate_batch_summary,
    generate_daily_overview,
    generate_lead_report,
    generate_rejections_report,
    generate_data_quality_report,
)


# Repository root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Location of generated assignment data
DATA_DIR = PROJECT_ROOT / "data"


def main():

    print("\n========== INTERACTION LEDGER PIPELINE ==========\n")

    # STEP 1: Initialize database
    print("[1/5] Initializing database...")
    initialize_database()

    # STEP 2: Process each data drop
    drop_directories = sorted(DATA_DIR.glob("drop_*"))

    for drop_dir in drop_directories:

        print(f"\nProcessing {drop_dir.name}...")

        # STEP 2A: Ingest lead CSV files
        lead_files = sorted(
            (drop_dir / "leads").glob("*/*.csv")
        )

        for lead_file in lead_files:
            result = ingest_lead_file(lead_file)
            print(f"Lead file: {lead_file.name} -> {result}")

        # STEP 2B: Ingest event JSONL files
        event_files = sorted(
            (drop_dir / "events").glob("*.jsonl")
        )

        for event_file in event_files:
            result = ingest_event_file(event_file)
            print(f"Event file: {event_file.name} -> {result}")

        # STEP 2C: Link events to leads
        with get_connection() as connection:
            linked_count = link_pending_events(connection)

        print(f"New event-to-lead links: {linked_count}")

    # STEP 3: Generate all reports
    print("\n[4/5] Generating reports...")

    with get_connection() as connection:

        generate_batch_summary(connection)
        generate_daily_overview(connection)
        generate_lead_report(connection)
        generate_rejections_report(connection)
        generate_data_quality_report(connection)

    # STEP 4: Finish
    print("\n[5/5] Pipeline completed successfully!")
    print(f"Reports generated in: {PROJECT_ROOT / 'solution' / 'reports'}")


if __name__ == "__main__":
    main()
 