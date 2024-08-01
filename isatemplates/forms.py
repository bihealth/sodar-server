"""Forms for the isatemplates app"""

import json
import os
import tempfile

import logging

from altamisa.isatab import (
    InvestigationReader,
    StudyReader,
    AssayReader,
    InvestigationValidator,
    StudyValidator,
    AssayValidator,
)
from cubi_isa_templates import _TEMPLATES as CUBI_TEMPLATES
from zipfile import ZipFile

from django import forms
from django.conf import settings
from django.db import transaction

# Projectroles dependency
from projectroles.forms import MultipleFileField

from isatemplates.api import ISATemplateAPI
from isatemplates.models import (
    CookiecutterISATemplate,
    CookiecutterISAFile,
    ISA_FILE_PREFIXES,
)


logger = logging.getLogger(__name__)


# Local constants
ARCHIVE_TYPES = ['application/zip', 'application/x-zip-compressed']
FILE_SKIP_MSG = 'Skipping unrecognized file in template archive: {file_name}'
NO_JSON_MSG = 'File cookiecutter.json not found'
NO_INVESTIGATION_MSG = 'Investigation file not found'
NO_STUDY_MSG = 'Study file not found'
INVALID_JSON_MSG = 'Unable to parse JSON data from cookiecutter.json'
CUBI_DESC_EXISTS_MSG = (
    'Template with identical description found in CUBI templates'
)
TPL_DIR_FIELD = '__output_dir'
TPL_DIR_VALUE = 'isa_test'


class ISATemplateForm(forms.ModelForm):
    """Form for importing and updating a custom ISA-Tab template."""

    @classmethod
    def _get_files_from_zip(cls, zip_file):
        """
        Return template files from Zip archive.

        :param zip_file: ZipFile object
        :return: Dict
        """
        ret = {'json': None, 'files': {}}
        for path in [n for n in zip_file.namelist() if not n.endswith('/')]:
            file_name = path.split('/')[-1]
            if file_name == 'cookiecutter.json':
                with zip_file.open(str(path), 'r') as f:
                    ret['json'] = f.read().decode('utf-8')
            elif file_name[:2] in ISA_FILE_PREFIXES:
                with zip_file.open(str(path), 'r') as f:
                    ret['files'][file_name] = f.read().decode('utf-8')
            else:
                logger.warning(FILE_SKIP_MSG.format(file_name=file_name))
        return ret

    @classmethod
    def _get_files_from_multi(cls, files):
        """
        Return template files from multi-file upload.

        :param files: List
        :return: Dict
        """
        ret = {'json': None, 'files': {}}
        for file in files:
            if file.name == 'cookiecutter.json':
                ret['json'] = file.read().decode('utf-8')
            elif file.name[:2] in ISA_FILE_PREFIXES:
                ret['files'][file.name] = file.read().decode('utf-8')
            else:
                logger.warning(FILE_SKIP_MSG.format(file_name=file.name))
        return ret

    def _validate_file_data(self):
        """Validate self.file data"""
        if not self.file_data['json']:
            self.add_error('file_upload', NO_JSON_MSG)
        inv_found = False
        study_found = False
        for k in self.file_data['files']:
            if k.startswith('i_'):
                inv_found = True
            elif k.startswith('s_'):
                study_found = True
        if not inv_found:
            self.add_error('file_upload', NO_INVESTIGATION_MSG)
        if not study_found:
            self.add_error('file_upload', NO_STUDY_MSG)
        try:
            json.loads(self.file_data['json'])
        except Exception:
            self.add_error('file_upload', INVALID_JSON_MSG)
            return

    @classmethod
    def _validate_isa(cls, output_dir):
        """
        Validate ISA-Tab files with default values using altamISA.

        :param output_dir: Output directory object
        """
        path = os.path.join(output_dir, TPL_DIR_VALUE)
        fl = sorted(
            [f for f in os.listdir(path)], key=lambda x: 'isa'.index(x[0])
        )
        fn = fl[0]
        with open(os.path.join(path, fn), 'r') as f:
            isa_inv = InvestigationReader.from_stream(
                input_file=f, filename=fn
            ).read()
        InvestigationValidator(isa_inv).validate()
        logger.debug('Investigation validation OK')
        i = 0
        for isa_study in isa_inv.studies:
            study_path = isa_study.info.path
            study_id = 'study{}'.format(i)
            with open(os.path.join(path, study_path), 'r') as f:
                s = StudyReader.from_stream(
                    study_id=study_id,
                    input_file=f,
                    filename=study_path,
                ).read()
            StudyValidator(isa_inv, isa_study, s).validate()
            logger.debug('Study validation OK: {}'.format(study_path))
            i += 1
            j = 0
            for isa_assay in isa_study.assays:
                assay_path = isa_assay.path
                assay_id = 'assay{}'.format(j)
                with open(os.path.join(path, assay_path), 'r') as f:
                    a = AssayReader.from_stream(
                        study_id=study_id,
                        assay_id=assay_id,
                        input_file=f,
                        filename=assay_path,
                    ).read()
                AssayValidator(isa_inv, isa_study, isa_assay, a).validate()
                logger.debug('Assay validation OK: {}'.format(assay_path))
                j += 1

    file_upload = MultipleFileField(
        allow_empty_file=False,
        help_text='Zip archive or JSON/text files for an ISA-Tab template',
    )

    class Meta:
        model = CookiecutterISATemplate
        fields = ['file_upload', 'description', 'name', 'active']

    def __init__(self, current_user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = current_user
        self.file_data = None
        self.fields['name'].required = False  # Will be auto-generated if empty
        # Update
        if self.instance.pk:
            self.fields['file_upload'].required = False

    def clean(self):
        self.cleaned_data = super().clean()
        # Validate files
        files = self.files.getlist('file_upload')
        if not self.instance.pk or files:
            if len(files) == 1:  # Zip archive upload
                file = self.cleaned_data.get('file_upload')[0]
                if file.content_type not in ARCHIVE_TYPES:
                    self.add_error(
                        'file_upload', 'The file is not a zip archive'
                    )
                    return self.cleaned_data
                try:
                    self.isa_zip = ZipFile(file)
                except Exception as ex:
                    self.add_error(
                        'file_upload',
                        'Unable to open zip archive: {}'.format(ex),
                    )
                    return self.cleaned_data
                self.file_data = self._get_files_from_zip(self.isa_zip)
            else:  # Multi-file upload
                for file in files:
                    if file.content_type in ARCHIVE_TYPES:
                        self.add_error(
                            'file_upload',
                            'You can only upload one Zip archive at a time',
                        )
                        return self.cleaned_data
                    if not file.name.endswith(
                        '.json'
                    ) and not file.name.endswith('.txt'):
                        self.add_error(
                            'file_upload',
                            'Only a Zip archive or template JSON/txt files '
                            'allowed',
                        )
                        return self.cleaned_data
                self.file_data = self._get_files_from_multi(
                    self.files.getlist('file_upload')
                )
            # Common validation on self.file_data
            self._validate_file_data()
        # Validate description
        if settings.ISATEMPLATES_ENABLE_CUBI_TEMPLATES:
            cubi_descs = [t.description.lower() for t in CUBI_TEMPLATES]
            if self.cleaned_data['description'].lower() in cubi_descs:
                self.add_error('description', CUBI_DESC_EXISTS_MSG)
        return self.cleaned_data

    @transaction.atomic
    def save(self, *args, **kwargs):
        tpl_backend = ISATemplateAPI()
        # Create template
        if not self.instance.pk:
            template = CookiecutterISATemplate.objects.create(
                name=self.cleaned_data['name'],
                description=self.cleaned_data['description'],
                configuration=self.file_data['json'],
                user=self.current_user,
            )
            logger.debug(
                'Created ISA template: {} ({})'.format(
                    template.name, template.sodar_uuid
                )
            )
        # Update template
        else:
            self.instance.name = self.cleaned_data['name']
            self.instance.description = self.cleaned_data['description']
            if self.file_data:
                self.instance.configuration = self.file_data['json']
            self.instance.user = self.current_user
            self.instance.save()
            template = self.instance
            logger.debug(
                'Updated ISA template: {} ({})'.format(
                    template.name, template.sodar_uuid
                )
            )
        # Create/update files
        if self.file_data:
            # Delete existing files in case of update
            if self.instance.pk:
                file_objs = CookiecutterISAFile.objects.filter(
                    template=template
                )
                del_count = file_objs.count()
                file_objs.delete()
                if del_count > 0:
                    logger.debug(
                        'Deleted {} existing template file{}'.format(
                            del_count, 's' if del_count != 1 else ''
                        )
                    )
            for k, v in self.file_data['files'].items():
                file = CookiecutterISAFile.objects.create(
                    template=template, file_name=k, content=v
                )
                logger.debug(
                    'Created ISA template file: {} ({})'.format(
                        k, file.sodar_uuid
                    )
                )
        # Validate template content
        if self.file_data:  # No need to validate if files haven't changed
            with tempfile.TemporaryDirectory() as output_dir:
                # Run cookiecutter on template with default values
                try:
                    tpl_backend.run_cookiecutter_custom(
                        template,
                        output_dir,
                        extra_context={TPL_DIR_FIELD: TPL_DIR_VALUE},
                    )
                except Exception as ex:
                    logger.error(
                        'Exception running cookiecutter: {}'.format(ex)
                    )
                    raise ex
                # Validate with altamISA
                try:
                    self._validate_isa(output_dir)
                except Exception as ex:
                    logger.error(
                        'Exception validating generated ISA-Tab files: '
                        '{}'.format(ex)
                    )
                    raise ex
        logger.debug('Template save OK')
        return template
