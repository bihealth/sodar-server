from isatools import isatab
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from django import forms
from django.conf import settings

# Projectroles dependency
from projectroles.models import Project

from .models import Investigation, Study, Assay, GenericMaterial, Protocol, \
    Process
from .io import import_isa, get_inv_file_name


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
        self.isa_inv = None
        self.project = None
        self.inv_file_name = None

        if project:
            try:
                self.project = Project.objects.get(pk=project)

            except Project.DoesNotExist:
                pass

    def clean(self):
        file = self.cleaned_data.get('file_upload')

        # Ensure file type
        if file.content_type != 'application/zip':
            self.add_error('file_upload', 'The file is not a Zip archive')
            return self.cleaned_data

        # Extract zip into temporary dir
        with TemporaryDirectory() as temp_dir:
            with ZipFile(file) as zip_file:
                zip_file = ZipFile(file)

                # Get investigation file name
                self.inv_file_name = get_inv_file_name(zip_file)

                if not self.inv_file_name:
                    self.add_error(
                        'file_upload',
                        'Investigation file not found in archive')
                    return self.cleaned_data

                zip_file.extractall(temp_dir)

            # Parse ISAtab
            try:
                self.isa_inv = isatab.load(temp_dir)

            except Exception as ex:
                self.add_error(
                    'file_upload', 'ISA-API parsing failed: {}'.format(ex))

        return self.cleaned_data

    def save(self, *args, **kwargs):
        try:
            return import_isa(
                isa_inv=self.isa_inv,
                file_name=self.inv_file_name,
                project=self.project)

        except Exception as ex:
            # If investigation was partially created, delete it
            try:
                Investigation.objects.get(project=self.project).delete()

            except Investigation.DoesNotExist:
                pass

            raise Exception('Django import failed: {}'.format(ex))
