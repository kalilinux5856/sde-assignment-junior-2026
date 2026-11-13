
from interaction_ledger.call_reconstruction import classify_lead


# Small set of disposition rules for our tests
DISPOSITION_RULES = {
    "motor_renewal": {
        "renewed": {
            "is_terminal": True,
            "is_success": True,
        },
        "not_interested": {
            "is_terminal": True,
            "is_success": False,
        },
        "callback_requested": {
            "is_terminal": False,
            "is_success": False,
        },
    }
}


def test_lead_with_no_calls():
    result = classify_lead(
        "motor_renewal",
        [],
        DISPOSITION_RULES,
    )

    assert result == "yet_to_reach_out"


def test_lead_with_terminal_disposition():
    calls = [
        {
            "effective_disposition": "renewed",
            "telephony_failed": False,
        }
    ]

    result = classify_lead(
        "motor_renewal",
        calls,
        DISPOSITION_RULES,
    )

    assert result == "completed"


def test_all_calls_telephony_failed():
    calls = [
        {
            "effective_disposition": None,
            "telephony_failed": True,
        },
        {
            "effective_disposition": None,
            "telephony_failed": True,
        },
    ]

    result = classify_lead(
        "motor_renewal",
        calls,
        DISPOSITION_RULES,
    )

    assert result == "in_progress_telephony_failed"


def test_mixed_call_outcomes():
    calls = [
        {
            "effective_disposition": None,
            "telephony_failed": True,
        },
        {
            "effective_disposition": None,
            "telephony_failed": False,
        },
    ]

    result = classify_lead(
        "motor_renewal",
        calls,
        DISPOSITION_RULES,
    )

    assert result == "in_progress_dialed"


def test_terminal_disposition_has_priority_over_failed_calls():
    calls = [
        {
            "effective_disposition": None,
            "telephony_failed": True,
        },
        {
            "effective_disposition": "renewed",
            "telephony_failed": False,
        },
    ]

    result = classify_lead(
        "motor_renewal",
        calls,
        DISPOSITION_RULES,
    )

    assert result == "completed"


def test_non_terminal_disposition_is_still_in_progress():
    calls = [
        {
            "effective_disposition": "callback_requested",
            "telephony_failed": False,
        }
    ]

    result = classify_lead(
        "motor_renewal",
        calls,
        DISPOSITION_RULES,
    )

    assert result == "in_progress_dialed"
