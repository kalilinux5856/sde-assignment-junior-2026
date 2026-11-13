import pytest

from interaction_ledger.normalization import (
    normalize_phone,
    normalize_date,
    normalize_decimal,
    normalize_enum,
)


# -------------------------
# PHONE NORMALIZATION TESTS
# -------------------------

@pytest.mark.parametrize(
    "phone, expected",
    [
        ("9876543210", "+919876543210"),
        ("+919876543210", "+919876543210"),
        ("919876543210", "+919876543210"),
        ("09876543210", "+919876543210"),
        ("98765-43210", "+919876543210"),
    ],
)
def test_normalize_phone_valid(phone, expected):
    assert normalize_phone(phone) == expected


@pytest.mark.parametrize(
    "phone",
    [
        "",
        "1234567890",
        "12345",
        "987654321",
        "98765432101",
        "abcdefghij",
    ],
)
def test_normalize_phone_invalid(phone):
    with pytest.raises(ValueError):
        normalize_phone(phone)


# -------------------------
# DATE NORMALIZATION TESTS
# -------------------------

@pytest.mark.parametrize(
    "date, expected",
    [
        ("2026-11-21", "2026-11-21"),
        ("21/11/2026", "2026-11-21"),
        ("21-11-2026", "2026-11-21"),
        ("21-Nov-2026", "2026-11-21"),
    ],
)
def test_normalize_date_valid(date, expected):
    assert normalize_date(date) == expected


@pytest.mark.parametrize(
    "date",
    [
        "2026-02-30",
        "31/13/2026",
        "invalid-date",
    ],
)
def test_normalize_date_invalid(date):
    with pytest.raises(ValueError):
        normalize_date(date)


def test_normalize_date_empty():
    assert normalize_date("") is None


# -------------------------
# DECIMAL NORMALIZATION TESTS
# -------------------------

@pytest.mark.parametrize(
    "amount, expected",
    [
        ("27554", "27554.00"),
        ("₹27,554", "27554.00"),
        ("Rs. 27,554.50", "27554.50"),
        ("INR 100.5", "100.50"),
        ("100.567", "100.57"),
    ],
)
def test_normalize_decimal_valid(amount, expected):
    assert normalize_decimal(amount) == expected


@pytest.mark.parametrize(
    "amount",
    [
        "-100",
        "abc",
        "₹",
        "12,34,567",
    ],
)
def test_normalize_decimal_invalid(amount):
    with pytest.raises(ValueError):
        normalize_decimal(amount)


def test_normalize_decimal_empty():
    assert normalize_decimal("") is None


# -------------------------
# ENUM NORMALIZATION TESTS
# -------------------------

def test_normalize_enum_valid():
    assert normalize_enum("HI", ["en", "hi", "ta"]) == "hi"


def test_normalize_enum_invalid():
    with pytest.raises(ValueError):
        normalize_enum("fr", ["en", "hi", "ta"])


def test_normalize_enum_empty():
    assert normalize_enum("", ["en", "hi", "ta"]) is None
