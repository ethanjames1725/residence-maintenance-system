from django.contrib.auth.models import User
from django.test import TestCase

from .models import (
    BedSpace,
    Building,
    Category,
    CommonArea,
    Priority,
    Report,
    StudentProfile,
    Unit,
)


class VisibilityTests(TestCase):
    """The three visibility tiers from README section 6.1."""

    def setUp(self):
        """Two buildings, one shared unit, three students, three reports."""
        self.building_a = Building.objects.create(name="Building A", code="A")
        self.building_b = Building.objects.create(name="Building B", code="B")

        # A shared unit in building A, and a unit in building B
        self.unit_43 = Unit.objects.create(building=self.building_a, number="43")
        self.unit_50 = Unit.objects.create(building=self.building_b, number="50")

        # Two flatmates in unit 43, one student in building B
        self.bed_43_1 = BedSpace.objects.create(unit=self.unit_43, label="43-1")
        self.bed_43_2 = BedSpace.objects.create(unit=self.unit_43, label="43-2")
        self.bed_50_1 = BedSpace.objects.create(unit=self.unit_50, label="50-1")

        self.alice = self.make_student("alice", self.bed_43_1)
        self.bob = self.make_student("bob", self.bed_43_2)
        self.carol = self.make_student("carol", self.bed_50_1)

        # One area at each tier
        self.kitchen_43 = CommonArea.objects.create(
            building=self.building_a, unit=self.unit_43,
            name="Kitchen", area_type="kitchen")
        self.laundry_a = CommonArea.objects.create(
            building=self.building_a, unit=None,
            name="Ground floor laundry", area_type="laundry")

        self.category = Category.objects.create(
            name="Plumbing", slug="plumbing",
            minimum_priority=Priority.LOW)

        # One report at each tier, all made by alice
        self.private_report = self.make_report(bed_space=self.bed_43_1)
        self.unit_report = self.make_report(common_area=self.kitchen_43)
        self.building_report = self.make_report(common_area=self.laundry_a)

    def make_student(self, username, bed_space):
        """Create a user with a profile on the given bed space."""
        user = User.objects.create_user(username=username, password="testpass123")
        StudentProfile.objects.create(user=user, bed_space=bed_space)
        return user

    def make_report(self, bed_space=None, common_area=None):
        """Create a report by alice at the given location."""
        return Report.objects.create(
            reporter=self.alice,
            bed_space=bed_space,
            common_area=common_area,
            category=self.category,
            description="Something is broken.",
            derived_priority=Priority.LOW,
            current_priority=Priority.LOW,
        )

    def test_student_sees_own_bed_space_report(self):
        visible = Report.objects.visible_to(self.alice)
        self.assertIn(self.private_report, visible)

    def test_flatmate_cannot_see_bed_space_report(self):
        """Tier 1 does not extend to others in the same unit."""
        visible = Report.objects.visible_to(self.bob)
        self.assertNotIn(self.private_report, visible)

    def test_flatmate_sees_unit_common_area_report(self):
        visible = Report.objects.visible_to(self.bob)
        self.assertIn(self.unit_report, visible)

    def test_other_building_cannot_see_unit_report(self):
        visible = Report.objects.visible_to(self.carol)
        self.assertNotIn(self.unit_report, visible)

    def test_resident_sees_building_common_area_report(self):
        visible = Report.objects.visible_to(self.bob)
        self.assertIn(self.building_report, visible)

    def test_other_building_cannot_see_building_report(self):
        """Carol is in building B, the laundry is in building A."""
        visible = Report.objects.visible_to(self.carol)
        self.assertNotIn(self.building_report, visible)

    def test_staff_see_everything(self):
        staff = User.objects.create_user(
            username="tech", password="testpass123", is_staff=True)
        visible = Report.objects.visible_to(staff)
        self.assertEqual(visible.count(), 3)
