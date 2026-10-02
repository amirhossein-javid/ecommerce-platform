import pytest
from django.core.cache import cache
from rest_framework.throttling import ScopedRateThrottle


@pytest.fixture(autouse=True)
def isolate_django_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def configure_throttle_rates(monkeypatch):
    def configure(**rates):
        monkeypatch.setattr(
            ScopedRateThrottle,
            "THROTTLE_RATES",
            {**ScopedRateThrottle.THROTTLE_RATES, **rates},
        )

    return configure
