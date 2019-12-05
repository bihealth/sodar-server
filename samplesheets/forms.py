from zipfile import ZipFile

from django import forms
from django.conf import settings

# Projectroles dependency
from projectroles.models import Project

from samplesheets.io import SampleSheetIO
from samplesheets.models import Investigation


# Local constants
ARCHIVE_TYPES = ['application/zip', 'application/x-zip-compressed']


class SampleSheetImportForm(forms.Form):
    """Form for importing an ISA investigation from an ISAtab archive or
    directory"""

    file_upload = forms.FileField(
        allow_empty_file=False,
        help_text='Zip archive or ISAtab files for a single investigation',
        widget=forms.ClearableFileInput(attrs={'multiple': True}),
    )

    class Meta:
        fields = ['file_upload']

    def __init__(
        self, project=None, replace=False, current_user=None, *args, **kwargs
    ):
        """Override form initialization"""
        super().__init__(*args, **kwargs)
        self.isa_zip = None
        self.project = None
        self.replace = replace
        self.current_user = current_user
        self.sheet_io = SampleSheetIO(
            allow_critical=settings.SHEETS_ALLOW_CRITICAL
        )

        if project:
            self.project = Project.objects.filter(sodar_uuid=project).first()

    def clean(self):
        files = self.files.getlist('file_upload')

        # Zip archive upload
        if len(files) == 1:
            file = self.cleaned_data.get('file_upload')

            # Ensure file type
            if file and file.content_type not in ARCHIVE_TYPES:
                self.add_error('file_upload', 'The file is not a Zip archive')
                return self.cleaned_data

            # Validate zip file
            try:
                zip_file = ZipFile(file)

            except Exception as ex:
                self.add_error(
                    'file_upload', 'Unable to open zip file: {}'.format(ex)
                )
                return self.cleaned_data

            # Get investigation file path(s)
            i_paths = self.sheet_io.get_inv_paths(zip_file)

            if len(i_paths) == 0:
                self.add_error(
                    'file_upload', 'Investigation file not found in archive'
                )
                return self.cleaned_data

            elif len(i_paths) > 1:
                self.add_error(
                    'file_upload',
                    'Multiple investigation files found in archive',
                )
                return self.cleaned_data

            self.isa_zip = zip_file

        # Multi-file checkup
        else:
            inv_found = False
            study_found = False

            for file in files:
                if file.content_type in ARCHIVE_TYPES:
                    self.add_error(
                        'file_upload',
                        'You can only upload one Zip archive at a time',
                    )
                    return self.cleaned_data

                if not file.name.endswith('.txt'):
                    self.add_error(
                        'file_upload',
                        'Only a Zip archive or ISAtab .txt files allowed',
                    )
                    return self.cleaned_data

                if file.name.startswith('i_'):
                    inv_found = True

                elif file.name.startswith('s_'):
                    study_found = True

            if not inv_found:
                self.add_error(
                    'file_upload',
                    'Investigation file not found among uploaded files',
                )
                return self.cleaned_data

            if not study_found:
                self.add_error(
                    'file_upload', 'Study file not found among uploaded files'
                )
                return self.cleaned_data

        return self.cleaned_data

    def save(self, *args, **kwargs):
        # Zip archive
        if self.isa_zip:
            isa_data = self.sheet_io.get_isa_from_zip(self.isa_zip)

        # Multi-file
        else:

            isa_data = {'investigation': {}, 'studies': {}, 'assays': {}}

            for file in self.files.getlist('file_upload'):
                if file.name.startswith('i_'):
                    isa_data['investigation']['path'] = file.name
                    isa_data['investigation']['tsv'] = file.read().decode(
                        'utf-8'
                    )

                elif file.name.startswith('s_'):
                    isa_data['studies'][file.name] = {
                        'tsv': file.read().decode('utf-8')
                    }

                elif file.name.startswith('a_'):
                    isa_data['assays'][file.name] = {
                        'tsv': file.read().decode('utf-8')
                    }

        replace_uuid = None

        if self.replace:
            replace_uuid = (
                Investigation.objects.filter(project=self.project, active=True)
                .first()
                .sodar_uuid
            )

        # NOTE: May raise an exception, caught and handled in the view
        investigation = self.sheet_io.import_isa(
            isa_data=isa_data,
            project=self.project,
            archive_name=self.isa_zip.filename if self.isa_zip else None,
            user=self.current_user,
            replace=self.replace,
            replace_uuid=replace_uuid,
        )

        return investigation
