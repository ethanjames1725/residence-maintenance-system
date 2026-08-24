"""URL patterns for maintenance."""

from django.urls import path

from . import views

app_name = "maintenance"

urlpatterns = [
    path("", views.index, name="index"),
    path("reports/", views.my_reports, name="my_reports"),
    path("reports/<int:report_id>/", views.report_detail,
         name="report_detail"),
]
