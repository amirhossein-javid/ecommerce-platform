from ipaddress import ip_address
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

from apps.payments.bale import BaleGateway
from apps.payments.gateways import PaymentGatewayError

DOCUMENTATION_HOSTS = frozenset(("example.com", "example.net", "example.org"))
RESERVED_HOST_SUFFIXES = (".example", ".invalid", ".localhost", ".test")


def _is_forbidden_webhook_host(hostname):
    hostname = hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return True
    if hostname in DOCUMENTATION_HOSTS or any(
        hostname.endswith(f".{reserved_host}") for reserved_host in DOCUMENTATION_HOSTS
    ):
        return True
    if hostname.endswith(RESERVED_HOST_SUFFIXES):
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


class Command(BaseCommand):
    help = "Register the configured HTTPS payment webhook URL with Bale."

    def handle(self, *args, **options):
        webhook_url = settings.BALE_WEBHOOK_URL
        try:
            parsed = urlsplit(webhook_url)
            port = parsed.port
        except ValueError:
            raise CommandError(
                "BALE_WEBHOOK_URL must be the public HTTPS Bale webhook URL "
                "on port 443 or 88."
            ) from None
        hostname = parsed.hostname
        if (
            parsed.scheme != "https"
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or parsed.query
            or (port is not None and port not in (88, 443))
            or _is_forbidden_webhook_host(hostname)
            or parsed.path != reverse("payments:bale-webhook")
        ):
            raise CommandError(
                "BALE_WEBHOOK_URL must be the public HTTPS Bale webhook URL "
                "on port 443 or 88."
            )

        try:
            BaleGateway().set_webhook(webhook_url)
        except PaymentGatewayError:
            raise CommandError("Bale webhook registration failed.") from None

        self.stdout.write(self.style.SUCCESS("Bale webhook registered."))
