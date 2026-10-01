from django.urls import path

from .views import health_check, readiness_check

app_name = "common"

urlpatterns = [
    path("", health_check, name="health-check"),
    path("readiness/", readiness_check, name="readiness-check"),
]
