"""Settings for a production deployment."""

from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import env

DEBUG = False


def _configuration_error(variable_name, requirement):
    raise ImproperlyConfigured(f"{variable_name} must {requirement} in production.")


def _validate_secret(variable_name, value):
    normalized = value.strip()
    if (
        len(normalized) < 50
        or len(set(normalized)) < 5
        or normalized.startswith("django-insecure-")
        or "replace-this" in normalized.lower()
        or "change-me" in normalized.lower()
        or "changeme" in normalized.lower()
    ):
        _configuration_error(
            variable_name,
            "be a strong, non-placeholder value of at least 50 characters",
        )
    return normalized


def _validate_origins(variable_name, origins):
    validated = []
    for origin in origins:
        origin = origin.strip()
        try:
            parsed = urlsplit(origin)
            port = parsed.port
        except ValueError:
            _configuration_error(variable_name, "contain only valid HTTPS origins")
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
            or port is not None
            and not 1 <= port <= 65535
        ):
            _configuration_error(variable_name, "contain only valid HTTPS origins")
        validated.append(origin.rstrip("/"))
    return validated


SECRET_KEY = _validate_secret("DJANGO_SECRET_KEY", env("DJANGO_SECRET_KEY", default=""))
JWT_SIGNING_KEY = _validate_secret(
    "DJANGO_JWT_SIGNING_KEY", env("DJANGO_JWT_SIGNING_KEY", default="")
)
if JWT_SIGNING_KEY == SECRET_KEY:
    _configuration_error("DJANGO_JWT_SIGNING_KEY", "differ from DJANGO_SECRET_KEY")
SIMPLE_JWT["SIGNING_KEY"] = JWT_SIGNING_KEY  # noqa: F405

SECRET_KEY_FALLBACKS = [
    _validate_secret("DJANGO_SECRET_KEY_FALLBACKS", fallback)
    for fallback in env.list("DJANGO_SECRET_KEY_FALLBACKS", default=[])
    if fallback.strip()
]
if SECRET_KEY in SECRET_KEY_FALLBACKS or len(SECRET_KEY_FALLBACKS) != len(
    set(SECRET_KEY_FALLBACKS)
):
    _configuration_error(
        "DJANGO_SECRET_KEY_FALLBACKS",
        "contain unique keys that differ from DJANGO_SECRET_KEY",
    )

ALLOWED_HOSTS = [
    host.strip()
    for host in env.list("DJANGO_ALLOWED_HOSTS", default=[])
    if host.strip()
]
if not ALLOWED_HOSTS:
    _configuration_error("DJANGO_ALLOWED_HOSTS", "contain at least one hostname")
if any(host == "*" or "://" in host or "/" in host for host in ALLOWED_HOSTS):
    _configuration_error(
        "DJANGO_ALLOWED_HOSTS", "contain explicit hostnames without schemes or paths"
    )

CSRF_TRUSTED_ORIGINS = _validate_origins(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[]),
)
CORS_ALLOWED_ORIGINS = _validate_origins(  # noqa: F405
    "DJANGO_CORS_ALLOWED_ORIGINS",
    env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=[]),
)

database_url = env("DATABASE_URL", default="").strip()
if (
    not database_url
    or database_url == "postgresql://ecommerce:ecommerce@db:5432/ecommerce"
):
    _configuration_error(
        "DATABASE_URL", "be set and differ from the development placeholder"
    )
try:
    database_scheme = urlsplit(database_url).scheme
except ValueError:
    _configuration_error("DATABASE_URL", "be a valid PostgreSQL URL")
if database_scheme not in {"postgres", "postgresql"}:
    _configuration_error("DATABASE_URL", "use the PostgreSQL backend")
try:
    database_config = env.db_url_config(database_url)
except (ImproperlyConfigured, KeyError, ValueError):
    _configuration_error("DATABASE_URL", "be a valid PostgreSQL URL")
if database_config["ENGINE"] != "django.db.backends.postgresql":
    _configuration_error("DATABASE_URL", "use the PostgreSQL backend")
DATABASES = {"default": database_config}

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=3600)
if SECURE_HSTS_SECONDS <= 0:
    _configuration_error("DJANGO_SECURE_HSTS_SECONDS", "be greater than zero")
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False
)
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=False)
if SECURE_HSTS_PRELOAD and (
    not SECURE_HSTS_INCLUDE_SUBDOMAINS or SECURE_HSTS_SECONDS < 31_536_000
):
    _configuration_error(
        "DJANGO_SECURE_HSTS_PRELOAD",
        "only be enabled with includeSubDomains and at least one year of HSTS",
    )
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"

if env.bool("DJANGO_TRUST_X_FORWARDED_PROTO", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

valid_log_levels = {"INFO", "WARNING", "ERROR", "CRITICAL"}
django_log_level = env("DJANGO_LOG_LEVEL", default="INFO").upper()
app_log_level = env("DJANGO_APP_LOG_LEVEL", default="INFO").upper()
if django_log_level not in valid_log_levels:
    _configuration_error("DJANGO_LOG_LEVEL", "be INFO, WARNING, ERROR, or CRITICAL")
if app_log_level not in valid_log_levels:
    _configuration_error("DJANGO_APP_LOG_LEVEL", "be INFO, WARNING, ERROR, or CRITICAL")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "application": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "application",
        }
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": django_log_level,
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": app_log_level,
            "propagate": False,
        },
    },
}
