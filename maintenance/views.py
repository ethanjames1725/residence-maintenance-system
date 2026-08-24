from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Report


def index(request):
    """The ResFix home page."""
    return render(request, "maintenance/index.html")


@login_required
def my_reports(request):
    """Every report this user is allowed to see."""
    reports = Report.objects.visible_to(request.user)
    context = {"reports": reports}
    return render(request, "maintenance/my_reports.html", context)


@login_required
def report_detail(request, report_id):
    """One report and its timeline."""
    report = get_object_or_404(
        Report.objects.visible_to(request.user), pk=report_id)
    context = {"report": report}
    return render(request, "maintenance/report_detail.html", context)