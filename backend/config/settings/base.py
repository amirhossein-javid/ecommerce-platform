"""Settings shared by all environments."""

from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, []),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    DJANGO_CORS_ALLOWED_ORIGINS=(list, []),
)
environ.Env.read_env(BASE_DIR.parent / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-development-only")
DEBUG = env.bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "apps.common.admin_config.NaghshAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "corsheaders",
    "apps.accounts.apps.AccountsConfig",
    "apps.carts.apps.CartsConfig",
    "apps.common.apps.CommonConfig",
    "apps.orders.apps.OrdersConfig",
    "apps.payments.apps.PaymentsConfig",
    "apps.products.apps.ProductsConfig",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.common.admin_locale.AdminPersianLocaleMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgresql://ecommerce:ecommerce@db:5432/ecommerce",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        )
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = False
CORS_URLS_REGEX = r"^/api/.*$"
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-cart-token",
    "x-csrftoken",
    "x-requested-with",
]


def _throttle_rate(variable_name, default):
    rate = env(variable_name, default=default).strip()
    try:
        request_count, period = rate.split("/", maxsplit=1)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"{variable_name} must use the '<requests>/<period>' format."
        ) from exc
    if (
        not request_count.isdigit()
        or int(request_count) <= 0
        or period not in {"s", "second", "m", "minute", "h", "hour", "d", "day"}
    ):
        raise ImproperlyConfigured(
            f"{variable_name} must use a positive request count and a supported period."
        )
    return rate


THROTTLE_NUM_PROXIES = env.int("DJANGO_THROTTLE_NUM_PROXIES", default=0)
if THROTTLE_NUM_PROXIES < 0:
    raise ImproperlyConfigured(
        "DJANGO_THROTTLE_NUM_PROXIES must be zero or a positive integer."
    )

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": _throttle_rate("DJANGO_THROTTLE_AUTH_REGISTER_RATE", "5/hour"),
        "auth_login": _throttle_rate("DJANGO_THROTTLE_AUTH_LOGIN_RATE", "10/minute"),
        "auth_refresh": _throttle_rate(
            "DJANGO_THROTTLE_AUTH_REFRESH_RATE", "30/minute"
        ),
        "cart_mutation": _throttle_rate(
            "DJANGO_THROTTLE_CART_MUTATION_RATE", "60/minute"
        ),
        "checkout": _throttle_rate("DJANGO_THROTTLE_CHECKOUT_RATE", "10/minute"),
        "payment_initiate": _throttle_rate(
            "DJANGO_THROTTLE_PAYMENT_INITIATE_RATE", "10/minute"
        ),
        "payment_verify": _throttle_rate(
            "DJANGO_THROTTLE_PAYMENT_VERIFY_RATE", "20/minute"
        ),
        "bale_webhook": _throttle_rate(
            "DJANGO_THROTTLE_BALE_WEBHOOK_RATE", "300/minute"
        ),
        "review_mutation": _throttle_rate(
            "DJANGO_THROTTLE_REVIEW_MUTATION_RATE", "10/hour"
        ),
    },
    "NUM_PROXIES": THROTTLE_NUM_PROXIES,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": env("DJANGO_JWT_SIGNING_KEY", default=SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "E-commerce API",
    "DESCRIPTION": "REST API for the e-commerce platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

PAYMENT_GATEWAY_CLASS = env(
    "PAYMENT_GATEWAY_CLASS",
    default="apps.payments.gateways.UnavailablePaymentGateway",
)
BALE_BOT_TOKEN = env("BALE_BOT_TOKEN", default="")
BALE_PROVIDER_TOKEN = env("BALE_PROVIDER_TOKEN", default="")
BALE_CONNECT_TIMEOUT = env.float("BALE_CONNECT_TIMEOUT", default=3.0)
BALE_READ_TIMEOUT = env.float("BALE_READ_TIMEOUT", default=10.0)
BALE_WEBHOOK_URL = env("BALE_WEBHOOK_URL", default="")
