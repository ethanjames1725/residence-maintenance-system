"""URL patterns for maintenance."""

from django.urls import path

from . import views

app_name = "maintenance"

urlpatterns = [
    path("", views.index, name="index"),
]
