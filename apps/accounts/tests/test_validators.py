import pytest
from django.core.exceptions import ValidationError

from apps.accounts.validators import (
    validate_e164_phone_number,
    validate_iran_postal_code,
)


@pytest.mark.parametrize(
    "phone_number",
    ["+1", "+14155552671", "+989121234567", "+123456789012345"],
)
def test_e164_validator_accepts_canonical_phone_numbers(phone_number):
    validate_e164_phone_number(phone_number)


@pytest.mark.parametrize(
    "phone_number",
    [
        "14155552671",
        "+0123456789",
        "+1234567890123456",
        "+1 415 555 2671",
        "+1-415-555-2671",
        " +14155552671",
        "+14155552671 ",
        "+",
        "+۱۲۳۴۵۶۷۸۹",
        "+1۲۳۴۵۶۷۸۹",
    ],
)
def test_e164_validator_rejects_noncanonical_phone_numbers(phone_number):
    with pytest.raises(ValidationError) as exc_info:
        validate_e164_phone_number(phone_number)

    assert exc_info.value.code == "invalid_phone_number"


@pytest.mark.parametrize("postal_code", ["1234567890", "9876543210"])
def test_iran_postal_code_validator_accepts_ten_ascii_digits(postal_code):
    validate_iran_postal_code(postal_code)


@pytest.mark.parametrize(
    "postal_code",
    [
        "123456789",
        "12345678901",
        "12345-67890",
        "12345 67890",
        " 1234567890",
        "1234567890 ",
        "۱۲۳۴۵۶۷۸۹۰",
        "123456789a",
    ],
)
def test_iran_postal_code_validator_rejects_invalid_values(postal_code):
    with pytest.raises(ValidationError) as exc_info:
        validate_iran_postal_code(postal_code)

    assert exc_info.value.code == "invalid_postal_code"
