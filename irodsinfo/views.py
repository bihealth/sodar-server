"""Views for the irodsinfo app"""

import io
import json
import logging
import zipfile

from irods.exception import NetworkException, CAT_INVALID_AUTHENTICATION
from packaging import version

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, View

# Projectroles dependency
from projectroles.plugins import PluginAPI
from projectroles.views import LoggedInPermissionMixin, HTTPRefererMixin


logger = logging.getLogger(__name__)
plugin_api = PluginAPI()


class IrodsConfigMixin:
    """Mixin for iRODS configuration views"""

    @staticmethod
    def get_irods_client_env(user, irods_backend):
        """
        Create iRODS configuration file for the current user.
        """
        user_name = user.username
        # Just in case Django mangles the user name case, as it might
        if user_name.find('@') != -1:
            user_name = (
                user_name.split('@')[0] + '@' + user_name.split('@')[1].upper()
            )
        home_path = f'/{settings.IRODS_ZONE}/home/{user_name}'
        cert_file_name = settings.IRODS_HOST + '.crt'

        # Set up irods_environment.json
        irods_env = dict(settings.IRODS_ENV_DEFAULT)
        irods_env.update(
            {
                'irods_cwd': home_path,
                'irods_home': home_path,
                'irods_host': settings.IRODS_HOST_FQDN,
                'irods_port': settings.IRODS_PORT,
                'irods_user_name': user_name,
                'irods_zone_name': settings.IRODS_ZONE,
            }
        )
        if settings.IRODS_CERT_PATH:
            irods_env['irods_ssl_certificate_file'] = cert_file_name
        # Get optional client environment overrides
        irods_env.update(dict(settings.IRODS_ENV_CLIENT))
        # Update authentication scheme with iRODS v4.3+ support
        with irods_backend.get_session() as irods:
            irods_version = irods_backend.get_version(irods)
            if version.parse(irods_version) >= version.parse('4.3'):
                auth_scheme = 'pam_password'
            else:
                auth_scheme = 'PAM'
            irods_env['irods_authentication_scheme'] = auth_scheme
        irods_env = irods_backend.format_env(irods_env)
        logger.debug(f'iRODS environment: {irods_env}')
        return irods_env


class IrodsInfoView(LoggedInPermissionMixin, HTTPRefererMixin, TemplateView):
    """iRODS Information View"""

    permission_required = 'irodsinfo.view_info'
    template_name = 'irodsinfo/info.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        # HACK for #909
        ib_enabled = (
            True if plugin_api.get_backend_api('omics_irods') else False
        )
        irods_backend = plugin_api.get_backend_api('omics_irods')
        unavail_info = {
            'server_ok': False,
            'server_host': settings.IRODS_HOST_FQDN,
            'server_port': settings.IRODS_PORT,
            'server_zone': settings.IRODS_ZONE,
            'server_version': None,
        }
        unavail_status = 'Server Unreachable'

        if irods_backend:
            try:
                with irods_backend.get_session() as irods:
                    context['server_info'] = irods_backend.get_info(irods)
                # HACK: Display FQDN of iRODS server in UI
                context['server_info']['server_host'] = settings.IRODS_HOST_FQDN
            except NetworkException:
                unavail_status = 'Server Unreachable'
            except CAT_INVALID_AUTHENTICATION:
                unavail_status = 'Invalid Authentication'
            except irods_backend.IrodsQueryException:
                unavail_status = 'Invalid iRODS Query'
        if not context.get('server_info'):
            if unavail_status:
                unavail_info['server_status'] = f'Unavailable: {unavail_status}'
                context['server_info'] = unavail_info

        context['irods_backend_enabled'] = ib_enabled
        return context


class IrodsConfigView(
    IrodsConfigMixin, LoggedInPermissionMixin, HTTPRefererMixin, View
):
    """iRODS Configuration file download view"""

    permission_required = 'irodsinfo.get_config'

    def get(self, request, *args, **kwargs):
        irods_backend = plugin_api.get_backend_api('omics_irods')
        if not irods_backend:
            messages.error(request, 'iRODS Backend not enabled.')
            return redirect(reverse('irodsinfo:info'))

        # Create iRODS environment file
        irods_env = self.get_irods_client_env(request.user, irods_backend)
        env_json = json.dumps(irods_env, indent=2)

        # If no client side cert file is provided, return JSON file directly
        if not settings.IRODS_CERT_PATH:
            response = HttpResponse(env_json, content_type='application/json')
            attach_name = 'irods_environment.json'
        # Else return environment JSON file and cert as zip archive
        else:
            io_buf = io.BytesIO()
            zip_file = zipfile.ZipFile(io_buf, 'w')
            # Write environment file
            zip_file.writestr('irods_environment.json', env_json)
            # Write cert file
            try:
                with open(settings.IRODS_CERT_PATH) as cert_file:
                    cert_file_name = irods_env['irods_ssl_certificate_file']
                    zip_file.writestr(cert_file_name, cert_file.read())
            except FileNotFoundError:
                logger.warning(
                    f'iRODS server cert file not found, '
                    f'not adding to archive (path={settings.IRODS_CERT_PATH})'
                )
            zip_file.close()
            response = HttpResponse(
                io_buf.getvalue(), content_type='application/zip'
            )
            attach_name = 'irods_config.zip'
        response['Content-Disposition'] = f'attachment; filename={attach_name}'
        return response
