
from interaction_ledger.database import get_connection
import json
import csv
from interaction_ledger.event_ingestion import DISPOSITIONS_PATH
from collections import defaultdict

def fetch_linked_events(connection):
    """
    Retrieve events that have been successfully linked to leads.

    Each returned row contains:
    - Event information
    - The lead ID associated with the event
    """

    return connection.execute("""
        SELECT
            e.event_id,
            e.workflow_id,
            e.call_id,
            e.event_type,
            e.occurred_at,
            e.payload_json,
            l.lead_id
        FROM events AS e
        JOIN event_lead_links AS l
            ON e.event_id = l.event_id
        ORDER BY
            e.workflow_id,
            e.call_id,
            e.occurred_at
    """).fetchall()


def group_events_into_calls(events):
    """
    Group events belonging to the same call.

    Grouping key:
        (workflow_id, call_id)

    Returns a dictionary where each key identifies
    one call and its value contains all its events.
    """

    calls = {}

    for event in events:

        # Identify which call this event belongs to.
        call_key = (
            event["workflow_id"],
            event["call_id"]
        )

        # Create a group if this is the first event
        # encountered for this particular call.
        if call_key not in calls:
            calls[call_key] = []

        # Add this event to its call group.
        calls[call_key].append(dict(event))

    return calls


def reconstruct_call(call_key, events):
    """
    Convert a group of events into one logical call record.

    Returns None if the call has no call.initiated event.
    """

    # Sort events by their actual occurrence time.
    events = sorted(
        events,
        key=lambda event: event["occurred_at"]
    )

    # Separate events by their type.
    initiated_events = [
        event for event in events
        if event["event_type"] == "call.initiated"
    ]

    connected_events = [
        event for event in events
        if event["event_type"] == "call.connected"
    ]

    telephony_failed_events = [
        event for event in events
        if event["event_type"] == "call.telephony_failed"
    ]

    disposition_events = [
        event for event in events
        if event["event_type"] == "disposition.set"
    ]

    override_events = [
        event for event in events
        if event["event_type"] == "disposition.override"
    ]

    # A call only counts if call.initiated exists.
    if not initiated_events:
        return None

    # Choose the latest override if available.
    # Otherwise choose the latest regular disposition.
    effective_event = None

    if override_events:
        effective_event = override_events[-1]

    elif disposition_events:
        effective_event = disposition_events[-1]

    # Extract the disposition code from the event payload.
    effective_disposition = None

    if effective_event:
        payload = json.loads(effective_event["payload_json"])
        effective_disposition = (
            payload.get("payload", {}).get("disposition_code")
        )

    # All events in a call should belong to the same lead.
    lead_ids = {event["lead_id"] for event in events}

    if len(lead_ids) != 1:
        raise ValueError(
            f"Inconsistent lead IDs for call {call_key}: {lead_ids}"
        )

    return {
        "workflow_id": call_key[0],
        "call_id": call_key[1],
        "lead_id": next(iter(lead_ids)),
        "initiated_at": initiated_events[0]["occurred_at"],
        "connected": bool(connected_events),
        "telephony_failed": bool(telephony_failed_events),
        "effective_disposition": effective_disposition
    }


def load_disposition_rules():
    """
    Load terminal and success rules for every workflow
    from the dispositions.csv configuration.
    """

    rules = {}

    with open(DISPOSITIONS_PATH, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            workflow_id = row["workflow_id"]
            code = row["code"]

            # Create a dictionary for this workflow
            # if it does not exist yet.
            if workflow_id not in rules:
                rules[workflow_id] = {}

            rules[workflow_id][code] = {
                "is_terminal": row["is_terminal"].strip().lower() == "true",
                "is_success": row["is_success"].strip().lower() == "true"
            }

    return rules


def classify_lead(workflow_id, calls, disposition_rules):
    """
    Classify a lead into one of four business buckets.

    calls contains all reconstructed calls belonging to this lead.
    """

    # Rule 1: No calls means the lead has not been contacted.
    if not calls:
        return "yet_to_reach_out"

    # Rule 2: If ANY call has a terminal disposition,
    # the lead is considered completed.
    for call in calls:
        disposition = call["effective_disposition"]

        if disposition is None:
            continue

        rule = disposition_rules[workflow_id].get(disposition)

        if rule and rule["is_terminal"]:
            return "completed"

    # Rule 3: Every call must have experienced telephony failure.
    if all(call["telephony_failed"] for call in calls):
        return "in_progress_telephony_failed"

    # Rule 4: Everything else.
    return "in_progress_dialed"


def classify_all_leads(connection):
    """
    Reconstruct calls and classify every lead in the database.

    Returns a list containing one classification per lead.
    """

    # Load configuration.
    disposition_rules = load_disposition_rules()

    # Retrieve linked events.
    events = fetch_linked_events(connection)

    # Group events into calls.
    event_groups = group_events_into_calls(events)

    # Reconstruct valid calls.
    reconstructed_calls = []

    for call_key, call_events in event_groups.items():
        call = reconstruct_call(call_key, call_events)

        if call is not None:
            reconstructed_calls.append(call)

    # Organize reconstructed calls by lead ID.
    calls_by_lead = defaultdict(list)

    for call in reconstructed_calls:
        calls_by_lead[call["lead_id"]].append(call)

    # Retrieve every lead, including leads with no calls.
    leads = connection.execute("""
        SELECT id, workflow_id
        FROM leads
    """).fetchall()

    # Classify every lead.
    results = []

    for lead in leads:
        lead_calls = calls_by_lead[lead["id"]]

        bucket = classify_lead(
            lead["workflow_id"],
            lead_calls,
            disposition_rules
        )

        results.append({
            "lead_id": lead["id"],
            "workflow_id": lead["workflow_id"],
            "total_calls": len(lead_calls),
            "bucket": bucket
        })

    return results
