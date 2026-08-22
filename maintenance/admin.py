from django.contrib import admin

from .models import (
    BedSpace,
    Building,
    Category,
    CommonArea,
    Corroboration,
    Report,
    ReportEvent,
    StudentProfile,
    Unit,
)

admin.site.register(BedSpace)
admin.site.register(Building)
admin.site.register(Category)
admin.site.register(CommonArea)
admin.site.register(Corroboration)
admin.site.register(Report)
admin.site.register(ReportEvent)
admin.site.register(StudentProfile)
admin.site.register(Unit)
