"""Tests for UI views in the isatemplates app"""

import io
import json
import os
import zipfile

from cubi_isa_templates import _TEMPLATES as CUBI_TEMPLATES

from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.models import model_to_dict
from django.test import override_settings
from django.urls import reverse
from django.utils.text import slugify

from test_plus.test import TestCase

# Timeline dependency
from timeline.models import ProjectEvent

from isatemplates.forms import (
    NO_JSON_MSG,
    NO_INVESTIGATION_MSG,
    NO_STUDY_MSG,
    INVALID_JSON_MSG,
    CUBI_DESC_EXISTS_MSG,
)
from isatemplates.models import CookiecutterISATemplate, CookiecutterISAFile
from isatemplates.tests.test_models import (
    CookiecutterISATemplateMixin,
    CookiecutterISAFileMixin,
    TEMPLATE_PATH,
    TEMPLATE_JSON_PATH,
    TEMPLATE_NAME,
    TEMPLATE_NAME_AUTO_GEN,
    TEMPLATE_DESC,
    ISA_FILE_DIR,
)


# Local constants
ARCHIVE_NAME = 'test_generic.zip'
ISA_FILE_PATH = os.path.join(
    os.path.dirname(__file__), 'templates', 'test_generic', ISA_FILE_DIR
)
ISA_FILE_NAMES = [
    'i_Investigation.txt',
    's_{{cookiecutter.s_file_name}}.txt',
    'a_{{cookiecutter.assay_prefix}}_{{cookiecutter.assay_name}}.txt',
]
TEMPLATE_NAME_UPDATE = 'updated_name'
TEMPLATE_DESC_UPDATE = 'Updated template name'
INVALID_UUID = '11111111-1111-1111-1111-111111111111'


class ISATemplateViewTestBase(
    CookiecutterISATemplateMixin, CookiecutterISAFileMixin, TestCase
):
    """Base blass for ISA template view tests"""

    @classmethod
    def get_zip(cls, path, zip_name, omit=None):
        """
        Read template files into an uploadable in-memory Zip archive.

        :param path: Path to files
        :param zip_name: Zip archive name
        :param omit: Omit files by file name (String, list or None)
        :return: SimpleUploadedFile
        """
        if not omit:
            omit = []
        elif not isinstance(omit, list):
            omit = [omit]
        zip_buffer = io.BytesIO()
        zip_file = zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_STORED)
        for dir_name, sub_dirs, file_names in os.walk(path):
            for file_name in [f for f in file_names if f not in omit]:
                file_path = os.path.join(dir_name, file_name)
                zip_file.write(str(file_path))
        zip_file.close()
        zip_buffer.seek(0)
        return SimpleUploadedFile(
            zip_name, zip_buffer.read(), content_type='application/zip'
        )

    def setUp(self):
        self.user = self.make_user('superuser')
        self.user.is_superuser = True
        self.user.save()


class TestISATemplateListView(ISATemplateViewTestBase):
    """Tests for ISATemplateListView"""

    def setUp(self):
        super().setUp()
        # Set up template
        self.template = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration='{}',
            active=True,
            user=self.user,
        )
        # Set up other variables
        self.url = reverse('isatemplates:list')

    def test_get(self):
        """Test ISATemplateListView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['templates'].count(), 1)
        self.assertEqual(
            response.context['templates'][0].sodar_uuid,
            self.template.sodar_uuid,
        )
        self.assertEqual(
            len(response.context['cubi_templates']), len(CUBI_TEMPLATES)
        )

    @override_settings(ISATEMPLATES_ENABLE_CUBI_TEMPLATES=False)
    def test_get_disable_cubi_templates(self):
        """Test GET with cubi templates disabled"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['templates'].count(), 1)
        self.assertEqual(response.context['cubi_templates'], None)


class TestISATemplateDetailView(ISATemplateViewTestBase):
    """Tests for ISATemplateDetailView"""

    def setUp(self):
        super().setUp()
        # Set up template with data
        with open(TEMPLATE_JSON_PATH, 'rb') as f:
            configuration = f.read().decode('utf-8')
        self.template = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration=configuration,
            user=self.user,
        )
        self.file_data = {}
        for fn in ISA_FILE_NAMES:
            fp = os.path.join(str(ISA_FILE_PATH), fn)
            with open(fp, 'rb') as f:
                fd = f.read().decode('utf-8')
                self.file_data[fn] = fd
                self.make_isa_file(
                    template=self.template, file_name=fn, content=fd
                )
        self.url = reverse(
            'isatemplates:detail',
            kwargs={'cookiecutterisatemplate': self.template.sodar_uuid},
        )

    def test_get(self):
        """Test ISATemplateDetailView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertEqual(context['object'], self.template)
        self.assertEqual(len(context['files']), 3)
        self.assertTrue(context['files'][0].file_name.startswith('i_'))
        self.assertEqual(
            context['files'][0].content,
            self.file_data[context['files'][0].file_name],
        )
        self.assertTrue(context['files'][1].file_name.startswith('s_'))
        self.assertEqual(
            context['files'][1].content,
            self.file_data[context['files'][1].file_name],
        )
        self.assertTrue(context['files'][2].file_name.startswith('a_'))
        self.assertEqual(
            context['files'][2].content,
            self.file_data[context['files'][2].file_name],
        )


class TestCUBIISATemplateDetailView(ISATemplateViewTestBase):
    """Tests for CUBIISATemplateDetailView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'isatemplates:detail_cubi', kwargs={'name': CUBI_TEMPLATES[0].name}
        )

    def test_get(self):
        """Test CUBIISATemplateDetailView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertEqual(context['name'], CUBI_TEMPLATES[0].name)
        self.assertEqual(
            context['description'],
            CUBI_TEMPLATES[0].description[0].upper()
            + CUBI_TEMPLATES[0].description[1:],
        )
        self.assertEqual(
            context['configuration'],
            json.dumps(CUBI_TEMPLATES[0].configuration, indent=2),
        )
        self.assertEqual(len(context['files']), 3)
        file_path = os.path.join(CUBI_TEMPLATES[0].path, ISA_FILE_DIR)
        self.assertTrue(context['files'][0]['file_name'].startswith('i_'))
        with open(
            os.path.join(file_path, context['files'][0]['file_name']), 'r'
        ) as f:
            self.assertEqual(context['files'][0]['content'], f.read())
        self.assertTrue(context['files'][1]['file_name'].startswith('s_'))
        with open(
            os.path.join(file_path, context['files'][1]['file_name']), 'r'
        ) as f:
            self.assertEqual(context['files'][1]['content'], f.read())
        self.assertTrue(context['files'][2]['file_name'].startswith('a_'))
        with open(
            os.path.join(file_path, context['files'][2]['file_name']), 'r'
        ) as f:
            self.assertEqual(context['files'][2]['content'], f.read())


class TestISATemplateCreateView(ISATemplateViewTestBase):
    """Tests for ISATemplateCreateView"""

    def setUp(self):
        super().setUp()
        self.url = reverse('isatemplates:create')

    def test_get(self):
        """Test ISATemplateCreateView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        form = response.context.get('form')
        self.assertIn('file_upload', form.fields)
        self.assertIn('description', form.fields)
        self.assertIn('name', form.fields)
        self.assertEqual(form.fields['file_upload'].required, True)

    def test_post_zip(self):
        """Test POST with Zip archive"""
        self.assertEqual(CookiecutterISATemplate.objects.count(), 0)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)
        self.assertEqual(
            ProjectEvent.objects.filter(event_name='template_create').count(), 0
        )

        data = {
            'file_upload': self.get_zip(TEMPLATE_PATH, ARCHIVE_NAME),
            'description': TEMPLATE_DESC,
            'name': TEMPLATE_NAME,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(CookiecutterISATemplate.objects.count(), 1)
        template = CookiecutterISATemplate.objects.first()
        with open(TEMPLATE_JSON_PATH, 'rb') as f:
            configuration = f.read().decode('utf-8')
        expected = {
            'id': template.pk,
            'description': TEMPLATE_DESC,
            'name': TEMPLATE_NAME,
            'configuration': configuration,
            'active': True,
            'user': self.user.pk,
            'sodar_uuid': template.sodar_uuid,
        }
        self.assertEqual(model_to_dict(template), expected)
        self.assertEqual(CookiecutterISAFile.objects.count(), 3)
        for fn in ISA_FILE_NAMES:
            file_obj = CookiecutterISAFile.objects.get(file_name=fn)
            fp = os.path.join(str(ISA_FILE_PATH), fn)
            with open(fp, 'rb') as f:
                expected = {
                    'id': file_obj.pk,
                    'template': template.pk,
                    'file_name': fn,
                    'content': f.read().decode('utf-8'),
                    'sodar_uuid': file_obj.sodar_uuid,
                }
                self.assertEqual(model_to_dict(file_obj), expected)
        self.assertEqual(
            ProjectEvent.objects.filter(event_name='template_create').count(), 1
        )

    def test_post_zip_no_json(self):
        """Test POST with zip and no cookiecutter.json file"""
        data = {
            'file_upload': self.get_zip(
                TEMPLATE_PATH, ARCHIVE_NAME, omit='cookiecutter.json'
            ),
            'description': TEMPLATE_DESC,
            'name': TEMPLATE_NAME,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['file_upload'][0], NO_JSON_MSG
        )
        self.assertEqual(CookiecutterISATemplate.objects.count(), 0)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)

    def test_post_zip_no_investigation(self):
        """Test POST with zip and no investigation file"""
        data = {
            'file_upload': self.get_zip(
                TEMPLATE_PATH, ARCHIVE_NAME, omit='i_Investigation.txt'
            ),
            'description': TEMPLATE_DESC,
            'name': TEMPLATE_NAME,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['file_upload'][0],
            NO_INVESTIGATION_MSG,
        )
        self.assertEqual(CookiecutterISATemplate.objects.count(), 0)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)

    def test_post_zip_no_study(self):
        """Test POST with zip and no study file"""
        data = {
            'file_upload': self.get_zip(
                TEMPLATE_PATH,
                ARCHIVE_NAME,
                omit='s_{{cookiecutter.s_file_name}}.txt',
            ),
            'description': TEMPLATE_DESC,
            'name': TEMPLATE_NAME,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['file_upload'][0], NO_STUDY_MSG
        )
        self.assertEqual(CookiecutterISATemplate.objects.count(), 0)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)

    def test_post_multi(self):
        """Test POST with multiple files"""
        self.assertEqual(CookiecutterISATemplate.objects.count(), 0)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)
        files = [open(TEMPLATE_JSON_PATH, 'rb')]
        for fn in ISA_FILE_NAMES:
            files.append(open(os.path.join(str(ISA_FILE_PATH), fn), 'rb'))
        data = {
            'file_upload': files,
            'description': TEMPLATE_DESC,
            'name': TEMPLATE_NAME,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CookiecutterISATemplate.objects.count(), 1)
        template = CookiecutterISATemplate.objects.first()
        with open(TEMPLATE_JSON_PATH, 'rb') as f:
            configuration = f.read().decode('utf-8')
        expected = {
            'id': template.pk,
            'description': TEMPLATE_DESC,
            'name': TEMPLATE_NAME,
            'configuration': configuration,
            'active': True,
            'user': self.user.pk,
            'sodar_uuid': template.sodar_uuid,
        }
        self.assertEqual(model_to_dict(template), expected)
        self.assertEqual(CookiecutterISAFile.objects.count(), 3)
        for fn in ISA_FILE_NAMES:
            file_obj = CookiecutterISAFile.objects.get(file_name=fn)
            fp = os.path.join(str(ISA_FILE_PATH), fn)
            with open(fp, 'rb') as f:
                expected = {
                    'id': file_obj.pk,
                    'template': template.pk,
                    'file_name': fn,
                    'content': f.read().decode('utf-8'),
                    'sodar_uuid': file_obj.sodar_uuid,
                }
                self.assertEqual(model_to_dict(file_obj), expected)

    def test_post_multi_no_json(self):
        """Test POST with multi-file and no cookiecutter.json file"""
        files = []  # Omit JSON
        for fn in ISA_FILE_NAMES:
            files.append(open(os.path.join(str(ISA_FILE_PATH), fn), 'rb'))
        data = {
            'file_upload': files,
            'description': TEMPLATE_DESC,
            'name': TEMPLATE_NAME,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['file_upload'][0], NO_JSON_MSG
        )
        self.assertEqual(CookiecutterISATemplate.objects.count(), 0)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)

    def test_post_multi_invalid_json(self):
        """Test POST with multi-file and invalid JSON data"""
        f = io.BytesIO(b'{"investigation:')
        f.seek(0)
        files = [SimpleUploadedFile('cookiecutter.json', f.read()).open('rb')]
        for fn in ISA_FILE_NAMES:
            files.append(open(os.path.join(str(ISA_FILE_PATH), fn), 'rb'))
        data = {
            'file_upload': files,
            'description': TEMPLATE_DESC,
            'name': TEMPLATE_NAME,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['file_upload'][0], INVALID_JSON_MSG
        )
        self.assertEqual(CookiecutterISATemplate.objects.count(), 0)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)

    def test_post_multi_no_investigation(self):
        """Test POST with multi-file and no investigation file"""
        files = [open(TEMPLATE_JSON_PATH, 'rb')]
        for fn in [n for n in ISA_FILE_NAMES if not n.startswith('i_')]:
            files.append(open(os.path.join(str(ISA_FILE_PATH), fn), 'rb'))
        data = {
            'file_upload': files,
            'description': TEMPLATE_DESC,
            'name': TEMPLATE_NAME,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['file_upload'][0],
            NO_INVESTIGATION_MSG,
        )
        self.assertEqual(CookiecutterISATemplate.objects.count(), 0)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)

    def test_post_multi_no_study(self):
        """Test POST with multi-file and no study file"""
        files = [open(TEMPLATE_JSON_PATH, 'rb')]
        for fn in [n for n in ISA_FILE_NAMES if not n.startswith('s_')]:
            files.append(open(os.path.join(str(ISA_FILE_PATH), fn), 'rb'))
        data = {
            'file_upload': files,
            'description': TEMPLATE_DESC,
            'name': TEMPLATE_NAME,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['file_upload'][0], NO_STUDY_MSG
        )
        self.assertEqual(CookiecutterISATemplate.objects.count(), 0)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)

    def test_post_no_file(self):
        """Test POST with no files"""
        data = {
            'description': TEMPLATE_DESC,
            'name': TEMPLATE_NAME,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['file_upload'][0], NO_JSON_MSG
        )
        self.assertEqual(CookiecutterISATemplate.objects.count(), 0)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)

    def test_post_empty_name(self):
        """Test POST with empty name"""
        self.assertEqual(CookiecutterISATemplate.objects.count(), 0)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)
        data = {
            'file_upload': self.get_zip(TEMPLATE_PATH, ARCHIVE_NAME),
            'description': TEMPLATE_DESC,
            'name': '',
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CookiecutterISATemplate.objects.count(), 1)
        template = CookiecutterISATemplate.objects.first()
        with open(TEMPLATE_JSON_PATH, 'rb') as f:
            configuration = f.read().decode('utf-8')
        expected = {
            'id': template.pk,
            'description': TEMPLATE_DESC,
            'name': TEMPLATE_NAME_AUTO_GEN,
            'configuration': configuration,
            'active': True,
            'user': self.user.pk,
            'sodar_uuid': template.sodar_uuid,
        }
        self.assertEqual(model_to_dict(template), expected)
        self.assertEqual(CookiecutterISAFile.objects.count(), 3)

    def test_post_non_slugified_name(self):
        """Test POST with non-slugified name"""
        name = 'Non-slugified name'
        data = {
            'file_upload': self.get_zip(TEMPLATE_PATH, ARCHIVE_NAME),
            'description': TEMPLATE_DESC,
            'name': name,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        template = CookiecutterISATemplate.objects.first()
        self.assertEqual(template.name, slugify(name.lower()).replace('-', '_'))

    def test_post_custom_template_exists(self):
        """Test POST with existing custom template with same name"""
        self.make_isa_template(
            name='xxx', description=TEMPLATE_DESC, configuration='{}'
        )
        self.assertEqual(CookiecutterISATemplate.objects.count(), 1)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)
        data = {
            'file_upload': self.get_zip(TEMPLATE_PATH, ARCHIVE_NAME),
            'description': TEMPLATE_DESC,
            'name': TEMPLATE_NAME,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['description'][0],
            'Cookiecutter isa template with this Description already exists.',
        )
        self.assertEqual(CookiecutterISATemplate.objects.count(), 1)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)

    def test_post_cubi_template_exists(self):
        """Test POST with existing CUBI template with same name"""
        self.assertEqual(CookiecutterISATemplate.objects.count(), 0)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)
        data = {
            'file_upload': self.get_zip(TEMPLATE_PATH, ARCHIVE_NAME),
            'description': CUBI_TEMPLATES[0].description,
            'name': TEMPLATE_NAME,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['description'][0],
            CUBI_DESC_EXISTS_MSG,
        )
        self.assertEqual(CookiecutterISATemplate.objects.count(), 0)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)


class TestISATemplateUpdateView(ISATemplateViewTestBase):
    """Tests for ISATemplateUpdateView"""

    def _get_files(self):
        return CookiecutterISAFile.objects.filter(template=self.template)

    def setUp(self):
        super().setUp()
        # Set up template with empty files
        self.template = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration='{}',
            user=self.user,
        )
        for fn in ISA_FILE_NAMES:
            self.make_isa_file(template=self.template, file_name=fn, content='')
        self.url = reverse(
            'isatemplates:update',
            kwargs={'cookiecutterisatemplate': self.template.sodar_uuid},
        )

    def test_get(self):
        """Test ISATemplateUpdateView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        form = response.context.get('form')
        self.assertIn('file_upload', form.fields)
        self.assertIn('description', form.fields)
        self.assertIn('name', form.fields)
        self.assertEqual(form.fields['file_upload'].required, False)

    def test_post(self):
        """Test POST"""
        self.assertEqual(CookiecutterISATemplate.objects.count(), 1)
        self.assertEqual(CookiecutterISAFile.objects.count(), 3)
        self.assertEqual(self.template.description, TEMPLATE_DESC)
        self.assertEqual(self.template.name, TEMPLATE_NAME)
        self.assertEqual(self.template.configuration, '{}')
        self.assertEqual(self.template.active, True)
        for f in self._get_files():
            self.assertEqual(f.content, '')
        self.assertEqual(
            ProjectEvent.objects.filter(event_name='template_update').count(), 0
        )

        data = {
            'file_upload': self.get_zip(TEMPLATE_PATH, ARCHIVE_NAME),
            'description': TEMPLATE_DESC_UPDATE,
            'name': TEMPLATE_NAME_UPDATE,
            'active': False,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(CookiecutterISATemplate.objects.count(), 1)
        self.assertEqual(CookiecutterISAFile.objects.count(), 3)
        self.template.refresh_from_db()
        self.assertEqual(self.template.description, TEMPLATE_DESC_UPDATE)
        self.assertEqual(self.template.name, TEMPLATE_NAME_UPDATE)
        self.assertEqual(self.template.active, False)
        with open(TEMPLATE_JSON_PATH, 'rb') as f:
            configuration = f.read().decode('utf-8')
        self.assertEqual(self.template.configuration, configuration)
        for file_obj in self._get_files():
            fp = os.path.join(str(ISA_FILE_PATH), file_obj.file_name)
            with open(fp, 'rb') as f:
                self.assertEqual(file_obj.content, f.read().decode('utf-8'))
        self.assertEqual(
            ProjectEvent.objects.filter(event_name='template_update').count(), 1
        )

    def test_post_no_file(self):
        """Test POST with no file"""
        self.assertEqual(CookiecutterISATemplate.objects.count(), 1)
        self.assertEqual(CookiecutterISAFile.objects.count(), 3)
        self.assertEqual(self.template.description, TEMPLATE_DESC)
        self.assertEqual(self.template.name, TEMPLATE_NAME)
        self.assertEqual(self.template.configuration, '{}')
        for f in self._get_files():
            self.assertEqual(f.content, '')
        self.assertEqual(
            ProjectEvent.objects.filter(event_name='template_update').count(), 0
        )
        data = {
            'description': TEMPLATE_DESC_UPDATE,
            'name': TEMPLATE_NAME_UPDATE,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CookiecutterISATemplate.objects.count(), 1)
        self.assertEqual(CookiecutterISAFile.objects.count(), 3)
        self.template.refresh_from_db()
        self.assertEqual(self.template.description, TEMPLATE_DESC_UPDATE)
        self.assertEqual(self.template.name, TEMPLATE_NAME_UPDATE)
        self.assertEqual(self.template.configuration, '{}')
        for f in self._get_files():
            self.assertEqual(f.content, '')
        self.assertEqual(
            ProjectEvent.objects.filter(event_name='template_update').count(), 1
        )

    def test_post_no_name(self):
        """Test POST with no name"""
        data = {'description': TEMPLATE_DESC_UPDATE}
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CookiecutterISATemplate.objects.count(), 1)
        self.assertEqual(CookiecutterISAFile.objects.count(), 3)
        self.template.refresh_from_db()
        self.assertEqual(self.template.description, TEMPLATE_DESC_UPDATE)
        self.assertEqual(self.template.name, 'updated_template_name')
        self.assertEqual(self.template.configuration, '{}')

    def test_post_no_json(self):
        """Test POST with no cookiecutter.json file"""
        data = {
            'file_upload': self.get_zip(
                TEMPLATE_PATH, ARCHIVE_NAME, omit='cookiecutter.json'
            ),
            'description': TEMPLATE_DESC_UPDATE,
            'name': TEMPLATE_NAME_UPDATE,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['file_upload'][0], NO_JSON_MSG
        )
        self.template.refresh_from_db()
        self.assertEqual(self.template.description, TEMPLATE_DESC)
        self.assertEqual(self.template.name, TEMPLATE_NAME)
        self.assertEqual(self.template.configuration, '{}')
        self.assertEqual(CookiecutterISAFile.objects.count(), 3)
        for f in self._get_files():
            self.assertEqual(f.content, '')
        self.assertEqual(
            ProjectEvent.objects.filter(event_name='template_update').count(), 0
        )

    def test_post_no_investigation(self):
        """Test POST with no investigation file"""
        data = {
            'file_upload': self.get_zip(
                TEMPLATE_PATH, ARCHIVE_NAME, omit='i_Investigation.txt'
            ),
            'description': TEMPLATE_DESC_UPDATE,
            'name': TEMPLATE_NAME_UPDATE,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['file_upload'][0],
            NO_INVESTIGATION_MSG,
        )
        self.assertEqual(self.template.description, TEMPLATE_DESC)
        self.assertEqual(self.template.name, TEMPLATE_NAME)
        self.assertEqual(self.template.configuration, '{}')
        self.assertEqual(CookiecutterISAFile.objects.count(), 3)
        for f in self._get_files():
            self.assertEqual(f.content, '')

    def test_post_no_study(self):
        """Test POST with no study file"""
        data = {
            'file_upload': self.get_zip(
                TEMPLATE_PATH,
                ARCHIVE_NAME,
                omit='s_{{cookiecutter.s_file_name}}.txt',
            ),
            'description': TEMPLATE_DESC_UPDATE,
            'name': TEMPLATE_NAME_UPDATE,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['file_upload'][0],
            NO_STUDY_MSG,
        )
        self.assertEqual(self.template.description, TEMPLATE_DESC)
        self.assertEqual(self.template.name, TEMPLATE_NAME)
        self.assertEqual(self.template.configuration, '{}')
        self.assertEqual(CookiecutterISAFile.objects.count(), 3)
        for f in self._get_files():
            self.assertEqual(f.content, '')

    def test_post_cubi_template_exists(self):
        """Test POST with existing CUBI template with same name"""
        data = {
            'file_upload': self.get_zip(TEMPLATE_PATH, ARCHIVE_NAME),
            'description': CUBI_TEMPLATES[0].description,
            'name': TEMPLATE_NAME_UPDATE,
        }
        with self.login(self.user):
            response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['description'][0],
            CUBI_DESC_EXISTS_MSG,
        )
        self.assertEqual(self.template.description, TEMPLATE_DESC)
        self.assertEqual(self.template.name, TEMPLATE_NAME)
        self.assertEqual(self.template.configuration, '{}')
        self.assertEqual(CookiecutterISAFile.objects.count(), 3)
        for f in self._get_files():
            self.assertEqual(f.content, '')


class TestISATemplateDeleteView(ISATemplateViewTestBase):
    """Tests for ISATemplateDeleteView"""

    def _get_files(self):
        return CookiecutterISAFile.objects.filter(template=self.template)

    def setUp(self):
        super().setUp()
        # Set up template with empty files
        self.template = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration='{}',
            user=self.user,
        )
        for fn in ISA_FILE_NAMES:
            self.make_isa_file(template=self.template, file_name=fn, content='')
        self.url = reverse(
            'isatemplates:delete',
            kwargs={'cookiecutterisatemplate': self.template.sodar_uuid},
        )

    def test_get(self):
        """Test ISATemplateUpdateView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'], self.template)

    def test_post(self):
        """Test POST"""
        self.assertEqual(
            ProjectEvent.objects.filter(event_name='template_delete').count(), 0
        )
        self.assertEqual(CookiecutterISATemplate.objects.count(), 1)
        self.assertEqual(CookiecutterISAFile.objects.count(), 3)
        with self.login(self.user):
            response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CookiecutterISATemplate.objects.count(), 0)
        self.assertEqual(CookiecutterISAFile.objects.count(), 0)
        self.assertEqual(
            ProjectEvent.objects.filter(event_name='template_delete').count(), 1
        )


class TestISATemplateExportView(ISATemplateViewTestBase):
    """Tests for ISATemplateExportView"""

    def setUp(self):
        super().setUp()
        # Set up template with data
        with open(TEMPLATE_JSON_PATH, 'rb') as f:
            configuration = f.read().decode('utf-8')
        self.template = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration=configuration,
            user=self.user,
        )
        self.file_data = {}
        for fn in ISA_FILE_NAMES:
            fp = os.path.join(str(ISA_FILE_PATH), fn)
            with open(fp, 'rb') as f:
                fd = f.read().decode('utf-8')
                self.file_data[fn] = fd
                self.make_isa_file(
                    template=self.template, file_name=fn, content=fd
                )
        self.url = reverse(
            'isatemplates:export',
            kwargs={'cookiecutterisatemplate': self.template.sodar_uuid},
        )

    def test_get(self):
        """Test ISATemplateExportView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('Content-Disposition'),
            'attachment; filename="{}"'.format(self.template.name + '.zip'),
        )
        f = io.BytesIO(response.content)
        zf = zipfile.ZipFile(f, 'r')
        self.assertIsNone(zf.testzip())
        name_list = zf.namelist()
        self.assertIn('cookiecutter.json', name_list)
        self.assertEqual(
            zf.read('cookiecutter.json').decode('utf-8'),
            self.template.configuration,
        )
        for fn in ISA_FILE_NAMES:
            fp = os.path.join(ISA_FILE_DIR, fn)
            self.assertIn(fp, name_list)
            f_obj = CookiecutterISAFile.objects.get(
                template=self.template, file_name=fn
            )
            self.assertEqual(zf.read(fp).decode('utf-8'), f_obj.content)

    def test_get_invalid_uuid(self):
        """Test GET with invalid UUID"""
        url = reverse(
            'isatemplates:export',
            kwargs={'cookiecutterisatemplate': INVALID_UUID},
        )
        with self.login(self.user):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
