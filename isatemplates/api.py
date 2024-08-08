"""Backend plugin API for the isatemplates app"""

import os
import tempfile

from cookiecutter.main import cookiecutter
from cubi_isa_templates import _TEMPLATES as ISA_TEMPLATES
from pathlib import Path

from django.conf import settings

from isatemplates.models import CookiecutterISATemplate


# Local constants
TPL_FILE_DIR = '{{cookiecutter.__output_dir}}'


class ISATemplateAPI:
    """Backend API for ISA-Tab template retrieval"""

    @classmethod
    def _get_list_val(cls, t):
        """
        Return list value for a template.

        :param t: CookiecutterISATemplate or IsaTabTemplate object
        :return: Dict
        """
        return {
            'name': t.name,
            'description': t.description[0].upper() + t.description[1:],
        }

    @classmethod
    def get_list(cls):
        """
        Return list of available ISA-Tab templates.

        :return: List of dicts
        """
        ret = []
        for t in CookiecutterISATemplate.objects.filter(active=True):
            ret.append(cls._get_list_val(t))
        if settings.ISATEMPLATES_ENABLE_CUBI_TEMPLATES:
            for t in ISA_TEMPLATES:
                ret.append(cls._get_list_val(t))
        return sorted(ret, key=lambda x: x['description'].lower())

    @classmethod
    def get_template(cls, name):
        """
        Return template by name. Returns either a cubi-isa-templates ISATemplate
        object or a SODAR CookiecutterISATemplate object.

        :param name: String
        :return: ISATemplate or CookiecutterISATemplate object
        :raise: ValueError if enabled template with name is not found
        """
        try:
            return CookiecutterISATemplate.objects.get(name=name, active=True)
        except CookiecutterISATemplate.DoesNotExist:
            if settings.ISATEMPLATES_ENABLE_CUBI_TEMPLATES:
                template = {t.name: t for t in ISA_TEMPLATES}.get(name)
                if template:
                    return template
        raise ValueError('Template not found: {}'.format(name))

    @classmethod
    def is_template(self, name):
        """
        Return whether active template exists by name.

        :param name: String
        :return: Boolean
        """
        if CookiecutterISATemplate.objects.filter(name=name, active=True):
            return True
        if settings.ISATEMPLATES_ENABLE_CUBI_TEMPLATES and {
            t.name: t for t in ISA_TEMPLATES
        }.get(name):
            return True
        return False

    @classmethod
    def run_cookiecutter_custom(cls, sheet_tpl, output_dir, extra_context={}):
        """
        Run cookiecutter on a custom template. Creates ISA-Tab files from the
        template in the given output directory.

        :param sheet_tpl: CookiecutterISATemplate object
        :param output_dir: Writeable directory object (e.g. TemporaryDirectory)
        :param extra_context: Overrides for default values (dict)
        :raise: ValueError if sheet_tpl is not a CookiecutterISATemplate object
        """
        if not isinstance(sheet_tpl, CookiecutterISATemplate):
            raise ValueError('Template is not a CookiecutterISATemplate object')
        with tempfile.TemporaryDirectory() as input_dir:
            Path(os.path.join(input_dir, TPL_FILE_DIR)).mkdir()
            with open(os.path.join(input_dir, 'cookiecutter.json'), 'w') as f:
                f.write(sheet_tpl.configuration)
            for file_obj in sheet_tpl.files.all():
                fp = os.path.join(input_dir, TPL_FILE_DIR, file_obj.file_name)
                with open(fp, 'w') as f:
                    f.write(file_obj.content)
            cookiecutter(
                template=input_dir,
                extra_context=extra_context,
                output_dir=output_dir,
                no_input=True,
            )

    @classmethod
    def get_model(cls):
        """Return CookiecutterISATemplate model"""
        return CookiecutterISATemplate
