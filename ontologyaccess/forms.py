"""Forms for the ontologyaccess app"""

import fastobo

# import logging

from django import forms

# from django.conf import settings

from ontologyaccess.io import OBOFormatOntologyIO
from ontologyaccess.models import (
    OBOFormatOntology,
    DEFAULT_TERM_URL,
)


class OBOFormatOntologyForm(forms.ModelForm):
    """Form for importing an OBO ontology in the SODAR database"""

    #: OBO ontology document parsed by fastobo
    obo_doc = None

    #: Field for file upload
    file_upload = forms.FileField(
        allow_empty_file=False, help_text='OBO format file',
    )

    class Meta:
        model = OBOFormatOntology
        fields = ['file_upload', 'title', 'term_url']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Creation modifications
        if not self.instance.pk:
            self.initial['term_url'] = DEFAULT_TERM_URL

        # Update modifications
        else:
            self.fields['file_upload'].widget = forms.HiddenInput()
            self.fields['file_upload'].required = False

    def clean(self):
        if self.cleaned_data.get('file_upload'):
            try:
                file_data = self.files.get('file_upload').read().decode()
                self.obo_doc = fastobo.loads(file_data)

            except Exception as ex:
                # NOTE: Can't bind to FileField
                self.add_error(None, 'Fastobo exception: {}'.format(ex))

        # TODO: Validate term_url
        return self.cleaned_data

    def save(self, *args, **kwargs):
        if not self.instance.pk and self.cleaned_data.get('file_upload'):
            obo_io = OBOFormatOntologyIO()
            self.instance = obo_io.import_obo(
                obo_doc=self.obo_doc,
                file_name=self.cleaned_data.get('file_upload'),
                title=self.cleaned_data.get('title'),
                term_url=self.cleaned_data.get('term_url'),
            )

        if self.instance.pk:
            if self.cleaned_data.get('title'):
                self.instance.title = self.cleaned_data['title']
            self.instance.term_url = self.cleaned_data.get('term_url')
            self.instance.save()

        return self.instance
