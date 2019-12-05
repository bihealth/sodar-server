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

        # Add iRODS query API
        irods_backend = get_backend_api('omics_irods')

        if irods_backend:
            try:
                context['server_info'] = irods_backend.get_info()

            except (
                NetworkException,
                CAT_INVALID_AUTHENTICATION,
                irods_backend.IrodsQueryException,
            ):
                context['server_info'] = None

        context['irods_backend'] = get_backend_api('omics_irods')

        # Add settings constants
        context['irods_sample_dir'] = settings.IRODS_SAMPLE_DIR
        context['irods_landing_zone_dir'] = settings.IRODS_LANDING_ZONE_DIR
        context['irods_webdav_url'] = settings.IRODS_WEBDAV_URL
        context['irods_webdav_enabled'] = settings.IRODS_WEBDAV_ENABLED

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

        if settings.IRODSINFO_ENV_PATH:
            try:
                with open(settings.IRODSINFO_ENV_PATH) as env_file:
                    env_opt = json.load(env_file)

                logger.debug('Loaded iRODS env from file: {}'.format(env_opt))

            except FileNotFoundError:
                logger.warning(
                    'iRODS env file not found: generating with default '
                    'parameters (path={})'.format(settings.IRODSINFO_ENV_PATH)
                )
                env_opt = {}

            except Exception as ex:
                logger.error(
                    'Unable to read iRODS env file (path={}): {}'.format(
                        settings.IRODSINFO_ENV_PATH, ex
                    )
                )
                raise ex

        # Set up irods_environment.json
        irods_env = {
            'irods_host': settings.IRODS_HOST,
            'irods_port': settings.IRODS_PORT,
            'irods_authentication_scheme': 'PAM',
            'irods_client_server_negotiation': 'request_server_negotiation',
            'irods_client_server_policy': 'CS_NEG_REFUSE',
            'irods_ssl_verify_server': 'cert'
            if settings.IRODSINFO_SSL_VERIFY
            else 'none',
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
