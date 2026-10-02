"""Settings for local development and tests."""

import mimetypes

from .base import *  # noqa: F403
from .base import env

mimetypes.add_type("image/webp", ".webp")

DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += [  # noqa: F405
    "rest_framework.renderers.BrowsableAPIRenderer"
]
