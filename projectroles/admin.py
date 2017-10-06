from django.contrib import admin
from .models import Project, Role, RoleAssignment, ProjectSetting, ProjectInvite

# Register your models here.
admin.site.register(Project)
admin.site.register(Role)
admin.site.register(RoleAssignment)
admin.site.register(ProjectSetting)
admin.site.register(ProjectInvite)
