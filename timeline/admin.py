from django.contrib import admin

from .models import ProjectEvent, ProjectEventObjectRef, ProjectEventStatus


admin.site.register(ProjectEvent)
admin.site.register(ProjectEventObjectRef)
admin.site.register(ProjectEventStatus)
