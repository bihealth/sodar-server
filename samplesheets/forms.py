from collections import OrderedDict
from isatools import isajson
import json

from django import forms
from django.conf import settings

# Projectroles dependency
from projectroles.models import Project

from .models import Investigation, Study, Assay, GenericMaterial, Protocol, \
    Process
from .utils import import_isa_json


class SampleSheetImportForm(forms.Form):
    """Form for importing an ISA investigation from an JSON file (ISAtab format
    to be done)"""

    file_upload = forms.FileField(
        allow_empty_file=False,
        help_text='ISA-Tools compatible JSON file')

    class Meta:
        fields = ['json_file']

    def __init__(self, project=None, *args, **kwargs):
        """Override form initialization"""
        super(SampleSheetImportForm, self).__init__(*args, **kwargs)
        self.isa_data = None
        self.project = None
        self.inv_file_name = None

        if project:
            try:
                self.project = Project.objects.get(pk=project)

            except Project.DoesNotExist:
                pass

    def clean(self):
        file = self.cleaned_data.get('file_upload')
        self.inv_file_name = file.name

        try:
            json_file = file.read().decode('utf8')

            self.isa_data = json.loads(
                json_file,
                object_pairs_hook=OrderedDict)

        except ValueError as ex:
            self.add_error('file_upload', 'Not a valid JSON file!')
            print(str(ex))  # DEBUG

        report = isajson.validate(self.isa_data)

        if len(report['errors']) > 0:
            self.add_error(
                'file_upload', 'JSON file failed ISA API validation!')

            # DEBUG
            print('ISA API Errors:')
            for e in report['errors']:
                print(e)

        return self.cleaned_data

    def save(self, *args, **kwargs):
        investigation = import_isa_json(
            json_data=self.isa_data,
            file_name=self.inv_file_name,
            project=self.project)

        return investigation
