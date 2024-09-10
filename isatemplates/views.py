"""UI views for the isatemplates app"""

import io
import json
import os
import zipfile

from cubi_isa_templates import _TEMPLATES as CUBI_TEMPLATES

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
    DetailView,
    TemplateView,
    View,
)

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.views import CurrentUserFormMixin, LoggedInPermissionMixin

from isatemplates.forms import ISATemplateForm
from isatemplates.models import (
    CookiecutterISATemplate,
    CookiecutterISAFile,
    ISA_FILE_PREFIXES,
)


# Local constants
APP_NAME = 'isatemplates'
FILE_DIR = '{{cookiecutter.__output_dir}}'
CUBI_TPL_DICT = {t.name: t for t in CUBI_TEMPLATES}


# Mixins -----------------------------------------------------------------------


class ISATemplateModifyMixin:
    """Modification helpers for ISA-Tab template views"""

    def handle_modify(self, obj, action):
        timeline = get_backend_api('timeline_backend')
        if timeline:
            tl_extra = {}
            if action in ['create', 'update']:
                tl_extra = {
                    'name': obj.name,
                    'description': obj.description,
                    'active': obj.active,
                    'files': [
                        f.file_name
                        for f in CookiecutterISAFile.objects.filter(
                            template=obj
                        ).order_by('file_name')
                    ],
                }
            tl_event = timeline.add_event(
                project=None,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='template_' + action,
                description=action + ' ISA-Tab template {template}',
                extra_data=tl_extra,
                status_type='OK',
            )
            tl_event.add_object(obj, 'template', obj.description)
        messages.success(
            self.request,
            'ISA-Tab template "{}" {}d.'.format(obj.description, action),
        )
        return reverse('isatemplates:list')

    def form_valid(self, form):
        try:
            obj = form.save()
        except Exception as ex:
            messages.error(
                self.request, 'Exception in modifying template: {}'.format(ex)
            )
            return redirect('isatemplates:list')
        return redirect(self.handle_modify(obj, self.form_action))


# Views ------------------------------------------------------------------------


class ISATemplateListView(LoggedInPermissionMixin, TemplateView):
    """CookiecutterISATemplate list view"""

    permission_required = 'isatemplates.view_list'
    template_name = 'isatemplates/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['templates'] = CookiecutterISATemplate.objects.all().order_by(
            'name'
        )
        context['cubi_templates'] = None
        if settings.ISATEMPLATES_ENABLE_CUBI_TEMPLATES:
            context['cubi_templates'] = sorted(
                CUBI_TEMPLATES, key=lambda x: x.description.lower()
            )
        context['backend_enabled'] = (
            get_backend_api('isatemplates_backend') is not None
        )
        return context


class ISATemplateDetailView(LoggedInPermissionMixin, DetailView):
    """CookiecutterISATemplate details view"""

    model = CookiecutterISATemplate
    permission_required = 'isatemplates.view_template'
    slug_url_kwarg = 'cookiecutterisatemplate'
    slug_field = 'sodar_uuid'
    template_name = 'isatemplates/template_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        files = CookiecutterISAFile.objects.filter(template=self.object)
        context['files'] = sorted(
            list(files), key=lambda x: 'isa'.index(x.file_name[0])
        )
        return context


class CUBIISATemplateDetailView(LoggedInPermissionMixin, TemplateView):
    """CUBI template details view"""

    permission_required = 'isatemplates.view_template'
    template_name = 'isatemplates/template_detail_cubi.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        name = self.kwargs.get('name')
        if not name or name not in CUBI_TPL_DICT:
            raise Http404('Template not found')
        t = CUBI_TPL_DICT[name]
        context['name'] = t.name
        context['description'] = t.description[0].upper() + t.description[1:]
        context['configuration'] = json.dumps(t.configuration, indent=2)
        files = []
        for dir_name, sub_dirs, file_names in os.walk(t.path):
            for fn in file_names:
                if any(fn.startswith(x) for x in ISA_FILE_PREFIXES):
                    with open(os.path.join(dir_name, fn), 'r') as f:
                        files.append({'file_name': fn, 'content': f.read()})
        if files:
            context['files'] = sorted(
                files, key=lambda x: 'isa'.index(x['file_name'][0])
            )
        return context


class ISATemplateCreateView(
    LoggedInPermissionMixin,
    CurrentUserFormMixin,
    ISATemplateModifyMixin,
    CreateView,
):
    """CookiecutterISATemplate create view"""

    form_action = 'create'
    form_class = ISATemplateForm
    permission_required = 'isatemplates.create_template'
    template_name = 'isatemplates/template_form.html'


class ISATemplateUpdateView(
    LoggedInPermissionMixin,
    CurrentUserFormMixin,
    ISATemplateModifyMixin,
    UpdateView,
):
    """CookiecutterISATemplate update view"""

    form_action = 'update'
    form_class = ISATemplateForm
    model = CookiecutterISATemplate
    permission_required = 'isatemplates.update_template'
    slug_url_kwarg = 'cookiecutterisatemplate'
    slug_field = 'sodar_uuid'
    template_name = 'isatemplates/template_form.html'


class ISATemplateDeleteView(
    LoggedInPermissionMixin,
    ISATemplateModifyMixin,
    DeleteView,
):
    """CookiecutterISATemplate update view"""

    model = CookiecutterISATemplate
    permission_required = 'isatemplates.delete_template'
    slug_url_kwarg = 'cookiecutterisatemplate'
    slug_field = 'sodar_uuid'
    template_name = 'isatemplates/template_confirm_delete.html'

    def form_valid(self, form):
        self.object.delete()
        return redirect(self.handle_modify(self.object, 'delete'))


class ISATemplateExportView(LoggedInPermissionMixin, View):
    """CookiecutterISATemplate export view"""

    permission_required = 'isatemplates.view_template'

    def get(self, request, *args, **kwargs):
        template = CookiecutterISATemplate.objects.filter(
            sodar_uuid=kwargs.get('cookiecutterisatemplate')
        ).first()
        if not template:
            raise Http404('Template not found')
        zip_name = template.name + '.zip'
        zip_io = io.BytesIO()
        zf = zipfile.ZipFile(zip_io, 'w', compression=zipfile.ZIP_DEFLATED)
        zf.writestr('cookiecutter.json', template.configuration)
        for f in template.files.all():
            zf.writestr(os.path.join(FILE_DIR, f.file_name), f.content)
        zf.close()
        response = HttpResponse(
            zip_io.getvalue(), content_type='application/zip'
        )
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            zip_name
        )
        return response
