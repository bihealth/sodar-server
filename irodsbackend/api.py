"""iRODS REST API for Omics Data Management Django apps"""

from irods.session import iRODSSession
from pytz import timezone

from django.conf import settings


class IrodsAPI:
    """iRODS API to be used by Django apps"""

    class IrodsQueryException(Exception):
        """Irods REST service query exception"""
        pass

    def __init__(self):
        self.irods = iRODSSession(
            host=settings.IRODS_HOST,
            port=settings.IRODS_PORT,
            user=settings.IRODS_USER,
            password=settings.IRODS_PASS,
            zone=settings.IRODS_ZONE)

        # Ensure we have a connection
        self.irods.collections.exists('/{}/home/{}'.format(
            settings.IRODS_ZONE, settings.IRODS_USER))

    @classmethod
    def _get_datetime(cls, naive_dt):
        """Return a printable datetime in Berlin timezone from a naive
        datetime object"""
        dt = naive_dt.replace(tzinfo=timezone('GMT'))
        dt = dt.astimezone(timezone('Europe/Berlin'))
        return dt.strftime('%Y-%m-%d %H:%M')

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

    def list_objects(self, path):
        """Return iRODS object list"""

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

        coll = self.irods.collections.get(path)

        ret = {
            'data_objects': []}

        ret = get_obj_list(coll, ret)
        return ret
