"""Tests for UI view permissions in the isatemplates app"""

from cubi_isa_templates import _TEMPLATES as CUBI_TEMPLATES

from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.tests.test_permissions import SiteAppPermissionTestBase

from isatemplates.tests.test_models import (
    CookiecutterISATemplateMixin,
    TEMPLATE_NAME,
    TEMPLATE_DESC,
)


class TestISATemplatesPermissions(
    CookiecutterISATemplateMixin, SiteAppPermissionTestBase
):
    """Tests for isatemplates UI view permissions"""

    def setUp(self):
        super().setUp()
        self.bad_users = [self.regular_user, self.anonymous]

    def test_get_list(self):
        """Test ISATemplateListView GET"""
        url = reverse('isatemplates:list')
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_list_anon(self):
        """Test ISATemplateListView GET with anonymous access enabled"""
        url = reverse('isatemplates:list')
        self.assert_response(url, self.anonymous, 302)

    def test_get_list_read_only(self):
        """Test ISATemplateListView GET with site read-only mode"""
        self.set_site_read_only()
        url = reverse('isatemplates:list')
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_detail(self):
        """Test ISATemplateDetailView GET"""
        template = self.make_isa_template(TEMPLATE_NAME, TEMPLATE_DESC, {})
        url = reverse(
            'isatemplates:detail',
            kwargs={'cookiecutterisatemplate': template.sodar_uuid},
        )
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_detail_read_only(self):
        """Test ISATemplateDetailView GET with site read-only mode"""
        self.set_site_read_only()
        template = self.make_isa_template(TEMPLATE_NAME, TEMPLATE_DESC, {})
        url = reverse(
            'isatemplates:detail',
            kwargs={'cookiecutterisatemplate': template.sodar_uuid},
        )
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_detail_cubi(self):
        """Test CUBIISATemplateDetailView GET"""
        url = reverse(
            'isatemplates:detail_cubi',
            kwargs={'name': CUBI_TEMPLATES[0].name},
        )
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_detail_cubi_read_only(self):
        """Test CUBIISATemplateDetailView GET with site read-only mode"""
        self.set_site_read_only()
        url = reverse(
            'isatemplates:detail_cubi',
            kwargs={'name': CUBI_TEMPLATES[0].name},
        )
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_create(self):
        """Test ISATemplateCreateView GET"""
        url = reverse('isatemplates:create')
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_create_read_only(self):
        """Test ISATemplateCreateView GET with site read-only mode"""
        self.set_site_read_only()
        url = reverse('isatemplates:create')
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_update(self):
        """Test ISATemplateUpdateView GET"""
        template = self.make_isa_template(TEMPLATE_NAME, TEMPLATE_DESC, {})
        url = reverse(
            'isatemplates:update',
            kwargs={'cookiecutterisatemplate': template.sodar_uuid},
        )
        bad_users = [self.regular_user, self.anonymous]
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, bad_users, 302)

    def test_get_update_read_only(self):
        """Test ISATemplateUpdateView GET with site read-only mode"""
        self.set_site_read_only()
        template = self.make_isa_template(TEMPLATE_NAME, TEMPLATE_DESC, {})
        url = reverse(
            'isatemplates:update',
            kwargs={'cookiecutterisatemplate': template.sodar_uuid},
        )
        bad_users = [self.regular_user, self.anonymous]
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, bad_users, 302)

    def test_get_delete(self):
        """Test ISATemplateDeleteView GET"""
        template = self.make_isa_template(TEMPLATE_NAME, TEMPLATE_DESC, {})
        url = reverse(
            'isatemplates:delete',
            kwargs={'cookiecutterisatemplate': template.sodar_uuid},
        )
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_delete_read_only(self):
        """Test ISATemplateDeleteView GET with site read-only mode"""
        self.set_site_read_only()
        template = self.make_isa_template(TEMPLATE_NAME, TEMPLATE_DESC, {})
        url = reverse(
            'isatemplates:delete',
            kwargs={'cookiecutterisatemplate': template.sodar_uuid},
        )
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_export(self):
        """Test ISATemplateExportView GET"""
        template = self.make_isa_template(TEMPLATE_NAME, TEMPLATE_DESC, {})
        url = reverse(
            'isatemplates:export',
            kwargs={'cookiecutterisatemplate': template.sodar_uuid},
        )
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_export_read_only(self):
        """Test ISATemplateExportView GET with site read-only mode"""
        self.set_site_read_only()
        template = self.make_isa_template(TEMPLATE_NAME, TEMPLATE_DESC, {})
        url = reverse(
            'isatemplates:export',
            kwargs={'cookiecutterisatemplate': template.sodar_uuid},
        )
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)
