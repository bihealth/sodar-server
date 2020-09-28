from django.contrib import admin

from ontologyaccess.models import OBOFormatOntology, OBOFormatOntologyTerm


admin.site.register(OBOFormatOntology)
admin.site.register(OBOFormatOntologyTerm)
