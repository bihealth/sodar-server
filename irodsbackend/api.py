"""iRODS REST API for SODAR Django apps"""

from functools import wraps
from irods.api_number import api_number
from irods.exception import CollectionDoesNotExist
from irods.message import TicketAdminRequest, iRODSMessage
from irods.session import iRODSSession
from irods.ticket import Ticket

from pytz import timezone

from django.conf import settings
from django.utils.text import slugify


# Local constants
ACCEPTED_PATH_TYPES = [
    'Assay',
    'LandingZone',
    'Project',
    'Study']


# Irods init decorator ---------------------------------------------------------


def init_irods(func):
    @wraps(func)
    def _decorator(self, *args, **kwargs):
        try:
            self.irods = iRODSSession(
                host=settings.IRODS_HOST,
                port=settings.IRODS_PORT,
                user=settings.IRODS_USER,
                password=settings.IRODS_PASS,
                zone=settings.IRODS_ZONE)

            # Ensure we have a connection
            self.irods.collections.exists('/{}/home/{}'.format(
                settings.IRODS_ZONE, settings.IRODS_USER))

        except Exception as ex:
            pass    # TODO: Handle exceptions, add logging

        return func(self, *args, **kwargs)

    return _decorator


# API class --------------------------------------------------------------------

class IrodsAPI:
    """iRODS API to be used by Django apps"""

    class IrodsQueryException(Exception):
        """Irods REST service query exception"""
        pass

    def __init__(self):
        self.irods = None

    def __del__(self):
        if self.irods:
            self.irods.cleanup()

    #####################
    # Internal functions
    #####################

    @classmethod
    def _get_datetime(cls, naive_dt):
        """Return a printable datetime in Berlin timezone from a naive
        datetime object"""
        dt = naive_dt.replace(tzinfo=timezone('GMT'))
        dt = dt.astimezone(timezone('Europe/Berlin'))
        return dt.strftime('%Y-%m-%d %H:%M')

    @classmethod
    def _get_obj_list(cls, coll, check_md5=False):
        """
        Return a list of data objects within an iRODS collection
        :param coll: iRODS collection object
        :param check_md5: Whether to add md5 checksum file info (bool)
        :return: Dict
        """
        data = {'data_objects': []}

        for current_coll, sub_colls, objects in coll.walk():
            obj_names = []

            if check_md5:
                obj_names = [o.name for o in current_coll.data_objects]

            for obj in objects:
                if obj.name[-4:] != '.md5':
                    obj_info = {
                        'name': obj.name,
                        'path': obj.path,
                        'size': obj.size,
                        'modify_time': cls._get_datetime(obj.modify_time)}

                    if check_md5:
                        if obj.name + '.md5' in obj_names:
                            obj_info['md5_file'] = True

                        else:
                            obj_info['md5_file'] = False

                    data['data_objects'].append(obj_info)

        return data

    @classmethod
    def _get_obj_stats(cls, coll):
        """
        Return statistics for data objects within an iRODS collection
        :param coll: iRODS collection object
        :return: Dict
        """
        data = {
            'file_count': 0,
            'total_size': 0}

        for current_coll, sub_colls, objects in coll.walk():
            for obj in objects:
                if obj.name[-4:] != '.md5':
                    data['file_count'] += 1
                    data['total_size'] += obj.size

        return data

    # TODO: Fork python-irodsclient and implement ticket functionality there
    def _send_request(self, api_id, *args):
        """
        Temporary function for sending a raw API request using
        python-irodsclient
        :param *args: Arguments for the request body
        :return: Response
        :raise: Exception if iRODS is not initialized
        """
        if not self.irods:
            raise Exception('iRODS session not initialized')

        msg_body = TicketAdminRequest(*args)
        msg = iRODSMessage(
            'RODS_API_REQ', msg=msg_body, int_info=api_number[api_id])

        with self.irods.pool.get_connection() as conn:
            conn.send(msg)
            response = conn.recv()

        return response

    ##########
    # Helpers
    ##########

    @classmethod
    def get_subdir(cls, obj, landing_zone=False, include_parent=True):
        """
        Get the directory name for a stuy or assay under the sample data
        collection
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
                'Function get_display_name() not implemented')

        def get_dir(obj):
            if not landing_zone:
                return '{}_{}'.format(
                    obj.__class__.__name__.lower(),
                    obj.omics_uuid)

            else:
                return slugify(obj.get_display_name()).replace('-', '_')

        # If assay, add study first
        if obj_class == 'Assay' and include_parent:
            ret += get_dir(obj.study) + '/'

        ret += get_dir(obj)
        return ret

    @classmethod
    def get_path(cls, obj):
        """
        Get the path for object
        :param obj: Django model object
        :return: String
        :raise: TypeError if obj is not of supported type
        :raise: ValueError if project is not found
        """
        obj_class = obj.__class__.__name__

        if obj_class not in ACCEPTED_PATH_TYPES:
            raise TypeError(
                'Object of type "{}" not supported! Accepted models: {}',
                format(obj_class, ', '.join(ACCEPTED_PATH_TYPES)))

        if obj_class == 'Project':
            project = obj

        else:
            project = obj.get_project()

        if not project:
            raise ValueError('Project not found for given object')

        # Base path (project)
        path = '/{zone}/projects/{uuid_prefix}/{uuid}'.format(
            zone=settings.IRODS_ZONE,
            uuid_prefix=str(project.omics_uuid)[:2],
            uuid=project.omics_uuid)

        # Project
        if obj_class == 'Project':
            return path

        # Study (in sample data)
        if obj_class == 'Study':
            path += '/{sample_dir}/{study}'.format(
                sample_dir=settings.IRODS_SAMPLE_DIR,
                study=cls.get_subdir(obj))

        # Assay (in sample data)
        elif obj_class == 'Assay':
            path += '/{sample_dir}/{study_assay}'.format(
                sample_dir=settings.IRODS_SAMPLE_DIR,
                study_assay=cls.get_subdir(obj))

        # LandingZone
        elif obj_class == 'LandingZone':
            path += '/{zone_dir}/{user}/{study_assay}/{zone_title}' \
                    '{zone_config}'.format(
                zone_dir=settings.IRODS_LANDING_ZONE_DIR,
                user=obj.user.username,
                study_assay=cls.get_subdir(obj.assay, landing_zone=True),
                zone_title=obj.title,
                zone_config='_' + obj.configuration if
                obj.configuration else '')

        return path

    ###################
    # iRODS Operations
    ###################

    @init_irods
    def get_session(self):
        """
        Get iRODS session object (for direct API access)
        :return: iRODSSession object (already initialized)
        """
        return self.irods

    @init_irods
    def get_info(self):
        """Return iRODS server info"""
        ret = {}

        if self.irods:
            ret['server_status'] = 'available'
            ret['server_host'] = self.irods.host
            ret['server_port'] = self.irods.port
            ret['server_zone'] = self.irods.zone
            ret['server_version'] = '.'.join(
                str(x) for x in self.irods.pool.get_connection().server_version)

        else:
            ret['server_status'] = 'unavailable'

        return ret

    @init_irods
    def get_objects(self, path, check_md5=False):
        """
        Return iRODS object list
        :param path: Full path to iRODS collection
        :param check_md5: Whether to add md5 checksum file info (bool)
        :return: Dict
        :raise: FileNotFoundError if collection is not found
        """
        try:
            coll = self.irods.collections.get(path)

        except CollectionDoesNotExist:
            raise FileNotFoundError('iRODS collection not found')

        ret = self._get_obj_list(coll, check_md5)
        return ret

    @init_irods
    def get_object_stats(self, path):
        """
        Return file count and total file size for all files within a path.
        :param path: Full path to iRODS collection
        :return: Dict
        """
        try:
            coll = self.irods.collections.get(path)

        except CollectionDoesNotExist:
            raise FileNotFoundError('iRODS collection not found')

        ret = self._get_obj_stats(coll)
        return ret

    @init_irods
    def collection_exists(self, path):
        """
        Return True/False depending if the collection defined in path exists
        :param path: Full path to iRODS collection
        :return: Boolean
        """
        return self.irods.collections.exists(path)

    # TODO: Fork python-irodsclient and implement ticket functionality there

    @init_irods
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
        ticket.issue(mode, path)

        # Remove default file writing limitation
        self._send_request(
            'TICKET_ADMIN_AN', 'mod', ticket._ticket, 'write-file', '0')

        # Set expiration
        if expiry_date:
            exp_str = expiry_date.strftime('%Y-%m-%d.%H:%M:%S')
            self._send_request(
                'TICKET_ADMIN_AN', 'mod', ticket._ticket, 'expire', exp_str)

        return ticket

    @init_irods
    def delete_ticket(self, ticket_str):
        """
        Delete ticket
        :param ticket_str: String
        """
        self._send_request('TICKET_ADMIN_AN', 'delete', ticket_str)

