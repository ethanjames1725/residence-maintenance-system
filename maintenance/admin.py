from django.contrib import admin

from .models import BedSpace, Building, CommonArea, Unit

admin.site.register(Building)
admin.site.register(Unit)
admin.site.register(BedSpace)
admin.site.register(CommonArea)
