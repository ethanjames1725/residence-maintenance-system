"""Business rules that are more than a field lookup.

Kept out of views so they can be tested without going through HTTP -
see README section 18.
"""

from .models import Priority, ReportEvent, Status

ESCALATION_THRESHOLD = 5


def derive_priority(category, answers):
    """Return the priority for a new report.

    Never returns below the category minimum. See README section 7.2.
    """
    priority = Priority.STANDARD

    if answers["electrical_hazard"] or answers["cannot_secure"]:
        priority = Priority.EMERGENCY
    elif answers["water_active"] or answers["room_unusable"]:
        priority = Priority.HIGH

    return max(priority, category.minimum_priority)


def record_priority_change(report, new_priority, author, event_type):
    """Change a report's priority and write it to the timeline."""
    labels = dict(Priority.choices)
    old_priority = report.current_priority

    report.current_priority = new_priority
    report.save()

    ReportEvent.objects.create(
        report=report,
        author=author,
        event_type=event_type,
        body=f"Priority changed from {labels[old_priority]} "
             f"to {labels[new_priority]}.",
        from_value=str(old_priority),
        to_value=str(new_priority),
    )


def apply_corroboration_escalation(report):
    """Raise priority when enough residents confirm the same fault.

    Can only raise, never lower - see README section 6.3.
    """
    if report.corroborations.count() < ESCALATION_THRESHOLD:
        return
    if report.current_priority >= Priority.HIGH:
        return

    record_priority_change(
        report,
        Priority.HIGH,
        author=None,
        event_type=ReportEvent.EventType.ESCALATION,
    )
