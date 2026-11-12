
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def normalize_header(header: str) -> str:
    """
    Standardize CSV column names.

    Example:
        ' Customer_Name ' -> 'customer name'
    """
    header = header.strip().lower()
    header = re.sub(r"[_\s]+", " ", header)

    return header


def normalize_phone(value: str) -> str:
    """
    Normalize an Indian mobile number.

    Returns:
        +91XXXXXXXXXX

    Raises:
        ValueError if the number is invalid.
    """
    if not value or not value.strip():
        raise ValueError("invalid_phone")

    # Remove spaces, brackets, hyphens, and other non-digit characters.
    digits = re.sub(r"\D", "", value)

    # Remove Indian country code when exactly 12 digits are present.
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]

    # Remove leading zero from an 11-digit number.
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    # Indian mobile numbers must have 10 digits and start with 6, 7, 8, or 9.
    if len(digits) != 10 or digits[0] not in "6789":
        raise ValueError("invalid_phone")

    return "+91" + digits


def normalize_date(value: str) -> str | None:
    """
    Convert supported date formats into YYYY-MM-DD.

    Returns None for an empty value.
    Raises ValueError for an invalid date.
    """
    if not value or not value.strip():
        return None

    value = value.strip()

    supported_formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d-%b-%Y",
    ]

    for date_format in supported_formats:
        try:
            parsed_date = datetime.strptime(value, date_format)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError("invalid_date")


def normalize_decimal(value: str) -> str | None:
    """
    Normalize currency/numeric values into a decimal string
    with exactly two decimal places.

    Example:
        '₹27,554' -> '27554.00'
    """
    if not value or not value.strip():
        return None

    value = value.strip()

    # Remove an optional currency prefix.
    value = re.sub(
        r"^(?:₹|Rs\.?|INR)\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )

    # Accept either ordinary digits or correctly grouped thousands.
    valid_number = re.fullmatch(
        r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?",
        value,
    )

    if not valid_number:
        raise ValueError("invalid_decimal")

    value = value.replace(",", "")

    try:
        number = Decimal(value)

        if number < 0:
            raise ValueError("invalid_decimal")

        number = number.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        return format(number, ".2f")

    except InvalidOperation:
        raise ValueError("invalid_decimal")


def normalize_enum(value: str, allowed_values: list[str]) -> str:
    """
    Convert an enum value to lowercase and validate it.
    """
    if not value or not value.strip():
        return None

    normalized = value.strip().lower()

    if normalized not in allowed_values:
        raise ValueError("invalid_enum")

    return normalized
