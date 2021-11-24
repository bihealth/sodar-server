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
        allow_empty_file=False,
        help_text='OBO or OWL file (OWL will be converted to OBO)',
    )

    class Meta:
        model = OBOFormatOntology
        fields = ['file_upload', 'name', 'title', 'term_url']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obo_io = OBOFormatOntologyIO()

        # Default form modifications
        self.fields['term_url'].widget = forms.TextInput(
            attrs={'class': 'sodar-code-input'}
        )
        # Creation modifications
        if not self.instance.pk:
            self.initial['name'] = ''
            self.initial['term_url'] = DEFAULT_TERM_URL
        # Update modifications
        else:
            self.fields['file_upload'].widget = forms.HiddenInput()
            self.fields['file_upload'].required = False

    def clean(self):
        # TODO: Validate term_url
        if not self.cleaned_data.get('file_upload'):
            return self.cleaned_data

        o_format = 'obo'
        if self.cleaned_data['file_upload'].name.split('.')[-1] == 'owl':
            o_format = 'owl'
            try:
                file_data = self.obo_io.owl_to_obo(
                    self.cleaned_data['file_upload']
                )
            except Exception as ex:
                # NOTE: Can't bind to FileField
                print('DEBUG: OWL convert exception: {}'.format(ex))  # DEBUG
                self.add_error(None, 'OWL convert exception: {}'.format(ex))
                return self.cleaned_data
        else:
            file_data = self.files.get('file_upload').read().decode()

        try:
            if o_format == 'owl':
                self.obo_doc = fastobo.load(file_data)
            else:
                self.obo_doc = fastobo.loads(file_data)
        except Exception as ex:
            print('DEBUG: Fastobo exception: {}'.format(ex))  # DEBUG
            self.add_error(None, 'Fastobo exception: {}'.format(ex))

        return self.cleaned_data

    def save(self, *args, **kwargs):
        if not self.instance.pk and self.cleaned_data.get('file_upload'):
            self.instance = self.obo_io.import_obo(
                obo_doc=self.obo_doc,
                name=self.cleaned_data.get('name'),
                file=self.cleaned_data.get('file_upload'),
                title=self.cleaned_data.get('title'),
                term_url=self.cleaned_data.get('term_url'),
            )
        if self.instance.pk:
            self.instance.name = self.cleaned_data.get('name')
            if self.cleaned_data.get('title'):
                self.instance.title = self.cleaned_data['title']
            self.instance.term_url = self.cleaned_data.get('term_url')
            self.instance.save()
        return self.instance
