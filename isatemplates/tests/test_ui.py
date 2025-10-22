"""UI tests for the isatemplates app"""

import os

from cubi_isa_templates import _TEMPLATES as CUBI_TEMPLATES

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

# Projectroles dependency
from projectroles.tests.test_ui import UITestBase

from isatemplates.models import ISA_FILE_PREFIXES
from isatemplates.tests.test_models import (
    CookiecutterISATemplateMixin,
    CookiecutterISAFileMixin,
    TEMPLATE_NAME,
    TEMPLATE_DESC,
    TEMPLATE_JSON_PATH,
)
from isatemplates.tests.test_views import ISA_FILE_NAMES, ISA_FILE_PATH

# Local constants
BACKEND_PLUGINS_NO_TPL = settings.ENABLED_BACKEND_PLUGINS.copy()
BACKEND_PLUGINS_NO_TPL.remove('isatemplates_backend')


class TestISATemplateListView(CookiecutterISATemplateMixin, UITestBase):
    """Tests for ISATemplateListView UI"""

    def setUp(self):
        super().setUp()
        self.url = reverse('isatemplates:list')

    def test_get_no_templates(self):
        """Test ISATemplateListView GET with no templates"""
        self.login_and_redirect(self.superuser, self.url)
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.CLASS_NAME, 'sodar-it-list-item')
        self.assertIsNotNone(
            self.selenium.find_element(By.ID, 'sodar-it-list-empty')
        )
        self.assertEqual(
            len(
                self.selenium.find_elements(By.CLASS_NAME, 'sodar-it-cubi-item')
            ),
            len(CUBI_TEMPLATES),
        )
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, 'sodar-it-cubi-empty')
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, 'sodar-it-alert-backend')

    def test_get_existing_template(self):
        """Test GET with existing template"""
        self.template = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration={},
            active=True,
            user=self.superuser,
        )
        self.login_and_redirect(self.superuser, self.url)
        self.assertEqual(
            len(
                self.selenium.find_elements(By.CLASS_NAME, 'sodar-it-list-item')
            ),
            1,
        )
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, 'sodar-it-list-empty')
        self.assertEqual(
            len(
                self.selenium.find_elements(By.CLASS_NAME, 'sodar-it-cubi-item')
            ),
            len(CUBI_TEMPLATES),
        )
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, 'sodar-it-cubi-empty')
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, 'sodar-it-alert-backend')

    @override_settings(ISATEMPLATES_ENABLE_CUBI_TEMPLATES=False)
    def test_get_disable_cubi_templates(self):
        """Test GET with CUBI templates disabled"""
        self.login_and_redirect(self.superuser, self.url)
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.CLASS_NAME, 'sodar-it-cubi-item')
        self.assertIsNotNone(
            self.selenium.find_element(By.ID, 'sodar-it-cubi-empty')
        )
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, 'sodar-it-alert-backend')

    @override_settings(ENABLED_BACKEND_PLUGINS=BACKEND_PLUGINS_NO_TPL)
    def test_get_disable_backend(self):
        """Test GET with backend plugin disabled"""
        self.login_and_redirect(self.superuser, self.url)
        self.assertIsNotNone(
            self.selenium.find_element(By.ID, 'sodar-it-alert-backend')
        )


class TestISATemplateDetailView(
    CookiecutterISATemplateMixin, CookiecutterISAFileMixin, UITestBase
):
    """Tests for ISATemplateDetailView UI"""

    def setUp(self):
        super().setUp()
        # Set up template with data
        with open(TEMPLATE_JSON_PATH, 'rb') as f:
            configuration = f.read().decode('utf-8')
        self.template = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration=configuration,
            user=self.superuser,
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
        self.login_and_redirect(self.superuser, self.url)
        self.assertEqual(
            len(
                self.selenium.find_elements(
                    By.CLASS_NAME, 'sodar-it-template-detail-file'
                )
            ),
            3,
        )
        for f in self.template.files.all():
            elem = self.selenium.find_element(
                By.ID, f'sodar-it-template-detail-file-{f.sodar_uuid}'
            )
            self.assertIn(
                f.file_name, elem.find_element(By.TAG_NAME, 'h4').text
            )


class TestCUBIISATemplateDetailView(
    CookiecutterISATemplateMixin, CookiecutterISAFileMixin, UITestBase
):
    """Tests for CUBIISATemplateDetailView UI"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'isatemplates:detail_cubi', kwargs={'name': CUBI_TEMPLATES[0].name}
        )

    def test_get(self):
        """Test CUBIISATemplateDetailView GET"""
        self.login_and_redirect(self.superuser, self.url)
        self.assertEqual(
            len(
                self.selenium.find_elements(
                    By.CLASS_NAME, 'sodar-it-template-detail-file'
                )
            ),
            3,
        )
        for dir_name, sub_dirs, file_names in os.walk(CUBI_TEMPLATES[0].path):
            for fn in file_names:
                if any(fn.startswith(x) for x in ISA_FILE_PREFIXES):
                    self.assertIsNotNone(
                        self.selenium.find_element(
                            By.ID, f'sodar-it-template-detail-file-{fn}'
                        )
                    )
