from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.payments.bale import BaleGateway
from apps.payments.gateways import PaymentGatewayError


class Command(BaseCommand):
    help = "Register the configured HTTPS payment webhook URL with Bale."

    def handle(self, *args, **options):
        webhook_url = settings.BALE_WEBHOOK_URL
        parsed = urlsplit(webhook_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise CommandError("BALE_WEBHOOK_URL must be a valid HTTPS URL.")

        try:
            BaleGateway().set_webhook(webhook_url)
        except PaymentGatewayError:
            raise CommandError("Bale webhook registration failed.") from None

        self.stdout.write(self.style.SUCCESS("Bale webhook registered."))
