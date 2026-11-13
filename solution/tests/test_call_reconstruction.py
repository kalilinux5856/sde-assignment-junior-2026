import pytest

from interaction_ledger.call_reconstruction import reconstruct_call


def make_event(event_type, occurred_at, payload=None):
    return {
        "event_id": f"event-{event_type}-{occurred_at}",
        "workflow_id": "motor_renewal",
        "call_id": "call-001",
        "event_type": event_type,
        "occurred_at": occurred_at,
        "payload_json": {
            "payload": payload or {}
        } if False else __import__("json").dumps({
            "payload": payload or {}
        }),
        "lead_id": 101,
    }


def test_call_without_initiated_event_is_ignored():
    events = [
        make_event("call.connected", "2026-10-01T05:30:00+00:00")
    ]

    result = reconstruct_call(
        ("motor_renewal", "call-001"),
        events
    )

    assert result is None


def test_call_without_disposition():
    events = [
        make_event("call.initiated", "2026-10-01T05:30:00+00:00"),
        make_event("call.connected", "2026-10-01T05:31:00+00:00"),
    ]

    result = reconstruct_call(
        ("motor_renewal", "call-001"),
        events
    )

    assert result["effective_disposition"] is None
    assert result["connected"] is True
    assert result["telephony_failed"] is False


def test_latest_disposition_set_wins():
    events = [
        make_event("call.initiated", "2026-10-01T05:30:00+00:00"),
        make_event(
            "disposition.set",
            "2026-10-01T05:32:00+00:00",
            {"disposition_code": "callback_requested"}
        ),
        make_event(
            "disposition.set",
            "2026-10-01T05:35:00+00:00",
            {"disposition_code": "renewed"}
        ),
    ]

    result = reconstruct_call(
        ("motor_renewal", "call-001"),
        events
    )

    assert result["effective_disposition"] == "renewed"


def test_override_takes_precedence_over_disposition_set():
    events = [
        make_event("call.initiated", "2026-10-01T05:30:00+00:00"),
        make_event(
            "disposition.set",
            "2026-10-01T05:32:00+00:00",
            {"disposition_code": "renewed"}
        ),
        make_event(
            "disposition.override",
            "2026-10-01T05:40:00+00:00",
            {"disposition_code": "not_interested"}
        ),
    ]

    result = reconstruct_call(
        ("motor_renewal", "call-001"),
        events
    )

    assert result["effective_disposition"] == "not_interested"


def test_latest_override_wins():
    events = [
        make_event("call.initiated", "2026-10-01T05:30:00+00:00"),
        make_event(
            "disposition.override",
            "2026-10-01T05:40:00+00:00",
            {"disposition_code": "not_interested"}
        ),
        make_event(
            "disposition.override",
            "2026-10-01T05:45:00+00:00",
            {"disposition_code": "renewed"}
        ),
    ]

    result = reconstruct_call(
        ("motor_renewal", "call-001"),
        events
    )

    assert result["effective_disposition"] == "renewed"
