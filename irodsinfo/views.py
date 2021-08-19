"""Views for the irodsinfo app"""

import io
from irods.exception import NetworkException, CAT_INVALID_AUTHENTICATION
import json
import logging
import zipfile

from django.conf import settings
from django.http import HttpResponse
from django.views.generic import TemplateView, View

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.views import LoggedInPermissionMixin, HTTPRefererMixin


logger = logging.getLogger(__name__)


class IrodsInfoView(LoggedInPermissionMixin, HTTPRefererMixin, TemplateView):
    """iRODS Help View"""

    permission_required = 'irodsinfo.view_info'
    template_name = 'irodsinfo/info.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        # HACK for #909
        ib_enabled = (
            True if get_backend_api('omics_irods', conn=False) else False
        )
        irods_backend = get_backend_api('omics_irods')
        unavail_info = {
            'server_ok': False,
            'server_host': settings.IRODS_HOST,
            'server_port': settings.IRODS_PORT,
            'server_zone': settings.IRODS_ZONE,
            'server_version': None,
        }
        unavail_status = 'Server Unreachable'

        if irods_backend:
            try:
                context['server_info'] = irods_backend.get_info()
            except NetworkException:
                unavail_status = 'Server Unreachable'
            except CAT_INVALID_AUTHENTICATION:
                unavail_status = 'Invalid Authentication'
            except irods_backend.IrodsQueryException:
                unavail_status = 'Invalid iRODS Query'

        if not context.get('server_info'):
            if unavail_status:
                unavail_info['server_status'] = 'Unavailable: {}'.format(
                    unavail_status
                )
                context['server_info'] = unavail_info

        context['irods_backend_enabled'] = ib_enabled

        return context


class IrodsConfigView(LoggedInPermissionMixin, HTTPRefererMixin, View):
    """iRODS Configuration file download view"""

    permission_required = 'irodsinfo.get_config'

    def get(self, request, *args, **kwargs):
        user_name = request.user.username
        # Just in case Django mangles the user name case, as it might
        if user_name.find('@') != -1:
            user_name = (
                user_name.split('@')[0] + '@' + user_name.split('@')[1].upper()
            )
        home_path = '/{}/home/{}'.format(settings.IRODS_ZONE, user_name)
        cert_file_name = settings.IRODS_HOST + '.crt'

        # Get optional environment file
        env_opt = {}
        if settings.IRODS_ENV_CLIENT:
            env_opt = settings.IRODS_ENV_CLIENT
            logger.debug(
                'Read iRODS env from IRODS_ENV_CLIENT: {}'.format(env_opt)
            )
        # Set up irods_environment.json
        irods_env = {
            'irods_host': settings.IRODS_HOST,
            'irods_port': settings.IRODS_PORT,
            'irods_authentication_scheme': 'PAM',
            'irods_client_server_negotiation': 'request_server_negotiation',
            'irods_client_server_policy': 'CS_NEG_REFUSE',
            'irods_ssl_verify_server': 'cert',
            'irods_ssl_certificate_file': cert_file_name,
            'irods_zone_name': settings.IRODS_ZONE,
            'irods_user_name': user_name,
            'irods_cwd': home_path,
            'irods_home': home_path,
            'irods_default_hash_scheme': 'MD5',
        }
        irods_env.update(env_opt)
        env_json = json.dumps(irods_env, indent=2)

        # Create zip archive
        io_buf = io.BytesIO()
        zip_file = zipfile.ZipFile(io_buf, 'w')
        # Write environment file
        zip_file.writestr('irods_environment.json', env_json)

        # Write cert file if it exists
        try:
            with open(settings.IRODS_CERT_PATH) as cert_file:
                zip_file.writestr(cert_file_name, cert_file.read())
        except FileNotFoundError:
            logger.warning(
                'iRODS server cert file not found, '
                'not adding to archive (path={})'.format(
                    settings.IRODS_CERT_PATH
                )
            )
        zip_file.close()

        response = HttpResponse(
            io_buf.getvalue(), content_type='application/zip'
        )
        response['Content-Disposition'] = 'attachment; filename={}'.format(
            'irods_config.zip'
        )
        return response
