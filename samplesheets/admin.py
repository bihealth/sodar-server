from django.contrib import admin

from .models import (
    Investigation,
    Study,
    Assay,
    GenericMaterial,
    Protocol,
    Process,
)


admin.site.register(Investigation)
admin.site.register(Study)
admin.site.register(Assay)
admin.site.register(GenericMaterial)
admin.site.register(Protocol)
admin.site.register(Process)
