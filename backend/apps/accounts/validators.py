from django.core.validators import RegexValidator

validate_e164_phone_number = RegexValidator(
    regex=r"\A\+[1-9][0-9]{0,14}\Z",
    message="Enter a phone number in canonical E.164 format.",
    code="invalid_phone_number",
)

validate_iran_postal_code = RegexValidator(
    regex=r"\A[0-9]{10}\Z",
    message="Enter a valid 10-digit Iranian postal code.",
    code="invalid_postal_code",
)
