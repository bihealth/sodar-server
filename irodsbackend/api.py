"""iRODS backend API for SODAR Django apps"""

import logging
import math
import os
import pytz
import random
import re
import string
import uuid

from contextlib import contextmanager
from packaging import version

from irods.api_number import api_number
from irods.collection import iRODSCollection
from irods.column import Criterion
from irods.exception import CollectionDoesNotExist, CAT_NO_ROWS_FOUND
from irods.message import TicketAdminRequest, iRODSMessage
from irods.models import Collection, DataObject, TicketQuery
from irods.query import SpecificQuery
from irods.session import iRODSSession
from irods.ticket import Ticket

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.utils.text import slugify

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS


logger = logging.getLogger(__name__)


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
ACCEPTED_PATH_TYPES = [
    'Assay',
    'LandingZone',
    'Project',
    'Investigation',
    'Study',
]
NAME_LIKE_OVERHEAD = 23  # Magic number for query overhead for name filtering
NAME_LIKE_MAX_LEN = 2200  # Magic number for maximum length of name filters
ENV_INT_PARAMS = [
    'irods_encryption_key_size',
    'irods_encryption_num_hash_rounds',
    'irods_encryption_salt_size',
    'irods_port',
]
USER_GROUP_TEMPLATE = 'omics_project_{uuid}'
TRASH_COLL_NAME = 'trash'
PATH_PARENT_SUBSTRING = '/..'
ERROR_PATH_PARENT = 'Use of parent not allowed in path'
ERROR_PATH_UNSET = 'Path is not set'


class IrodsAPI:
    """iRODS API to be used by Django apps"""

    class IrodsQueryException(Exception):
        """iRODS query exception"""

    def __init__(self, user_name=None, user_pass=None):
        self.user_name = user_name if user_name else settings.IRODS_USER
        self.user_pass = user_pass if user_pass else settings.IRODS_PASS

    # Internal functions -------------------------------------------------------

    def _init_irods(self):
        """
        Initialize an iRODS connection.

        :return: iRODSSession object
        """
        # Set up additional iRODS environment variables
        irods_env = dict(settings.IRODS_ENV_DEFAULT)
        if settings.IRODS_CERT_PATH:
            irods_env['irods_ssl_ca_certificate_file'] = (
                settings.IRODS_CERT_PATH
            )
        irods_env.update(dict(settings.IRODS_ENV_BACKEND))
        # HACK: Clean up environment to avoid python-irodsclient crash
        irods_env = self.format_env(irods_env)
        # logger.debug('iRODS environment: {}'.format(irods_env))
        try:
            irods = iRODSSession(
                host=settings.IRODS_HOST,
                port=settings.IRODS_PORT,
                user=self.user_name,
                password=self.user_pass,
                zone=settings.IRODS_ZONE,
                **irods_env,
            )
            # Ensure we have a connection
            irods.collections.exists(
                '/{}/home/{}'.format(settings.IRODS_ZONE, self.user_name)
            )
            return irods
        except Exception as ex:
            logger.error(
                'Unable to connect to iRODS (host={}, port={}): {} ({})'.format(
                    settings.IRODS_HOST,
                    settings.IRODS_PORT,
                    type(ex).__name__,
                    ex,
                )
            )
            raise ex

    @classmethod
    def _get_datetime(cls, naive_dt):
        """
        Return a printable datetime in the system timezone from a naive
        datetime object.
        """
        dt = naive_dt.replace(tzinfo=pytz.timezone('GMT'))
        dt = dt.astimezone(timezone.get_default_timezone())
        return dt.strftime('%Y-%m-%d %H:%M')

    @classmethod
    def _get_query_alias(cls):
        """Return a random iCAT SQL query alias"""
        return 'sodar_query_{}'.format(
            ''.join(
                random.SystemRandom().choice(
                    string.ascii_lowercase + string.ascii_uppercase
                )
                for _ in range(16)
            )
        )

    @classmethod
    def _send_request(cls, irods, api_id, *args):
        """
        Temporary function for sending a raw API request using
        python-irodsclient.

        :param irods: iRODS connection object
        :param api_id: iRODS API ID
        :param *args: Arguments for the request body
        :return: Response
        :raise: Exception if iRODS is not initialized
        """
        msg_body = TicketAdminRequest(*args)
        msg = iRODSMessage(
            'RODS_API_REQ', msg=msg_body, int_info=api_number[api_id]
        )
        with irods.pool.get_connection() as conn:
            conn.send(msg)
            response = conn.recv()
        return response

    @classmethod
    def _validate_project(cls, project):
        """
        Validate the project parameter for retrieving a project iRODS path.

        :param project: Project object
        :raise: ValueError if "project" is not a valid Project object or if the
                object is of type CATEGORY
        """
        if project.__class__.__name__ != 'Project':
            raise ValueError('Argument "project" is not a Project object')
        if project.type != PROJECT_TYPE_PROJECT:
            raise ValueError(
                'Project type is not {}'.format(PROJECT_TYPE_PROJECT)
            )

    # Helpers ------------------------------------------------------------------

    @classmethod
    def format_env(cls, env):
        """
        Format an iRODS environment dict to ensure values are in a format
        accepted by iRODS.

        :param env: iRODS environment (dict)
        :return: dict
        """
        for k in env.keys():
            if k in ENV_INT_PARAMS:
                env[k] = int(env[k])
        return env

    @classmethod
    def sanitize_path(cls, path):
        """
        Validate and sanitize iRODS path.

        :param path: Full or partial iRODS path to collection or data object
                     (string)
        :raise: ValueError if iRODS path is invalid or unacceptable
        :return: Sanitized iRODS path (string)
        """
        if not path:
            raise ValueError(ERROR_PATH_UNSET)
        if path[0] != '/':
            path = '/' + path
        if PATH_PARENT_SUBSTRING in path:
            raise ValueError(ERROR_PATH_PARENT)
        if path[-1] == '/':
            path = path[:-1]
        return path

    @classmethod
    def get_sub_path(cls, obj, landing_zone=False, include_parent=True):
        """
        Get the collection path for a study or assay under the sample data
        collection.

        :param obj: Study or Assay object
        :param landing_zone: Return dir for landing zone if True (bool)
        :param include_parent: Include parent dir if True (bool)
        :return: String
        :raise: TypeError if obj type is not correct
        :raise: NotImplementedError if get_display_name() is not found in obj
        """
        ret = ''
        obj_class = obj.__class__.__name__
        if obj_class not in ['Assay', 'Study']:
            raise TypeError('Object of type "{}" not supported')
        if landing_zone and not hasattr(obj, 'get_display_name'):
            raise NotImplementedError(
                'Function get_display_name() not implemented'
            )

        def _get_path(obj):
            if not landing_zone:
                return '{}_{}'.format(
                    obj.__class__.__name__.lower(), obj.sodar_uuid
                )
            else:
                return slugify(obj.get_display_name()).replace('-', '_')

        # If assay, add study first
        if obj_class == 'Assay' and include_parent:
            ret += _get_path(obj.study) + '/'
        ret += _get_path(obj)
        return ret

    @classmethod
    def get_path(cls, obj):
        """
        Return the iRODS path for for a SODAR database object.

        :param obj: Django model object
        :return: String
        :raise: TypeError if obj is not of supported type
        :raise: ValueError if project is not found
        """
        obj_class = obj.__class__.__name__
        if obj_class not in ACCEPTED_PATH_TYPES:
            raise TypeError(
                'Object of type "{}" not supported! Accepted models: {}'.format(
                    obj_class, ', '.join(ACCEPTED_PATH_TYPES)
                )
            )
        if obj_class == 'Project':
            project = obj
        else:
            project = obj.get_project()
        if not project:
            raise ValueError('Project not found for given object')

        # Base path (project)
        path = '{root_path}/projects/{uuid_prefix}/{uuid}'.format(
            root_path=cls.get_root_path(),
            uuid_prefix=str(project.sodar_uuid)[:2],
            uuid=project.sodar_uuid,
        )
        # Project
        if obj_class == 'Project':
            return path
        # Investigation (sample data root)
        elif obj_class == 'Investigation':
            path += '/{sample_dir}'.format(
                sample_dir=settings.IRODS_SAMPLE_COLL
            )
        # Study (in sample data)
        elif obj_class == 'Study':
            path += '/{sample_dir}/{study}'.format(
                sample_dir=settings.IRODS_SAMPLE_COLL,
                study=cls.get_sub_path(obj),
            )
        # Assay (in sample data)
        elif obj_class == 'Assay':
            path += '/{sample_dir}/{study_assay}'.format(
                sample_dir=settings.IRODS_SAMPLE_COLL,
                study_assay=cls.get_sub_path(obj),
            )
        # LandingZone
        elif obj_class == 'LandingZone':
            path += (
                '/{zone_coll}/{user}/{study_assay}/{zone_title}'
                '{zone_config}'.format(
                    zone_coll=settings.IRODS_LANDING_ZONE_COLL,
                    user=obj.user.username,
                    study_assay=cls.get_sub_path(obj.assay, landing_zone=True),
                    zone_title=obj.title,
                    zone_config=(
                        '_' + obj.configuration if obj.configuration else ''
                    ),
                )
            )
        return path

    @classmethod
    def get_sample_path(cls, project):
        """
        Return the iRODS path for project sample data.

        :param project: Project object
        :return: String
        :raise: ValueError if "project" is not a valid Project object or if the
                object is of type CATEGORY
        """
        cls._validate_project(project)
        return cls.get_path(project) + '/' + settings.IRODS_SAMPLE_COLL

    @classmethod
    def get_zone_path(cls, project):
        """
        Return the iRODS path for project landing zones.

        :param project: Project object
        :return: String
        :raise: ValueError if "project" is not a valid Project object or if the
                object is of type CATEGORY
        """
        cls._validate_project(project)
        return cls.get_path(project) + '/' + settings.IRODS_LANDING_ZONE_COLL

    @classmethod
    def get_root_path(cls):
        """Return the SODAR root path in iRODS"""
        irods_zone = settings.IRODS_ZONE
        root_path = ''
        if settings.IRODS_ROOT_PATH:
            root_path = cls.sanitize_path(settings.IRODS_ROOT_PATH)
            if root_path.startswith('/' + irods_zone):
                raise ValueError(
                    'iRODS zone must not be included in IRODS_ROOT_PATH'
                )
        return '/{}{}'.format(irods_zone, root_path)

    @classmethod
    def get_projects_path(cls):
        """Return the SODAR projects collection path"""
        return cls.get_root_path() + '/projects'

    @classmethod
    def get_trash_path(cls):
        """Return the trash path in the current zone"""
        return '/' + os.path.join(settings.IRODS_ZONE, TRASH_COLL_NAME)

    @classmethod
    def get_uuid_from_path(cls, path, obj_type):
        """
        Return project, study or assay UUID from iRODS path or None if not
        found.

        :param path: Full iRODS path (string)
        :param obj_type: Type of object ("project", "study" or "assay")
        :return: String or None
        :raise: ValueError if obj_type is not accepted
        """
        path_regex = {
            'project': cls.get_root_path()
            + '/projects/[a-zA-Z0-9]{2}/(.+?)(?:/|$)',
            'study': '/study_(.+?)(?:/|$)',
            'assay': '/assay_(.+?)(?:/|$)',
        }
        obj_type = obj_type.lower()
        if obj_type not in path_regex.keys():
            raise ValueError(
                'Invalid argument for obj_type "{}"'.format(obj_type)
            )
        s = re.search(path_regex[obj_type], cls.sanitize_path(path))
        if s:
            return s.group(1)

    @classmethod
    def get_user_group_name(cls, project):
        """
        Return iRODS user group name for project.

        :param project: Project object or project UUID
        :return: String
        """
        if isinstance(project, (uuid.UUID, str)):
            project_uuid = project
        else:
            cls._validate_project(project)
            project_uuid = project.sodar_uuid
        return USER_GROUP_TEMPLATE.format(uuid=project_uuid)

    # TODO: Add tests
    @classmethod
    def get_url(
        cls,
        view,
        project=None,
        path='',
        md5=False,
        colls=False,
        method='GET',
        absolute=False,
        request=None,
    ):
        """
        Get the list or stats URL for an iRODS path.

        :param view: View of the URL ("stats" or "list")
        :param path: Full iRODS path (string)
        :param project: Project object or None
        :param md5: Include MD5 or not for a list view (boolean, default=False)
        :param colls: Include collections in list (boolean, default=False)
        :param method: Method for the function (string)
        :param absolute: Whether or not an absolute URI is required (boolean)
        :param request: Request object (required for building an absolute URI)
        :return: String
        :raise: ValueError if the view or method param is invalid
        """
        if view not in ['list', 'stats']:
            raise ValueError('Invalid type "{}" for view'.format(view))
        if method not in ['GET', 'POST']:
            raise ValueError('Invalid method "{}"'.format(method))

        url_kwargs = {'project': str(project.sodar_uuid)} if project else None
        rev_url = reverse('irodsbackend:{}'.format(view), kwargs=url_kwargs)

        if method == 'GET':
            query_string = {'path': cls.sanitize_path(path)}
            if view == 'list':
                query_string['md5'] = int(md5)
                query_string['colls'] = int(colls)
            rev_url += '?' + urlencode(query_string)
        if absolute and request:
            return request.build_absolute_uri(rev_url)
        return rev_url

    # iRODS Operations ---------------------------------------------------------

    @contextmanager
    def get_session(self):
        """
        Return the iRODS session object for direct API access as a generator.
        Use with the "with" keyword to ensure connection cleanup.

        :return: iRODSSession object wrapped as a generator
        """
        irods = self._init_irods()
        try:
            yield irods
        finally:
            irods.cleanup()

    def get_session_obj(self):
        """
        Return the iRODS session object for direct API access.
        NOTE: Connection needs to be manually closed with cleanup()! If
        possible, use get_session() instead.

        :return: iRODSSession object
        """
        return self._init_irods()

    @classmethod
    def get_info(cls, irods):
        """
        Return iRODS server info.

        :param irods: iRODSSession object
        :return: Dict
        :raise: NetworkException if iRODS is unreachable
        :raise: CAT_INVALID_AUTHENTICATION if iRODS authentication is invalid
        :raise: irods_backend.IrodsQueryException for iRODS query errors
        """
        return {
            'server_ok': True,
            'server_status': 'Available',
            'server_host': irods.host,
            'server_port': irods.port,
            'server_zone': irods.zone,
            'server_version': cls.get_version(irods),
        }

    @classmethod
    def get_version(cls, irods):
        """
        Return the version of the iRODS server SODAR is connected to.

        :param irods: iRODSSession object
        :return: String
        """
        return '.'.join(str(x) for x in irods.server_version)

    @classmethod
    def get_access_lookup(cls, irods):
        """
        Return an ACL lookup dict compatible with the currently used iRODS
        server version (4.2 and 4.3 supported).

        :param irods: iRODSSession object
        :return: Dict
        """
        v = version.parse(cls.get_version(irods))
        d = '_' if v >= version.parse('4.3') else ' '
        return {
            'read': 'read{}object'.format(d),
            'read{}object'.format(d): 'read',
            'write': 'modify{}object'.format(d),
            'modify{}object'.format(d): 'write',
            'null': 'null',
            'own': 'own',
        }

    def get_object_stats(self, irods, path):
        """
        Return file count and total file size for all files within a path.

        :param irods: iRODSSession object
        :param path: Full path to iRODS collection
        :return: Dict
        """
        try:
            coll = irods.collections.get(self.sanitize_path(path))
        except CollectionDoesNotExist:
            raise FileNotFoundError('iRODS collection not found')

        ret = {'file_count': 0, 'total_size': 0}
        sql = (
            'SELECT COUNT(data_id) as file_count, '
            'SUM(data_size) as total_size '
            'FROM (SELECT data_id, data_size FROM r_data_main '
            'JOIN r_coll_main USING (coll_id) '
            'WHERE (coll_name = \'{coll_path}\' '
            'OR coll_name LIKE \'{coll_path}/%\') '
            'AND data_name NOT LIKE \'%.md5\' '
            'GROUP BY data_id, data_size) AS sub_query'.format(
                coll_path=coll.path
            )
        )
        # logger.debug('Object stats query = "{}"'.format(sql))
        query = self.get_query(irods, sql)

        try:
            result = next(query.get_results())
            ret['file_count'] = int(result[0]) if result[0] else 0
            ret['total_size'] = int(result[1]) if result[1] else 0
        except CAT_NO_ROWS_FOUND:
            pass
        except Exception as ex:
            logger.error(
                'iRODS exception in get_object_stats(): {}; '
                'SQL = "{}"'.format(ex.__class__.__name__, sql)
            )
        finally:
            query.remove()
        return ret

    @classmethod
    def get_colls_recursively(cls, coll):
        """
        Return all subcollections for a coll efficiently (without multiple
        queries).

        :param coll: Collection object
        :return: List
        """
        query = coll.manager.sess.query(Collection).filter(
            Criterion('like', Collection.parent_name, coll.path + '%')
        )
        return [iRODSCollection(coll.manager, row) for row in query]

    def get_objs_recursively(
        self, irods, coll, include_md5=False, name_like=None, limit=None
    ):
        """
        Return objects below a coll recursively. Replacement for the
        non-scalable walk() function in the API. Also gets around the query
        length limitation in iRODS.

        :param irods: iRODSSession object
        :param coll: Collection object
        :param include_md5: if True, include .md5 files
        :param name_like: Filtering of file names (string or list of strings)
        :param limit: Limit retrieval to n rows (int)
        :return: List
        """
        ret = []
        md5_filter = '' if include_md5 else 'AND data_name NOT LIKE \'%.md5\''
        path_lookup = []
        q_count = 1

        def _do_query(irods, nl=None):
            sql = (
                'SELECT DISTINCT ON (data_id) data_name, data_size, '
                'r_data_main.modify_ts as modify_ts, coll_name '
                'FROM r_data_main JOIN r_coll_main USING (coll_id) '
                'WHERE (coll_name = \'{coll_path}\' '
                'OR coll_name LIKE \'{coll_path}/%\') {md5_filter}'.format(
                    coll_path=coll.path, md5_filter=md5_filter
                )
            )
            if nl:
                if not isinstance(nl, list):
                    nl = [nl]
                sql += ' AND ('
                for i, n in enumerate(nl):
                    if i > 0:
                        sql += ' OR '
                    sql += 'data_name LIKE \'%{}%\''.format(n)
                sql += ')'
            # TODO: Shouldn't we also allow limit if including .md5 files?
            if not include_md5 and limit:
                sql += ' LIMIT {}'.format(limit)

            # logger.debug('Object list query = "{}"'.format(sql))
            columns = [
                DataObject.name,
                DataObject.size,
                DataObject.modify_time,
                Collection.name,
            ]
            query = self.get_query(irods, sql, columns)

            try:
                results = query.get_results()
                for row in results:
                    obj_path = row[Collection.name] + '/' + row[DataObject.name]
                    if q_count > 1 and obj_path in path_lookup:
                        continue  # Skip possible dupes in case of split query
                    ret.append(
                        {
                            'name': row[DataObject.name],
                            'type': 'obj',
                            'path': obj_path,
                            'size': row[DataObject.size],
                            'modify_time': self._get_datetime(
                                row[DataObject.modify_time]
                            ),
                        }
                    )
                    if q_count > 1:
                        path_lookup.append(obj_path)
            except CAT_NO_ROWS_FOUND:
                pass
            except Exception as ex:
                logger.error(
                    'iRODS exception in get_objs_recursively(): {}'.format(
                        ex.__class__.__name__
                    )
                )
            finally:
                query.remove()

        # HACK: Long queries cause a crash with iRODS so we have to split them
        if name_like and isinstance(name_like, list) and len(name_like) > 1:
            f_len = sum([len(x) + NAME_LIKE_OVERHEAD for x in name_like])
            q_count = math.ceil(f_len / NAME_LIKE_MAX_LEN)
            q_len = math.ceil(len(name_like) / q_count)
            q_idx = 0
            for i in range(q_count):
                _do_query(irods, name_like[q_idx : q_idx + q_len])
                q_idx = q_idx + q_len
        else:  # Single query
            _do_query(irods, name_like)
        return sorted(ret, key=lambda x: x['path'])

    def get_objects(
        self,
        irods,
        path,
        include_md5=False,
        include_colls=False,
        name_like=None,
        limit=None,
    ):
        """
        Return a flat iRODS object list recursively under a given path.

        :param irods: iRODSSession object
        :param path: Full path to iRODS collection
        :param include_md5: Include .md5 checksum files (bool)
        :param include_colls: Include collections (bool)
        :param name_like: Filtering of file names (string or list of strings)
        :param limit: Limit search to n rows (int)
        :return: List
        :raise: FileNotFoundError if collection is not found
        """
        try:
            coll = irods.collections.get(self.sanitize_path(path))
        except CollectionDoesNotExist:
            raise FileNotFoundError('iRODS collection not found')

        if name_like:
            if not isinstance(name_like, list):
                name_like = [name_like]
            name_like = [n.replace('_', '\_') for n in name_like]  # noqa
        ret = self.get_objs_recursively(
            irods,
            coll,
            include_md5=include_md5,
            name_like=name_like,
            limit=limit,
        )

        # Add collections if enabled
        # TODO: Combine into a single query? (see issues #1440, #1883)
        if include_colls:
            colls = self.get_colls_recursively(coll)
            for c in colls:
                ret.append({'name': c.name, 'type': 'coll', 'path': c.path})
            ret = sorted(ret, key=lambda x: x['path'])
        return ret

    @classmethod
    def get_child_colls(cls, irods, path):
        """
        Return child collections for a collection by path. Does not return
        children recursively.

        :param irods: iRODSSession object
        :param path: Full path to iRODS collection
        :return: List
        """
        try:
            coll = irods.collections.get(cls.sanitize_path(path))
            return coll.subcollections
        except CollectionDoesNotExist:
            return []

    def get_query(self, irods, sql, columns=None, register=True):
        """
        Return a SpecificQuery object with a standard query alias. If
        registered, should be removed with remove() after use.

        :param irods: iRODSSession object
        :param sql: SQL (string)
        :param columns: List of columns to return (optional)
        :param register: Register query before returning (bool, default=True)
        :return: SpecificQuery
        """
        query = SpecificQuery(irods, sql, self._get_query_alias(), columns)
        if register:
            query.register()
        return query

    def issue_ticket(
        self, irods, mode, path, ticket_str=None, expiry_date=None
    ):
        """
        Issue ticket for a specific iRODS collection.

        :param irods: iRODSSession object
        :param mode: "read" or "write"
        :param path: iRODS path for creating the ticket
        :param ticket_str: String to use as the ticket
        :param expiry_date: Expiry date (DateTime object, optional)
        :return: irods client Ticket object
        """
        ticket = Ticket(irods, ticket=ticket_str)
        ticket.issue(mode, self.sanitize_path(path))
        # Remove default file writing limitation
        self._send_request(
            irods,
            'TICKET_ADMIN_AN',
            'mod',
            ticket._ticket,
            'write-file',
            '0',
        )
        # Set expiration
        if expiry_date:
            exp_str = expiry_date.strftime('%Y-%m-%d.%H:%M:%S')
            self._send_request(
                irods,
                'TICKET_ADMIN_AN',
                'mod',
                ticket._ticket,
                'expire',
                exp_str,
            )
        return ticket

    def get_ticket(self, irods, ticket_str):
        """
        Get ticket from iRODS.

        :param irods: iRODSSession object
        :param ticket_str: String
        :return: Ticket object or None
        """
        ticket_query = irods.query(TicketQuery.Ticket).filter(
            TicketQuery.Ticket.string == ticket_str
        )
        ticket_res = list(ticket_query)
        if len(ticket_res) == 1:
            return Ticket(ticket_res[0])
        return None

    def delete_ticket(self, irods, ticket_str):
        """
        Delete ticket.

        :param irods: iRODSSession object
        :param ticket_str: String
        """
        try:
            self._send_request(irods, 'TICKET_ADMIN_AN', 'delete', ticket_str)
        except Exception:
            raise Exception(
                'Failed to delete iRODS ticket {}'.format(ticket_str)
            )
