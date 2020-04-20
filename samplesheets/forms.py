from django import forms
from django.conf import settings

# Projectroles dependency
from projectroles.models import Project

from samplesheets.io import SampleSheetIO, ARCHIVE_TYPES
from samplesheets.models import Investigation


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

            try:
                self.isa_zip = self.sheet_io.get_zip_file(file)

            except OSError as ex:
                self.add_error('file_upload', str(ex))
                return self.cleaned_data

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
            isa_data = self.sheet_io.get_isa_from_files(
                self.files.getlist('file_upload')
            )

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
