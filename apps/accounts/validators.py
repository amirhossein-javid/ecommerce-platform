from django.core.validators import RegexValidator

validate_e164_phone_number = RegexValidator(
    regex=r"\A\+[1-9][0-9]{0,14}\Z",
    message="Enter a phone number in canonical E.164 format.",
    code="invalid_phone_number",
)
