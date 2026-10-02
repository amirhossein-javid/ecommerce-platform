from decimal import Decimal

from django.core.exceptions import ValidationError

STORE_CURRENCY = "IRR"


def validate_whole_rial(value):
    amount = Decimal(value)
    if amount != amount.to_integral_value():
        raise ValidationError(
            "Ensure this value is a whole number of rials.",
            code="fractional_rial",
        )
