from django.core.management.base import BaseCommand, CommandError

from apps.payments.bale_webhooks import (
    process_bale_webhook_update,
    recoverable_bale_update_ids,
)
from apps.payments.gateways import get_payment_gateway
from apps.payments.models import BaleWebhookUpdate


class Command(BaseCommand):
    help = "Retry locally recoverable Bale payment updates."

    def handle(self, *args, **options):
        gateway = get_payment_gateway()
        if gateway.name != "bale":
            raise CommandError("The configured payment gateway is not Bale.")

        processed = 0
        pending = 0
        rejected = 0
        for update_id in recoverable_bale_update_ids():
            record = process_bale_webhook_update(
                update_id=update_id,
                gateway=gateway,
            )
            if record.status == BaleWebhookUpdate.Status.PROCESSED:
                processed += 1
            elif record.status == BaleWebhookUpdate.Status.REJECTED:
                rejected += 1
            else:
                pending += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Bale recovery complete: {processed} processed, "
                f"{pending} pending, {rejected} rejected."
            )
        )
