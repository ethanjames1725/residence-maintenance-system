from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Category,
    CommonArea,
    Priority,
    Report,
    ReportEvent,
    Status,
)
from .services import derive_priority, record_priority_change


def staff_required(view_func):
    """Restrict a view to maintenance staff."""
    return user_passes_test(
        lambda u: u.is_staff, login_url="maintenance:index")(view_func)


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
    context = {"report": report, "priorities": Priority.choices}
    return render(request, "maintenance/report_detail.html", context)


@login_required
def report_where(request):
    """Step 1 of reporting: choose a location."""
    profile = request.user.studentprofile
    unit = profile.unit

    if request.method == "POST":
        request.session["location"] = request.POST["location"]
        return redirect("maintenance:report_what")

    context = {
        "bed_space": profile.bed_space,
        "unit_areas": unit.common_areas.all(),
        "building_areas": CommonArea.objects.filter(
            building=profile.building, unit__isnull=True),
    }
    return render(request, "maintenance/report_where.html", context)


@login_required
def report_what(request):
    """Step 2 of reporting: choose a category."""
    if "location" not in request.session:
        return redirect("maintenance:report_where")

    if request.method == "POST":
        request.session["category_id"] = request.POST["category"]
        return redirect("maintenance:report_describe")

    context = {"categories": Category.objects.all()}
    return render(request, "maintenance/report_what.html", context)


@login_required
def report_describe(request):
    """Step 3 of reporting: describe the fault and answer triage."""
    if "category_id" not in request.session:
        return redirect("maintenance:report_where")

    if request.method != "POST":
        return render(request, "maintenance/report_describe.html")

    profile = request.user.studentprofile
    location = request.session["location"]

    # Resolve the location, constrained to what this student may report
    if location == "bed_space":
        bed_space = profile.bed_space
        common_area = None
    else:
        allowed = CommonArea.objects.filter(
            Q(unit=profile.unit)
            | Q(unit__isnull=True, building=profile.building)
        )
        area_id = int(location.removeprefix("area-"))
        common_area = get_object_or_404(allowed, pk=area_id)
        bed_space = None

    category = get_object_or_404(Category, pk=request.session["category_id"])

    answers = {
        "water_active": "water_active" in request.POST,
        "cannot_secure": "cannot_secure" in request.POST,
        "electrical_hazard": "electrical_hazard" in request.POST,
        "room_unusable": "room_unusable" in request.POST,
    }
    priority = derive_priority(category, answers)

    report = Report.objects.create(
        reporter=request.user,
        bed_space=bed_space,
        common_area=common_area,
        category=category,
        description=request.POST["description"],
        derived_priority=priority,
        current_priority=priority,
        **answers,
    )

    del request.session["location"]
    del request.session["category_id"]

    return redirect("maintenance:report_detail", report_id=report.id)


@staff_required
def staff_queue(request):
    """Every report, highest priority first."""
    reports = Report.objects.all()

    status = request.GET.get("status", "")
    if status:
        reports = reports.filter(status=status)

    context = {
        "reports": reports,
        "statuses": Status.choices,
        "current_status": status,
    }
    return render(request, "maintenance/staff_queue.html", context)


@staff_required
@require_POST
def assign_to_me(request, report_id):
    """Take ownership of a report."""
    report = get_object_or_404(Report, pk=report_id)

    report.assigned_to = request.user
    if report.status == Status.REPORTED:
        report.status = Status.ACKNOWLEDGED
    report.save()

    ReportEvent.objects.create(
        report=report,
        author=request.user,
        event_type=ReportEvent.EventType.STATUS_CHANGE,
        body=f"Assigned to {request.user.username}.",
        to_value=report.status,
    )
    return redirect("maintenance:report_detail", report_id=report.id)


@staff_required
@require_POST
def change_status(request, report_id):
    """Move a report through the workflow."""
    report = get_object_or_404(Report, pk=report_id)
    new_status = request.POST["status"]

    if not report.can_move_to(new_status):
        raise Http404("That status change is not allowed.")

    old_status = report.status
    report.status = new_status
    if new_status == Status.RESOLVED:
        report.resolved_at = timezone.now()
    report.save()

    ReportEvent.objects.create(
        report=report,
        author=request.user,
        event_type=ReportEvent.EventType.STATUS_CHANGE,
        body=f"Status changed to {report.get_status_display()}.",
        from_value=old_status,
        to_value=new_status,
    )
    return redirect("maintenance:report_detail", report_id=report.id)


@staff_required
@require_POST
def add_comment(request, report_id):
    """Post an update the reporter can see."""
    report = get_object_or_404(Report, pk=report_id)

    ReportEvent.objects.create(
        report=report,
        author=request.user,
        event_type=ReportEvent.EventType.COMMENT,
        body=request.POST["body"],
    )
    return redirect("maintenance:report_detail", report_id=report.id)


@staff_required
@require_POST
def change_priority(request, report_id):
    """Override a derived priority, with the change recorded."""
    report = get_object_or_404(Report, pk=report_id)
    new_priority = int(request.POST["priority"])

    if new_priority not in Priority.values:
        raise Http404("That is not a valid priority.")

    if new_priority != report.current_priority:
        record_priority_change(
            report,
            new_priority,
            author=request.user,
            event_type=ReportEvent.EventType.PRIORITY_CHANGE,
        )
    return redirect("maintenance:report_detail", report_id=report.id)
