import multiprocessing
from zipfile import ZipFile

from django import forms
from django.conf import settings

# Projectroles dependency
from projectroles.models import Project

from .models import Investigation, Study, Assay, GenericMaterial, Protocol, \
    Process
from .io import import_isa, get_inv_paths


class SampleSheetImportForm(forms.Form):
    """Form for importing an ISA investigation from an ISAtab archive"""

    file_upload = forms.FileField(
        allow_empty_file=False,
        help_text='Zip archive containing ISAtab investigation files')

    class Meta:
        fields = ['file_upload']

    def __init__(self, project=None, *args, **kwargs):
        """Override form initialization"""
        super(SampleSheetImportForm, self).__init__(*args, **kwargs)
        self.isa_zip = None
        self.project = None

        if project:
            try:
                self.project = Project.objects.get(omics_uuid=project)

            except Project.DoesNotExist:
                pass

    def clean(self):
        file = self.cleaned_data.get('file_upload')

        # Ensure file type
        if file and file.content_type not in [
                'application/zip',
                'application/x-zip-compressed']:
            self.add_error('file_upload', 'The file is not a Zip archive')
            return self.cleaned_data

        # Validate zip file
        try:
            zip_file = ZipFile(file)

        except Exception as ex:
            self.add_error(
                'file_upload', 'Unable to open zip file: {}'.format(ex))
            return self.cleaned_data

        # Get investigation file path(s)
        i_paths = get_inv_paths(zip_file)

        if len(i_paths) == 0:
            self.add_error(
                'file_upload',
                'Investigation file not found in archive')
            return self.cleaned_data

        elif len(i_paths) > 1:
            self.add_error(
                'file_upload',
                'Multiple investigation files found in archive')
            return self.cleaned_data

        self.isa_zip = zip_file

        return self.cleaned_data

    def save(self, *args, **kwargs):
        try:
            return import_isa(
                isa_zip=self.isa_zip,
                project=self.project)

        except Exception as ex:
            raise Exception('Django import failed: {}'.format(ex))
