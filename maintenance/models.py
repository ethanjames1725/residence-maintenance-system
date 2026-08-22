import secrets

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
        unique_together = ["building", "number"]

    def __str__(self):
        return f"{self.building.code}-{self.number}"


class BedSpace(models.Model):
    """One resident's private space within a unit."""
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE,
                             related_name="bed_spaces")
    label = models.CharField(max_length=20)
    claim_code = models.CharField(max_length=12, unique=True, blank=True)

    class Meta:
        unique_together = ["unit", "label"]

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

    AREA_TYPES = [
        ("kitchen", "Kitchen"),
        ("bathroom", "Bathroom"),
        ("lounge", "Lounge"),
        ("laundry", "Laundry"),
        ("gym", "Gym"),
        ("study", "Study centre"),
        ("corridor", "Corridor"),
        ("other", "Other"),
    ]

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
