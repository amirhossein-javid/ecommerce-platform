import pytest
from django.test import Client, override_settings
from django.urls import reverse


@override_settings(DEBUG=True)
def test_bale_smoke_page_uses_official_sdk_and_passes_identifier_unchanged():
    response = Client().get(reverse("payments:bale-smoke"))
    content = response.content.decode()

    assert response.status_code == 200
    assert '<script src="https://tapi.bale.ai/miniapp.js"></script>' in content
    assert "const invoiceIdentifier = input.value;" in content
    assert "Bale.WebApp.openInvoice(invoiceIdentifier" in content
    assert {"paid", "cancelled", "failed", "pending"} <= set(content.split('"'))
    assert "X-Frame-Options" not in response


@override_settings(DEBUG=False)
def test_bale_smoke_page_is_not_accessible_in_production():
    response = Client().get(reverse("payments:bale-smoke"))

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("bot_token", "provider_token"),
    [
        ("123456:private-bot-token", "WALLET-TEST-private-provider-token"),
    ],
)
def test_bale_smoke_page_does_not_render_credentials(bot_token, provider_token):
    with override_settings(
        DEBUG=True,
        BALE_BOT_TOKEN=bot_token,
        BALE_PROVIDER_TOKEN=provider_token,
    ):
        content = Client().get(reverse("payments:bale-smoke")).content.decode()

    assert bot_token not in content
    assert provider_token not in content
    assert "BALE_BOT_TOKEN" not in content
    assert "BALE_PROVIDER_TOKEN" not in content
