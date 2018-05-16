"""iRODS REST API for Omics Data Management Django apps"""

from functools import wraps
from irods.exception import CollectionDoesNotExist
from irods.session import iRODSSession
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

    ##########
    # Helpers
    ##########

    @classmethod
    def get_subdir(cls, obj, landing_zone=False):
        """
        Get the directory name for a stuy or assay under the sample data
        collection
        :param obj: Study or Assay object
        :param landing_zone: Return dir for landing zone if True (bool)
        :return: String
        :raise: TypeError if obj type is not correct
        """
        ret = ''
        obj_class = obj.__class__.__name__

        if obj_class not in ['Assay', 'Study']:
            raise TypeError('Object of type "{}" not supported')

        if not hasattr(obj, 'get_display_name'):
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
        if obj_class == 'Assay':
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
            path += '/{zone_dir}/{user}/{study_assay}/{zone_title}'.format(
                zone_dir=settings.IRODS_LANDING_ZONE_DIR,
                user=obj.user.username,
                study_assay=cls.get_subdir(obj.assay, landing_zone=True),
                zone_title=obj.title)

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
    def get_objects(self, path):
        """
        Return iRODS object list
        :param path: Full path to iRODS collection
        :return: Dict
        :raise: FileNotFoundError if collection is not found
        """

        def get_obj_list(coll, data):
            real_objects = [
                o for o in coll.data_objects
                if o.name.split('.')[-1].lower() != 'md5']

            md5_available = [
                '.'.join(o.path.split('.')[:-1]) for o in coll.data_objects
                if o.name.split('.')[-1].lower() == 'md5' and o.size > 0]

            for data_obj in real_objects:
                data['data_objects'].append({
                    'name': data_obj.name,
                    'path': data_obj.path,
                    'size': data_obj.size,
                    'md5_file': True if
                    data_obj.path in md5_available else False,
                    'modify_time': self._get_datetime(data_obj.modify_time)})

            for sub_coll in coll.subcollections:
                data = get_obj_list(sub_coll, data)

            return data

        try:
            coll = self.irods.collections.get(path)

        except CollectionDoesNotExist:
            raise FileNotFoundError('iRODS collection not found')

        ret = {
            'data_objects': []}

        ret = get_obj_list(coll, ret)
        return ret
