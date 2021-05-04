"""iRODS backend API for SODAR Django apps"""

import json
import logging
import math
import random
import re
import string

from irods.api_number import api_number
from irods.collection import iRODSCollection
from irods.column import Criterion
from irods.exception import CollectionDoesNotExist, CAT_NO_ROWS_FOUND
from irods.message import TicketAdminRequest, iRODSMessage
from irods.models import Collection, DataObject
from irods.query import SpecificQuery
from irods.session import iRODSSession
from irods.ticket import Ticket

from pytz import timezone

from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.text import slugify


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


logger = logging.getLogger(__name__)


class IrodsAPI:
    """iRODS API to be used by Django apps"""

    class IrodsQueryException(Exception):
        """Irods query exception"""

        pass

    def __init__(self, conn=True):
        # conn = kwargs.get('conn') or True
        self.irods = None
        self.irods_env = {}
        if not conn:
            return

        # Get optional environment file
        if settings.IRODS_ENV_PATH:
            try:
                with open(settings.IRODS_ENV_PATH) as env_file:
                    self.irods_env = json.load(env_file)

                logger.debug(
                    'Loaded iRODS env from file: {}'.format(self.irods_env)
                )
            except FileNotFoundError:
                logger.warning(
                    'iRODS env file not found: connecting with default '
                    'parameters (path={})'.format(settings.IRODS_ENV_PATH)
                )
            except Exception as ex:
                logger.error(
                    'Unable to read iRODS env file (path={}): {}'.format(
                        settings.IRODS_ENV_PATH, ex
                    )
                )
                raise ex

        # Connect
        try:
            self.irods = iRODSSession(
                host=settings.IRODS_HOST,
                port=settings.IRODS_PORT,
                user=settings.IRODS_USER,
                password=settings.IRODS_PASS,
                zone=settings.IRODS_ZONE,
                **self.irods_env,
            )
            # Ensure we have a connection
            self.irods.collections.exists(
                '/{}/home/{}'.format(settings.IRODS_ZONE, settings.IRODS_USER)
            )
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

    def __del__(self):
        if self.irods:
            self.irods.cleanup()

    # Internal functions -------------------------------------------------------

    @classmethod
    def _get_datetime(cls, naive_dt):
        """Return a printable datetime in Berlin timezone from a naive
        datetime object"""
        dt = naive_dt.replace(tzinfo=timezone('GMT'))
        dt = dt.astimezone(timezone(settings.TIME_ZONE))
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
    def _sanitize_coll_path(cls, path):
        """
        Return sanitized version of iRODS collection path
        :param path: iRODS collection path (string)
        :return: String
        """
        if path:
            if path[0] != '/':
                path = '/' + path
            if path[-1] == '/':
                path = path[:-1]
        return path

    # TODO: Fork python-irodsclient and implement ticket functionality there
    def _send_request(self, api_id, *args):
        """
        Temporary function for sending a raw API request using
        python-irodsclient.

        :param *args: Arguments for the request body
        :return: Response
        :raise: Exception if iRODS is not initialized
        """
        if not self.irods:
            raise Exception('iRODS session not initialized')

        msg_body = TicketAdminRequest(*args)
        msg = iRODSMessage(
            'RODS_API_REQ', msg=msg_body, int_info=api_number[api_id]
        )

        with self.irods.pool.get_connection() as conn:
            conn.send(msg)
            response = conn.recv()
        return response

    ##########
    # Helpers
    ##########

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

        def get_path(obj):
            if not landing_zone:
                return '{}_{}'.format(
                    obj.__class__.__name__.lower(), obj.sodar_uuid
                )
            else:
                return slugify(obj.get_display_name()).replace('-', '_')

        # If assay, add study first
        if obj_class == 'Assay' and include_parent:
            ret += get_path(obj.study) + '/'

        ret += get_path(obj)
        return ret

    @classmethod
    def get_path(cls, obj):
        """
        Get the path for object.

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
        rp = settings.IRODS_ROOT_PATH
        path = '/{zone}/projects/{root_prefix}{uuid_prefix}/{uuid}'.format(
            root_prefix=rp + '/' if rp else '',
            zone=settings.IRODS_ZONE,
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
                    zone_config='_' + obj.configuration
                    if obj.configuration
                    else '',
                )
            )

        return path

    @classmethod
    def get_sample_path(cls, project):
        """
        Return project sample data path.

        :param project: Project object
        :return: String
        :raise: ValueError if "project" is not a valid Project object
        """
        if project.__class__.__name__ != 'Project':
            raise ValueError('Argument "project" is not a Project object')
        return cls.get_path(project) + '/' + settings.IRODS_SAMPLE_COLL

    @classmethod
    def get_root_path(cls):
        """Return the root path for SODAR data"""
        root_prefix = (
            '/' + settings.IRODS_ROOT_PATH if settings.IRODS_ROOT_PATH else ''
        )
        return '/{}{}'.format(settings.IRODS_ZONE, root_prefix)

    @classmethod
    def get_projects_path(cls):
        """Return the SODAR projects collection path"""
        return cls.get_root_path() + '/projects'

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
        root_prefix = (
            settings.IRODS_ROOT_PATH + '/' if settings.IRODS_ROOT_PATH else ''
        )
        path_regex = {
            'project': '/{}/'.format(settings.IRODS_ZONE)
            + root_prefix
            + 'projects/[a-zA-Z0-9]{2}/(.+?)(?:/|$)',
            'study': '/study_(.+?)(?:/|$)',
            'assay': '/assay_(.+?)(?:/|$)',
        }
        obj_type = obj_type.lower()
        if obj_type not in path_regex.keys():
            raise ValueError(
                'Invalid argument for obj_type "{}"'.format(obj_type)
            )
        s = re.search(path_regex[obj_type], cls._sanitize_coll_path(path))
        if s:
            return s.group(1)

    # TODO: Add tests
    @classmethod
    def get_url(
        cls,
        view,
        project=None,
        path='',
        md5=False,
        method='GET',
        absolute=False,
        request=None,
    ):
        """
        Get the list or stats URL for an iRODS path.

        :param view: View of the URL ("stats" or "list")
        :param path: Full iRODS path (string)
        :param project: Project object or None
        :param md5: Include MD5 or not for a list view (boolean)
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
            query_string = {'path': cls._sanitize_coll_path(path)}
            if view == 'list':
                query_string['md5'] = int(md5)
            rev_url += '?' + urlencode(query_string)

        if absolute and request:
            return request.build_absolute_uri(rev_url)

        return rev_url

    # iRODS Operations ---------------------------------------------------------

    def get_session(self):
        """
        Get iRODS session object for direct API access.

        :return: iRODSSession object (already initialized)
        """
        return self.irods

    def get_info(self):
        """
        Return iRODS server info.

        :return: Dict
        :raise: NetworkException if iRODS is unreachable
        :raise: CAT_INVALID_AUTHENTICATION if iRODS authentication is invalid
        :raise: irods_backend.IrodsQueryException for iRODS query errors
        """
        return {
            'server_ok': True,
            'server_status': 'Available',
            'server_host': self.irods.host,
            'server_port': self.irods.port,
            'server_zone': self.irods.zone,
            'server_version': '.'.join(
                str(x) for x in self.irods.pool.get_connection().server_version
            ),
        }

    def get_objects(self, path, check_md5=False, name_like=None, limit=None):
        """
        Return iRODS object list.

        :param path: Full path to iRODS collection
        :param check_md5: Whether to add md5 checksum file info (bool)
        :param name_like: Filtering of file names (string or list of strings)
        :param limit: Limit search to n rows (int)
        :return: Dict
        :raise: FileNotFoundError if collection is not found
        """
        try:
            coll = self.irods.collections.get(self._sanitize_coll_path(path))
        except CollectionDoesNotExist:
            raise FileNotFoundError('iRODS collection not found')

        if name_like:
            if not isinstance(name_like, list):
                name_like = [name_like]
            name_like = [n.replace('_', '\_') for n in name_like]  # noqa
        ret = {'data_objects': []}
        md5_paths = None

        data_objs = self.get_objs_recursively(
            coll, name_like=name_like, limit=limit
        )
        if data_objs and check_md5:
            md5_paths = [
                o['path']
                for o in self.get_objs_recursively(
                    coll, md5=True, name_like=name_like
                )
            ]

        for o in data_objs:
            if check_md5:
                if o['path'] + '.md5' in md5_paths:
                    o['md5_file'] = True
                else:
                    o['md5_file'] = False
            ret['data_objects'].append(o)

        return ret

    def get_object_stats(self, path):
        """
        Return file count and total file size for all files within a path.

        :param path: Full path to iRODS collection
        :return: Dict
        """
        try:
            coll = self.irods.collections.get(self._sanitize_coll_path(path))
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
        query = self.get_query(sql)

        try:
            result = next(query.get_results())
            ret['file_count'] = int(result[0]) if result[0] else 0
            ret['total_size'] = int(result[1]) if result[1] else 0
        except CAT_NO_ROWS_FOUND:
            pass
        except Exception as ex:
            logger.error(
                'iRODS exception in get_object_stats(): {}; SQL = "{}"'.format(
                    ex.__class__.__name__, sql
                )
            )
        finally:
            query.remove()

        return ret

    def collection_exists(self, path):
        """
        Return True/False depending if the collection defined in path exists

        :param path: Full path to iRODS collection
        :return: Boolean
        """
        return self.irods.collections.exists(self._sanitize_coll_path(path))

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

    def get_objs_recursively(self, coll, md5=False, name_like=None, limit=None):
        """
        Return objects below a coll recursively. Replacement for the
        non-scalable walk() function in the API. Also gets around the query
        length limitation in iRODS.

        :param coll: Collection object
        :param md5: if True, return .md5 files, otherwise anything but them
        :param name_like: Filtering of file names (string or list of strings)
        :param limit: Limit search to n rows (int)
        :return: List
        """
        ret = []
        md5_filter = 'LIKE' if md5 else 'NOT LIKE'
        path_lookup = []
        q_count = 1

        def _do_query(nl=None):
            sql = (
                'SELECT DISTINCT ON (data_id) data_name, data_size, '
                'r_data_main.modify_ts as modify_ts, coll_name '
                'FROM r_data_main JOIN r_coll_main USING (coll_id) '
                'WHERE (coll_name = \'{coll_path}\' '
                'OR coll_name LIKE \'{coll_path}/%\') '
                'AND data_name {md5_filter} \'%.md5\''.format(
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
            if not md5 and limit:
                sql += ' LIMIT {}'.format(limit)

            # logger.debug('Object list query = "{}"'.format(sql))
            columns = [
                DataObject.name,
                DataObject.size,
                DataObject.modify_time,
                Collection.name,
            ]
            query = self.get_query(sql, columns)

            try:
                results = query.get_results()
                for row in results:
                    obj_path = row[Collection.name] + '/' + row[DataObject.name]
                    if q_count > 1 and obj_path in path_lookup:
                        continue  # Skip possible dupes in case of split query
                    ret.append(
                        {
                            'name': row[DataObject.name],
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
                    'iRODS exception in _get_objs_recursively(): {}'.format(
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
                _do_query(name_like[q_idx : q_idx + q_len])
                q_idx = q_idx + q_len
        else:  # Single query
            _do_query(name_like)
        return sorted(ret, key=lambda x: x['path'])

    def get_coll_by_path(self, path):
        try:
            return self.irods.collections.get(path)
        except CollectionDoesNotExist:
            return None

    def get_child_colls_by_path(self, path):
        coll = self.get_coll_by_path(path)
        if coll:
            return coll.subcollections
        return []

    def get_query(self, sql, columns=None, register=True):
        """
        Return a SpecificQuery object with a standard query alias. If
        registered, should be removed with remove() after use.

        :param sql: SQL (string)
        :param columns: List of columns to return (optional)
        :param register: Register query before returning (bool, default=True)
        :return: SpecificQuery
        """
        query = SpecificQuery(self.irods, sql, self._get_query_alias(), columns)
        if register:
            query.register()
        return query

    # TODO: Fork python-irodsclient and implement ticket functionality there

    def issue_ticket(self, mode, path, ticket_str=None, expiry_date=None):
        """
        Issue ticket for a specific iRODS collection

        :param mode: "read" or "write"
        :param path: iRODS path for creating the ticket
        :param ticket_str: String to use as the ticket
        :param expiry_date: Expiry date (DateTime object, optional)
        :return: irods client Ticket object
        """
        ticket = Ticket(self.irods, ticket=ticket_str)
        ticket.issue(mode, self._sanitize_coll_path(path))

        # Remove default file writing limitation
        self._send_request(
            'TICKET_ADMIN_AN', 'mod', ticket._ticket, 'write-file', '0'
        )

        # Set expiration
        if expiry_date:
            exp_str = expiry_date.strftime('%Y-%m-%d.%H:%M:%S')
            self._send_request(
                'TICKET_ADMIN_AN', 'mod', ticket._ticket, 'expire', exp_str
            )

        return ticket

    def delete_ticket(self, ticket_str):
        """
        Delete ticket
        :param ticket_str: String
        """
        try:
            self._send_request('TICKET_ADMIN_AN', 'delete', ticket_str)
        except Exception:
            raise Exception('Failed to delete iRODS ticket %s' % ticket_str)
