"""URL patterns for maintenance."""

from django.urls import path

from . import views

app_name = "maintenance"

urlpatterns = [
    path("", views.index, name="index"),
    path("reports/", views.my_reports, name="my_reports"),
    path("reports/<int:report_id>/", views.report_detail,
         name="report_detail"),
    path("reports/new/", views.report_where, name="report_where"),
    path("reports/new/what/", views.report_what, name="report_what"),
    path("reports/new/describe/", views.report_describe,
         name="report_describe"),
    path("queue/", views.staff_queue, name="staff_queue"),
    path("queue/<int:report_id>/assign/", views.assign_to_me,
         name="assign_to_me"),
    path("queue/<int:report_id>/status/", views.change_status,
         name="change_status"),
    path("queue/<int:report_id>/comment/", views.add_comment,
         name="add_comment"),
    path("queue/<int:report_id>/priority/", views.change_priority,
         name="change_priority"),
    path("reports/<int:report_id>/corroborate/", views.corroborate,
         name="corroborate"),
    path("reports/new/existing/", views.report_existing,
         name="report_existing"),
    path("reports/<int:report_id>/confirm/", views.confirm_fixed,
         name="confirm_fixed"),
    path("reports/<int:report_id>/reopen/", views.reopen,
         name="reopen"),
]
