import secrets

from django.contrib.auth.models import User
from django.db import models

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_claim_code():
    """Return a random 8-character code, hyphenated in the middle.

    Uses secrets rather than random so codes cannot be predicted from
    one another. The alphabet omits I, L, O, 0 and 1, which get confused
    when a code is read aloud at reception.
    """
    raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


class Priority(models.IntegerChoices):
    """Integers so that higher means more urgent.

    This lets the category floor be applied with max().
    """
    LOW = 1, "Low"
    STANDARD = 2, "Standard"
    HIGH = 3, "High"
    EMERGENCY = 4, "Emergency"


class Status(models.TextChoices):
    REPORTED = "reported", "Reported"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    IN_PROGRESS = "in_progress", "In Progress"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"
    CANCELLED = "cancelled", "Cancelled"


class Building(models.Model):
    """A residence block."""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name


class Unit(models.Model):
    """A room or flat within a building."""
    building = models.ForeignKey(Building, on_delete=models.CASCADE,
                                 related_name="units")
    number = models.CharField(max_length=10)

    class Meta:
        unique_together = ("building", "number")

    def __str__(self):
        return f"{self.building.code}-{self.number}"


class BedSpace(models.Model):
    """One resident's private space within a unit."""
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE,
                             related_name="bed_spaces")
    label = models.CharField(max_length=20)
    claim_code = models.CharField(max_length=12, unique=True, blank=True)

    class Meta:
        unique_together = ("unit", "label")

    def __str__(self):
        return f"{self.unit.building.code}-{self.label}"

    def save(self, *args, **kwargs):
        """Generate a claim code on first save, then leave it alone."""
        while not self.claim_code:
            code = generate_claim_code()
            if not BedSpace.objects.filter(claim_code=code).exists():
                self.claim_code = code
        super().save(*args, **kwargs)


class CommonArea(models.Model):
    """A shared space, belonging to one unit or to the whole building.

    A null unit means the area serves the whole building. This is what
    creates the three visibility tiers - see README section 6.1.
    """

    AREA_TYPES = (
        ("kitchen", "Kitchen"),
        ("bathroom", "Bathroom"),
        ("lounge", "Lounge"),
        ("laundry", "Laundry"),
        ("gym", "Gym"),
        ("study", "Study centre"),
        ("corridor", "Corridor"),
        ("other", "Other"),
    )

    # Always set, even for unit-level areas. Building-wide areas are the
    # ones where unit is null - filter on unit__isnull=True.
    building = models.ForeignKey(Building, on_delete=models.CASCADE,
                                 related_name="common_areas")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE,
                             related_name="common_areas",
                             null=True, blank=True)
    name = models.CharField(max_length=100)
    area_type = models.CharField(max_length=20, choices=AREA_TYPES)

    def __str__(self):
        if self.unit:
            return f"{self.unit} — {self.name}"
        return f"{self.building.code} — {self.name}"


class Category(models.Model):
    """A type of fault, carrying a minimum priority.

    The floor is stored as data rather than in code so staff can adjust
    it in the admin.
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    minimum_priority = models.IntegerField(
        choices=Priority.choices, default=Priority.LOW)

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    """Links a user account to the bed space they occupy.

    The one-to-one on bed_space enforces single occupancy at the
    database level, which is what makes a claim code single-use.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bed_space = models.OneToOneField(BedSpace, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.user.username} ({self.bed_space})"

    @property
    def unit(self):
        return self.bed_space.unit

    @property
    def building(self):
        return self.bed_space.unit.building


class Report(models.Model):
    """A maintenance fault reported by a student.

    Exactly one of bed_space or common_area is set - the location
    determines who can see the report. See README section 6.1.
    """
    reporter = models.ForeignKey(User, on_delete=models.PROTECT,
                                 related_name="reports")
    bed_space = models.ForeignKey(BedSpace, on_delete=models.PROTECT,
                                  null=True, blank=True,
                                  related_name="reports")
    common_area = models.ForeignKey(CommonArea, on_delete=models.PROTECT,
                                    null=True, blank=True,
                                    related_name="reports")
    category = models.ForeignKey(Category, on_delete=models.PROTECT,
                                 related_name="reports")
    description = models.TextField()

    # Triage answers - see README section 7.2
    water_active = models.BooleanField(default=False)
    cannot_secure = models.BooleanField(default=False)
    electrical_hazard = models.BooleanField(default=False)
    room_unusable = models.BooleanField(default=False)

    derived_priority = models.IntegerField(choices=Priority.choices)
    current_priority = models.IntegerField(choices=Priority.choices)

    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.REPORTED)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    limit_choices_to={"is_staff": True},
                                    related_name="assigned_reports")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-current_priority", "created_at")
        constraints = (
            models.CheckConstraint(
                condition=(
                    models.Q(bed_space__isnull=False,
                             common_area__isnull=True)
                    | models.Q(bed_space__isnull=True,
                               common_area__isnull=False)
                ),
                name="report_has_exactly_one_location",
            ),
        )

    def __str__(self):
        return f"#{self.pk} {self.location} ({self.get_status_display()})"

    @property
    def location(self):
        return self.bed_space or self.common_area


class ReportEvent(models.Model):
    """One entry in a report's timeline.

    Covers both the comments students see and the record of status and
    priority changes, so the detail page renders from a single query.
    """

    class EventType(models.TextChoices):
        COMMENT = "comment", "Comment"
        STATUS_CHANGE = "status_change", "Status change"
        PRIORITY_CHANGE = "priority_change", "Priority change"
        ESCALATION = "escalation", "Escalation"

    report = models.ForeignKey(Report, on_delete=models.CASCADE,
                               related_name="events")
    # Null for system-generated events such as corroboration escalation.
    author = models.ForeignKey(User, on_delete=models.SET_NULL,
                               null=True, blank=True,
                               related_name="report_events")
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    body = models.TextField(blank=True)
    from_value = models.CharField(max_length=30, blank=True)
    to_value = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.get_event_type_display()} on #{self.report_id}"


class Corroboration(models.Model):
    """A student confirming they have the same fault.

    Unique together is the database-level version of "once only" -
    see README section 6.3.
    """
    report = models.ForeignKey(Report, on_delete=models.CASCADE,
                               related_name="corroborations")
    student = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name="corroborations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("report", "student")

    def __str__(self):
        return f"{self.student.username} on #{self.report_id}"
