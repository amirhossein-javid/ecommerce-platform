import pytest
from django.core.exceptions import ValidationError

from apps.accounts.validators import validate_e164_phone_number


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
