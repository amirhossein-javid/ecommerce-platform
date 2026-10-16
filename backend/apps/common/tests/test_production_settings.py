import json
import os
import subprocess
import sys

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

PRODUCTION_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.production",
    "DJANGO_SECRET_KEY": "production-secret-" + "aB3!xY7@" * 6,
    "DJANGO_JWT_SIGNING_KEY": "jwt-signing-key-" + "qR8#nM2$" * 6,
    "DJANGO_SECRET_KEY_FALLBACKS": "",
    "DJANGO_ALLOWED_HOSTS": "api.example.com,.internal.example.com",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "https://admin.example.com",
    "DJANGO_CORS_ALLOWED_ORIGINS": "https://shop.example.com",
    "DJANGO_SECURE_HSTS_SECONDS": "3600",
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS": "False",
    "DJANGO_SECURE_HSTS_PRELOAD": "False",
    "DJANGO_TRUST_X_FORWARDED_PROTO": "False",
    "DJANGO_THROTTLE_NUM_PROXIES": "0",
    "DJANGO_LOG_LEVEL": "WARNING",
    "DJANGO_APP_LOG_LEVEL": "INFO",
    "DJANGO_DB_CONN_MAX_AGE": "60",
    "DATABASE_URL": "postgresql://app:strong-password@database.example.com/store",
}


@override_settings(CORS_ALLOWED_ORIGINS=["https://shop.example.com"])
def test_cors_allows_only_configured_origin_on_api_routes():
    client = APIClient()

    allowed_response = client.get(
        reverse("common:health-check"), HTTP_ORIGIN="https://shop.example.com"
    )
    denied_response = client.get(
        reverse("common:health-check"), HTTP_ORIGIN="https://attacker.example"
    )

    assert allowed_response["Access-Control-Allow-Origin"] == "https://shop.example.com"
    assert "Access-Control-Allow-Credentials" not in allowed_response
    assert "Access-Control-Allow-Origin" not in denied_response


@override_settings(CORS_ALLOWED_ORIGINS=["https://shop.example.com"])
def test_cors_is_limited_to_api_routes():
    response = APIClient().get("/admin/login/", HTTP_ORIGIN="https://shop.example.com")

    assert "Access-Control-Allow-Origin" not in response


def _load_production_settings(overrides=None):
    environment = os.environ.copy()
    environment.update(PRODUCTION_ENV)
    environment.update(overrides or {})
    code = """
import json
from config.settings import production as settings

print(json.dumps({
    "DEBUG": settings.DEBUG,
    "ALLOWED_HOSTS": settings.ALLOWED_HOSTS,
    "CSRF_TRUSTED_ORIGINS": settings.CSRF_TRUSTED_ORIGINS,
    "CORS_ALLOWED_ORIGINS": settings.CORS_ALLOWED_ORIGINS,
    "CORS_ALLOW_CREDENTIALS": settings.CORS_ALLOW_CREDENTIALS,
    "CORS_URLS_REGEX": settings.CORS_URLS_REGEX,
    "CORS_ALLOW_HEADERS": settings.CORS_ALLOW_HEADERS,
    "SECURE_SSL_REDIRECT": settings.SECURE_SSL_REDIRECT,
    "SECURE_REDIRECT_EXEMPT": settings.SECURE_REDIRECT_EXEMPT,
    "SECURE_HSTS_SECONDS": settings.SECURE_HSTS_SECONDS,
    "SECURE_HSTS_INCLUDE_SUBDOMAINS": settings.SECURE_HSTS_INCLUDE_SUBDOMAINS,
    "SECURE_HSTS_PRELOAD": settings.SECURE_HSTS_PRELOAD,
    "SESSION_COOKIE_SECURE": settings.SESSION_COOKIE_SECURE,
    "SESSION_COOKIE_HTTPONLY": settings.SESSION_COOKIE_HTTPONLY,
    "SESSION_COOKIE_SAMESITE": settings.SESSION_COOKIE_SAMESITE,
    "CSRF_COOKIE_SECURE": settings.CSRF_COOKIE_SECURE,
    "CSRF_COOKIE_HTTPONLY": settings.CSRF_COOKIE_HTTPONLY,
    "CSRF_COOKIE_SAMESITE": settings.CSRF_COOKIE_SAMESITE,
    "SECURE_PROXY_SSL_HEADER": getattr(settings, "SECURE_PROXY_SSL_HEADER", None),
    "DJANGO_LOG_LEVEL": settings.LOGGING["loggers"]["django"]["level"],
    "APP_LOG_LEVEL": settings.LOGGING["loggers"]["apps"]["level"],
    "DB_CONN_MAX_AGE": settings.DATABASES["default"]["CONN_MAX_AGE"],
    "DB_CONN_HEALTH_CHECKS": settings.DATABASES["default"]["CONN_HEALTH_CHECKS"],
    "THROTTLE_NUM_PROXIES": settings.REST_FRAMEWORK["NUM_PROXIES"],
    "THROTTLE_RATES": settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
    "MIDDLEWARE": settings.MIDDLEWARE,
    "DEFAULT_STORAGE": settings.STORAGES["default"]["BACKEND"],
    "STATIC_STORAGE": settings.STORAGES["staticfiles"]["BACKEND"],
}))
"""
    return subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )


def test_production_settings_apply_security_contract():
    result = _load_production_settings()

    assert result.returncode == 0, result.stderr
    configured = json.loads(result.stdout)
    assert configured == {
        "DEBUG": False,
        "ALLOWED_HOSTS": ["api.example.com", ".internal.example.com"],
        "CSRF_TRUSTED_ORIGINS": ["https://admin.example.com"],
        "CORS_ALLOWED_ORIGINS": ["https://shop.example.com"],
        "CORS_ALLOW_CREDENTIALS": False,
        "CORS_URLS_REGEX": "^/api/.*$",
        "CORS_ALLOW_HEADERS": [
            "accept",
            "authorization",
            "content-type",
            "user-agent",
            "x-cart-token",
            "x-csrftoken",
            "x-requested-with",
        ],
        "SECURE_SSL_REDIRECT": True,
        "SECURE_REDIRECT_EXEMPT": ["^api/v1/health/$"],
        "SECURE_HSTS_SECONDS": 3600,
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": False,
        "SECURE_HSTS_PRELOAD": False,
        "SESSION_COOKIE_SECURE": True,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "CSRF_COOKIE_SECURE": True,
        "CSRF_COOKIE_HTTPONLY": True,
        "CSRF_COOKIE_SAMESITE": "Lax",
        "SECURE_PROXY_SSL_HEADER": None,
        "DJANGO_LOG_LEVEL": "WARNING",
        "APP_LOG_LEVEL": "INFO",
        "DB_CONN_MAX_AGE": 60,
        "DB_CONN_HEALTH_CHECKS": True,
        "THROTTLE_NUM_PROXIES": 0,
        "THROTTLE_RATES": {
            "auth_register": "5/hour",
            "auth_login": "10/minute",
            "auth_refresh": "30/minute",
            "cart_mutation": "60/minute",
            "checkout": "10/minute",
            "payment_initiate": "10/minute",
            "payment_verify": "20/minute",
            "bale_webhook": "300/minute",
            "review_mutation": "10/hour",
        },
        "MIDDLEWARE": [
            "django.middleware.security.SecurityMiddleware",
            "whitenoise.middleware.WhiteNoiseMiddleware",
            "apps.common.admin_locale.AdminPersianLocaleMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "corsheaders.middleware.CorsMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
        ],
        "DEFAULT_STORAGE": "django.core.files.storage.FileSystemStorage",
        "STATIC_STORAGE": ("whitenoise.storage.CompressedManifestStaticFilesStorage"),
    }


@pytest.mark.parametrize(
    ("overrides", "invalid_variable"),
    [
        ({"DJANGO_SECRET_KEY": "replace-this-with-a-secret"}, "DJANGO_SECRET_KEY"),
        (
            {"DJANGO_JWT_SIGNING_KEY": PRODUCTION_ENV["DJANGO_SECRET_KEY"]},
            "DJANGO_JWT_SIGNING_KEY",
        ),
        ({"DJANGO_ALLOWED_HOSTS": ""}, "DJANGO_ALLOWED_HOSTS"),
        ({"DJANGO_ALLOWED_HOSTS": "*"}, "DJANGO_ALLOWED_HOSTS"),
        (
            {"DATABASE_URL": "postgresql://ecommerce:ecommerce@db:5432/ecommerce"},
            "DATABASE_URL",
        ),
        ({"DATABASE_URL": "not-a-database-url"}, "DATABASE_URL"),
        ({"DATABASE_URL": "sqlite:///tmp/production.sqlite3"}, "DATABASE_URL"),
        (
            {"DJANGO_CSRF_TRUSTED_ORIGINS": "http://admin.example.com"},
            "DJANGO_CSRF_TRUSTED_ORIGINS",
        ),
        (
            {"DJANGO_CORS_ALLOWED_ORIGINS": "https://shop.example.com/path"},
            "DJANGO_CORS_ALLOWED_ORIGINS",
        ),
        ({"DJANGO_SECURE_HSTS_SECONDS": "0"}, "DJANGO_SECURE_HSTS_SECONDS"),
        ({"DJANGO_SECURE_HSTS_PRELOAD": "True"}, "DJANGO_SECURE_HSTS_PRELOAD"),
        ({"DJANGO_LOG_LEVEL": "DEBUG"}, "DJANGO_LOG_LEVEL"),
        ({"DJANGO_DB_CONN_MAX_AGE": "-1"}, "DJANGO_DB_CONN_MAX_AGE"),
        ({"DJANGO_THROTTLE_NUM_PROXIES": "-1"}, "DJANGO_THROTTLE_NUM_PROXIES"),
        (
            {"DJANGO_THROTTLE_AUTH_LOGIN_RATE": "unlimited"},
            "DJANGO_THROTTLE_AUTH_LOGIN_RATE",
        ),
    ],
)
def test_production_settings_reject_unsafe_configuration(overrides, invalid_variable):
    result = _load_production_settings(overrides)

    assert result.returncode != 0
    assert invalid_variable in result.stderr
    if invalid_variable in {
        "DJANGO_SECRET_KEY",
        "DJANGO_JWT_SIGNING_KEY",
        "DATABASE_URL",
    }:
        assert next(iter(overrides.values())) not in result.stderr
