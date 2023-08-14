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
from projectroles.forms import MultipleFileField
from projectroles.models import Project
from projectroles.plugins import get_backend_api

from samplesheets.io import SampleSheetIO, ARCHIVE_TYPES
from samplesheets.utils import clean_sheet_dir_name
from samplesheets.models import (
    Investigation,
    Assay,
    Study,
    ISATab,
    IrodsAccessTicket,
    IrodsDataRequest,
    IRODS_REQUEST_STATUS_ACTIVE,
    IRODS_REQUEST_STATUS_FAILED,
)


# Local constants
ERROR_MSG_INVALID_PATH = 'Not a valid iRODS path for this project'
ERROR_MSG_EXISTING = 'An active request already exists for this path'
TPL_DIR_FIELD = '__output_dir'
TPL_DIR_LABEL = 'Output directory'


# Mixins and Helpers -----------------------------------------------------------


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class IrodsAccessTicketValidateMixin:
    """Validation helpers for iRODS access tickets"""

    def validate_data(self, irods_backend, project, instance, data):
        """
        Validate iRODS access ticket.

        :param irods_backend: IrodsAPI object
        :param project: Project object
        :param instance: IrodsAccessTicket object (None if creating)
        :param data: Dict of data to validate
        :return: Dict of errors in form field-error (empty if no errors)
        """
        # Validate path (only if creating)
        if not instance or not instance.pk:
            try:
                data['path'] = irods_backend.sanitize_path(data['path'])
            except Exception as ex:
                return {'path': 'Invalid iRODS path: {}'.format(ex)}
            # Ensure path is within project
            if not data['path'].startswith(irods_backend.get_path(project)):
                return {'path': 'Path is not within the project'}
            # Ensure path is a collection
            with irods_backend.get_session() as irods:
                if not irods.collections.exists(data['path']):
                    return {
                        'path': 'Path does not point to a collection '
                        'or the collection doesn\'t exist'
                    }
            # Ensure path is within a project assay
            match = re.search(
                r'/assay_([0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12})',
                data['path'],
            )
            if not match:
                return {'path': 'Not a valid assay path'}
            else:
                try:
                    # Set assay if successful
                    data['assay'] = Assay.objects.get(
                        study__investigation__project=project,
                        sodar_uuid=match.group(1),
                    )
                except ObjectDoesNotExist:
                    return {'path': 'Assay not found in project'}
            # Ensure path is not assay root
            if data['path'] == irods_backend.get_path(data['assay']):
                return {
                    'path': 'Ticket creation for assay root path is not allowed'
                }

        # Check if expiry date is in the past
        if (
            data.get('date_expires')
            and data.get('date_expires') <= timezone.now()
        ):
            return {'date_expires': 'Expiry date in the past not allowed'}

        # Check if unexpired ticket already exists for path
        if (
            not instance.pk
            and IrodsAccessTicket.objects.filter(path=data['path']).first()
        ):
            return {'path': 'Ticket already exists for this path'}
        return None


class IrodsDataRequestValidateMixin:
    """Validation helpers for iRODS data requests"""

    def validate_request_path(self, irods_backend, project, instance, path):
        """
        Validate path for IrodsAccessRequest.

        :param irods_backend: IrodsAPI object
        :param project: Project object
        :param instance: Existing instance in case of update or None
        :param path: Full iRODS path to a collection or a data object (string)
        :raises: ValueError if path is incorrect
        """
        old_request = IrodsDataRequest.objects.filter(
            path=path,
            status__in=[
                IRODS_REQUEST_STATUS_ACTIVE,
                IRODS_REQUEST_STATUS_FAILED,
            ],
        ).first()
        if old_request and old_request != instance:
            raise ValueError(ERROR_MSG_EXISTING)

        path_re = re.compile(
            '^' + irods_backend.get_projects_path() + '/[0-9a-f]{2}/'
            '(?P<project_uuid>[0-9a-f-]{36})/'
            + settings.IRODS_SAMPLE_COLL
            + '/study_(?P<study_uuid>[0-9a-f-]{36})/'
            'assay_(?P<assay_uuid>[0-9a-f-]{36})/.+$'
        )
        match = re.search(path_re, path)
        if not match:
            raise ValueError(ERROR_MSG_INVALID_PATH)

        project_path = irods_backend.get_path(project)
        if not path.startswith(project_path):
            raise ValueError('Path does not belong in project')

        try:
            Study.objects.get(
                sodar_uuid=match.group('study_uuid'),
                investigation__project__sodar_uuid=match.group('project_uuid'),
            )
        except Study.DoesNotExist:
            raise ValueError('Study not found in project with UUID')
        try:
            Assay.objects.get(
                sodar_uuid=match.group('assay_uuid'),
                study__sodar_uuid=match.group('study_uuid'),
            )
        except Assay.DoesNotExist:
            raise ValueError('Assay not found in this project with UUID')

        with irods_backend.get_session() as irods:
            if path and not (
                irods.data_objects.exists(path)
                or irods.collections.exists(path)
            ):
                raise ValueError(
                    'Path to collection or data object doesn\'t exist in iRODS',
                )


# Forms ------------------------------------------------------------------------


class SheetImportForm(forms.Form):
    """
    Form for importing an ISA investigation from an ISA-Tab archive or
    directory.
    """

    file_upload = MultipleFileField(
        allow_empty_file=False,
        help_text='Zip archive or ISA-Tab files for a single investigation',
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
            file = self.cleaned_data.get('file_upload')[0]
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
    """Form for creating sample sheets from an ISA-Tab template"""

    @classmethod
    def _get_tsv_data(cls, path, file_names):
        ret = {}
        for n in file_names:
            with open(os.path.join(path, n)) as f:
                ret[n] = {'path': n, 'tsv': f.read()}
        return ret

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
        prompts = sheet_tpl.configuration.get('__prompts__')

        for k, v in sheet_tpl.configuration.items():
            # Skip fields generated by cookiecutter
            if isinstance(v, str) and ('{{' in v or '{%' in v):
                continue
            # Get label
            if k == TPL_DIR_FIELD:
                label = TPL_DIR_LABEL
            elif prompts and k in prompts:
                label = prompts[k]
            else:
                label = k
            field_kwargs = {'label': label}
            # Set field and initial value
            if k == TPL_DIR_FIELD:
                field_kwargs[
                    'help_text'
                ] = 'Investigation directory and assay prefix'
                self.fields[k] = forms.CharField(**field_kwargs)
                self.initial[k] = clean_sheet_dir_name(project.title)
            elif isinstance(v, str):
                if not v:  # Allow empty value if default is not set
                    field_kwargs['required'] = False
                self.fields[k] = forms.CharField(**field_kwargs)
                self.initial[k] = v
            elif isinstance(v, list):
                field_kwargs['choices'] = [(x, x) for x in v]
                if not all(v):  # Allow empty value if in options
                    field_kwargs['required'] = False
                self.fields[k] = forms.ChoiceField(**field_kwargs)
            elif isinstance(v, dict):
                field_kwargs['widget'] = forms.Textarea(
                    {'class': 'sodar-json-input'}
                )
                self.fields[k] = forms.CharField(**field_kwargs)
                self.initial[k] = json.dumps(v)
                self.json_fields.append(k)
            # Hide fields not intended to be edited (see #1733)
            if k.startswith('_') and k != TPL_DIR_FIELD:
                self.fields[k].widget = forms.widgets.HiddenInput()

    def clean(self):
        # Do not allow creating multiple investigations
        inv = Investigation.objects.filter(project=self.project).first()
        if inv:
            self.add_error(None, 'Sample sheets already exist in project')
            return self.cleaned_data
        # Force regex for dir name
        self.cleaned_data[TPL_DIR_FIELD] = clean_sheet_dir_name(
            self.cleaned_data[TPL_DIR_FIELD]
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
        extra_context = {k: v for k, v in self.cleaned_data.items()}
        for k in self.json_fields:
            if not isinstance(extra_context[k], dict):
                extra_context[k] = json.loads(extra_context[k])
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
            tpl_dir_name = self.cleaned_data[TPL_DIR_FIELD]
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
                from_template=True,
            )


class IrodsAccessTicketForm(IrodsAccessTicketValidateMixin, forms.ModelForm):
    """Form for the irods access ticket creation and editing"""

    class Meta:
        model = IrodsAccessTicket
        fields = ('path', 'label', 'date_expires')

    def __init__(self, project=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.project = self.instance.get_project()
        else:
            self.project = project
        # Update path help and hide in update
        path_help = 'Full path to iRODS collection within an assay'
        self.fields['path'].help_text = path_help
        if self.instance.path:
            self.fields['path'].widget = forms.widgets.HiddenInput()
            self.fields['path'].required = False
        # Add date input widget to expiry date field
        self.fields['date_expires'].label = 'Expiry date'
        self.fields['date_expires'].widget = forms.widgets.DateInput(
            attrs={'type': 'date'}, format='%Y-%m-%d'
        )

    def clean(self):
        cleaned_data = super().clean()
        irods_backend = get_backend_api('omics_irods')
        cleaned_data['path'] = irods_backend.sanitize_path(cleaned_data['path'])
        errors = self.validate_data(
            irods_backend, self.project, self.instance, cleaned_data
        )
        if errors:
            for k, v in errors.items():
                self.add_error(k, v)
        return self.cleaned_data


class IrodsDataRequestForm(IrodsDataRequestValidateMixin, forms.ModelForm):
    """Form for iRODS data request creation and editing"""

    class Meta:
        model = IrodsDataRequest
        fields = ['path', 'description']

    def __init__(self, project=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            self.project = Project.objects.filter(sodar_uuid=project).first()
        self.fields['description'].required = False

    def clean(self):
        cleaned_data = super().clean()
        irods_backend = get_backend_api('omics_irods')
        cleaned_data['path'] = irods_backend.sanitize_path(cleaned_data['path'])
        try:
            self.validate_request_path(
                irods_backend, self.project, self.instance, cleaned_data['path']
            )
        except Exception as ex:
            self.add_error('path', str(ex))
        return cleaned_data


class IrodsDataRequestAcceptForm(forms.Form):
    """Form for accepting an iRODS data request"""

    confirm = forms.BooleanField(required=True)

    def __init__(self, *args, **kwargs):
        num_requests = kwargs.pop('num_requests', None)
        super().__init__(*args, **kwargs)
        self.fields['confirm'].label = 'I accept the iRODS delete request'
        if num_requests > 1:
            self.fields['confirm'].label += 's'


class SheetVersionEditForm(forms.ModelForm):
    """Form for editing a saved ISA-Tab version of sample sheets"""

    class Meta:
        model = ISATab
        fields = ['description']
