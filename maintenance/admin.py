from django.contrib import admin

from .models import Building, Unit, BedSpace, CommonArea

admin.site.register(Building)
admin.site.register(Unit)
admin.site.register(BedSpace)
admin.site.register(CommonArea)
