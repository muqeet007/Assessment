from django.urls import path
from .views import health_check, route

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("api/route", route, name="route"),
]
