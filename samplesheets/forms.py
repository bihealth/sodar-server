"""Forms for the samplesheets app"""

import json
import os
import re
import tempfile

from cookiecutter.main import cookiecutter

from django import forms
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api

from samplesheets.constants import HIDDEN_SHEET_TEMPLATE_FIELDS
from samplesheets.io import SampleSheetIO, ARCHIVE_TYPES
from samplesheets.utils import clean_sheet_dir_name
from samplesheets.models import (
    Investigation,
    Assay,
    Study,
    ISATab,
    IrodsAccessTicket,
    IrodsDataRequest,
)


# Local constants
ERROR_MSG_INVALID_PATH = 'Not a valid iRODS path for this project'
ERROR_MSG_EXISTING = 'An active request already exists for this path'


class SheetImportForm(forms.Form):
    """
    Form for importing an ISA investigation from an ISA-Tab archive or
    directory.
    """

    file_upload = forms.FileField(
        allow_empty_file=False,
        help_text='Zip archive or ISA-Tab files for a single investigation',
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
                        'Only a Zip archive or ISA-Tab .txt files allowed',
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
        if self.isa_zip:  # Zip archive
            isa_data = self.sheet_io.get_isa_from_zip(self.isa_zip)
        else:  # Multi-file
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
        return self.sheet_io.import_isa(
            isa_data=isa_data,
            project=self.project,
            archive_name=self.isa_zip.filename if self.isa_zip else None,
            user=self.current_user,
            replace=self.replace,
            replace_uuid=replace_uuid,
        )


class SheetTemplateCreateForm(forms.Form):
    """Form for creating sample sheets from an ISA-Tab template."""

    def __init__(
        self, project=None, sheet_tpl=None, current_user=None, *args, **kwargs
    ):
        """Override form initialization"""
        super().__init__(*args, **kwargs)
        self.sheet_io = SampleSheetIO(
            allow_critical=settings.SHEETS_ALLOW_CRITICAL
        )
        self.project = project
        self.current_user = current_user
        self.sheet_tpl = sheet_tpl
        self.json_fields = []
        self.fields['i_dir_name'] = forms.CharField(
            label='Directory Name',
            help_text='Investigation directory name and assay prefix',
        )
        self.initial['i_dir_name'] = clean_sheet_dir_name(project.title)

        for k, v in sheet_tpl.configuration.items():
            # Skip fields generated by cookiecutter
            if isinstance(v, str) and ('{{' in v or '{%' in v):
                continue
            field_kwargs = {'label': k}
            if isinstance(v, str):
                if not v:  # Allow empty value if default is not set
                    field_kwargs = {'required': False}
                self.fields[k] = forms.CharField(**field_kwargs)
                self.initial[k] = v
            elif isinstance(v, list):
                field_kwargs['choices'] = [(x, x) for x in v]
                if not all(v):  # Allow empty value if in options
                    field_kwargs = {'required': False}
                self.fields[k] = forms.ChoiceField(**field_kwargs)
            elif isinstance(v, dict):
                field_kwargs['widget'] = forms.Textarea(
                    {'class': 'sodar-json-input'}
                )
                self.fields[k] = forms.CharField(**field_kwargs)
                self.initial[k] = json.dumps(v)
                self.json_fields.append(k)
            # Hide fields not intended to be edited (see issue #1443)
            if k in HIDDEN_SHEET_TEMPLATE_FIELDS:
                self.fields[k].widget = forms.widgets.HiddenInput()

    @classmethod
    def _get_tsv_data(cls, path, file_names):
        ret = {}
        for n in file_names:
            with open(os.path.join(path, n)) as f:
                ret[n] = {'path': n, 'tsv': f.read()}
        return ret

    def clean(self):
        # Force regex for dir name
        self.cleaned_data['i_dir_name'] = clean_sheet_dir_name(
            self.cleaned_data['i_dir_name']
        )

        # Validate JSON
        for k in self.json_fields:
            if not isinstance(self.cleaned_data[k], dict):
                try:
                    json.loads(self.cleaned_data[k])
                except Exception as ex:
                    self.add_error(k, 'Invalid JSON: {}'.format(ex))

        return self.cleaned_data

    def save(self):
        extra_context = {
            k: v for k, v in self.cleaned_data.items() if k != 'i_dir_name'
        }
        for k in self.json_fields:
            if not isinstance(extra_context[k], dict):
                extra_context[k] = json.loads(extra_context[k])
        tpl_dir_name = self.cleaned_data['i_dir_name']
        extra_context['i_dir_name'] = tpl_dir_name
        if 'is_triplet' in self.sheet_tpl.configuration:
            extra_context['is_triplet'] = self.sheet_tpl.configuration[
                'is_triplet'
            ]

        with tempfile.TemporaryDirectory() as td:
            cookiecutter(
                template=self.sheet_tpl.path,
                extra_context=extra_context,
                output_dir=td,
                no_input=True,
            )

            isa_data = {
                'investigation': {},
                'studies': {},
                'assays': {},
            }
            path = os.path.join(td, tpl_dir_name)
            i_name = [n for n in os.listdir(path) if n.startswith('i_')][0]
            i_path = os.path.join(path, i_name)

            with open(i_path) as f:
                isa_data['investigation'] = {
                    'path': '{}/{}'.format(tpl_dir_name, i_name),
                    'tsv': f.read(),
                }
            isa_data['studies'] = self._get_tsv_data(
                path, [n for n in os.listdir(path) if n.startswith('s_')]
            )
            isa_data['assays'] = self._get_tsv_data(
                path, [n for n in os.listdir(path) if n.startswith('a_')]
            )
            return self.sheet_io.import_isa(
                isa_data=isa_data,
                project=self.project,
                archive_name=None,
                user=self.current_user,
            )


class IrodsAccessTicketForm(forms.ModelForm):
    """Form for the irods access ticket creation and editing."""

    class Meta:
        model = IrodsAccessTicket
        fields = ('path', 'label', 'date_expires')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from samplesheets.views import TRACK_HUBS_COLL

        # Add selection to path field
        irods_backend = get_backend_api('omics_irods')
        assays = Assay.objects.filter(
            study__investigation__project=kwargs['initial']['project']
        )
        if irods_backend:
            choices = [
                (
                    track_hub.path,
                    "{} / {}".format(assay.get_display_name(), track_hub.name),
                )
                for assay in assays
                for track_hub in irods_backend.get_child_colls_by_path(
                    irods_backend.get_path(assay) + '/' + TRACK_HUBS_COLL
                )
            ]
        else:
            choices = []

        # Hide path in update or make it a dropdown with available track hubs
        # on creation
        if self.instance.path:
            self.fields['path'].widget = forms.widgets.HiddenInput()
        else:
            self.fields['path'].widget = forms.widgets.Select(choices=choices)

        # Add date input widget to expiry date field
        self.fields['date_expires'].label = 'Expiry date'
        self.fields['date_expires'].widget = forms.widgets.DateInput(
            attrs={'type': 'date'}, format='%Y-%m-%d'
        )

    def clean(self):
        cleaned_data = super().clean()

        # Check if expiry date is in the past
        if (
            cleaned_data.get('date_expires')
            and cleaned_data.get('date_expires') <= timezone.now()
        ):
            self.add_error(
                'date_expires', 'Expiry date should not lie in the past'
            )

        match = re.search(
            r'/assay_([0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12})/',
            cleaned_data['path'],
        )
        if not match:
            self.add_error('path', 'No valid TrackHubs path')
        else:
            try:
                cleaned_data['assay'] = Assay.objects.get(
                    sodar_uuid=match.group(1)
                )
            except ObjectDoesNotExist:
                self.add_error('path', 'Assay not found')

        return cleaned_data


class IrodsRequestForm(forms.ModelForm):
    """Form for the iRODS delete request creation and editing"""

    class Meta:
        model = IrodsDataRequest
        fields = ['path', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False

    def clean(self):
        cleaned_data = super().clean()
        irods_backend = get_backend_api('omics_irods')
        # Remove trailing slashes as irodspython client does not recognize
        # this as a collection
        cleaned_data['path'] = cleaned_data['path'].rstrip('/')

        old_request = IrodsDataRequest.objects.filter(
            path=cleaned_data['path'], status__in=['ACTIVE', 'FAILED']
        ).first()
        if old_request and old_request != self.instance:
            self.add_error('path', ERROR_MSG_EXISTING)
            return cleaned_data

        path_re = re.compile(
            '^' + irods_backend.get_projects_path() + '/[0-9a-f]{2}/'
            '(?P<project_uuid>[0-9a-f-]{36})/'
            + settings.IRODS_SAMPLE_COLL
            + '/study_(?P<study_uuid>[0-9a-f-]{36})/'
            'assay_(?P<assay_uuid>[0-9a-f-]{36})/.+$'
        )
        match = re.search(
            path_re,
            cleaned_data['path'],
        )
        if not match:
            self.add_error('path', ERROR_MSG_INVALID_PATH)
        else:
            try:
                cleaned_data['project'] = Project.objects.get(
                    sodar_uuid=match.group('project_uuid')
                )
            except Project.DoesNotExist:
                self.add_error('path', 'Project not found')

            try:
                Study.objects.get(
                    sodar_uuid=match.group('study_uuid'),
                    investigation__project__sodar_uuid=match.group(
                        'project_uuid'
                    ),
                )
            except Study.DoesNotExist:
                self.add_error('path', 'Study not found in project with UUID')

            try:
                Assay.objects.get(
                    sodar_uuid=match.group('assay_uuid'),
                    study__sodar_uuid=match.group('study_uuid'),
                )
            except Assay.DoesNotExist:
                self.add_error(
                    'path', 'Assay not found in this project with UUID'
                )

        irods_session = irods_backend.get_session()
        if 'path' in cleaned_data and not (
            irods_session.data_objects.exists(cleaned_data['path'])
            or irods_session.collections.exists(cleaned_data['path'])
        ):
            self.add_error(
                'path',
                'Path to collection or data object doesn\'t exist in iRODS',
            )

        return cleaned_data


class IrodsRequestAcceptForm(forms.Form):
    """Form accepting an iRODS delete request."""

    confirm = forms.BooleanField(
        label='I accept the iRODS delete request',
        required=True,
    )


class SheetVersionEditForm(forms.ModelForm):
    """Form for editing a saved ISA-Tab version of the sample sheets."""

    class Meta:
        model = ISATab
        fields = ['description']
