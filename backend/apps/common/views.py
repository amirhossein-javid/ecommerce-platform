from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(
    responses={200: {"type": "object", "properties": {"status": {"type": "string"}}}},
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health_check(request):
    """Return a lightweight liveness response without touching the database."""
    return Response({"status": "ok"})


@extend_schema(
    responses={
        200: {"type": "object", "properties": {"status": {"type": "string"}}},
        503: {"type": "object", "properties": {"status": {"type": "string"}}},
    },
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def readiness_check(request):
    """Return whether the required database dependency is available."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return Response({"status": "unavailable"}, status=503)
    return Response({"status": "ready"})
