"""API view model serializers for the landingzone app"""

from packaging.version import parse as parse_version
from typing import Optional

from rest_framework import serializers
from rest_framework.exceptions import APIException

# Projectroles dependency
from projectroles.plugins import PluginAPI
from projectroles.serializers import SODARProjectModelSerializer

# Samplesheets dependency
from samplesheets.models import Investigation, Assay

import landingzones.constants as lc

# TODO: Refactor these away
from landingzones.constants import (
    ZONE_STATUS_OK,
    ZONE_STATUS_DELETED,
    ZONE_STATUS_NOT_CREATED,
)
from landingzones.models import LandingZone
from landingzones.utils import get_zone_title


plugin_api = PluginAPI()


# Local constants
ZONE_NO_INV_MSG = 'No investigation found for project'
VERSION_1_1 = parse_version('1.1')


class LandingZoneSerializer(SODARProjectModelSerializer):
    """Serializer for the LandingZone model"""

    title = serializers.CharField(required=False)
    user = serializers.SlugRelatedField(slug_field='sodar_uuid', read_only=True)
    assay = serializers.CharField(source='assay.sodar_uuid')
    status_locked = serializers.SerializerMethodField(read_only=True)
    create_colls = serializers.BooleanField(write_only=True, default=False)
    restrict_colls = serializers.BooleanField(write_only=True, default=False)
    coll_creation = serializers.CharField(read_only=True)
    irods_path = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = LandingZone
        fields = [
            'title',
            'project',
            'user',
            'assay',
            'status',
            'status_info',
            'status_locked',
            'date_modified',
            'description',
            'user_message',
            'create_colls',
            'restrict_colls',
            'coll_creation',
            'configuration',
            'config_data',
            'irods_path',
            'sodar_uuid',
        ]
        read_only_fields = ['status', 'status_info', 'coll_creation']
        write_only_fields = ['create_colls', 'restrict_colls']

    def get_status_locked(self, obj: LandingZone) -> bool:
        return obj.is_locked()

    def get_irods_path(self, obj: LandingZone) -> Optional[str]:
        irods_backend = plugin_api.get_backend_api('omics_irods')
        if irods_backend and obj.status not in [
            ZONE_STATUS_OK,
            ZONE_STATUS_DELETED,
            ZONE_STATUS_NOT_CREATED,
        ]:
            return irods_backend.get_path(obj)

    def validate(self, attrs):
        # If there is no investigation, we can't have a landing zone
        investigation = Investigation.objects.filter(
            project=self.context.get('project'), active=True
        ).first()
        if not investigation:
            ex = APIException(ZONE_NO_INV_MSG)
            ex.status_code = 503
            raise ex
        # Else continue validating the input
        try:
            if 'assay' in attrs:
                assay = Assay.objects.get(
                    sodar_uuid=attrs['assay']['sodar_uuid']
                )
            elif 'assay' in self.context:
                assay = Assay.objects.get(sodar_uuid=self.context['assay'])
            else:
                raise serializers.ValidationError('Assay not found')
        except Exception as ex:
            raise serializers.ValidationError('Assay not found') from ex
        if assay.get_project() != self.context['project']:
            raise serializers.ValidationError(
                'Assay does not belong to project'
            )
        # Ensure restrict_colls is not set without create_colls
        if (
            not self.instance
            and not attrs.get('create_colls', False)
            and attrs.get('restrict_colls', True)
        ):
            raise serializers.ValidationError(
                'Attempting to set restrict_colls True while create_colls is '
                'False'
            )
        # Ensure coll args are not given on update
        if self.instance and any(
            a in attrs for a in ['create_colls', 'restrict_colls']
        ):
            raise serializers.ValidationError(
                'Collection creation params can not be updated after creation'
            )
        return attrs

    def create(self, validated_data):
        validated_data['title'] = get_zone_title(validated_data.get('title'))
        validated_data['project'] = self.context['project']
        validated_data['user'] = self.context['request'].user
        validated_data['assay'] = Assay.objects.get(
            sodar_uuid=validated_data['assay']['sodar_uuid']
        )
        create_colls = validated_data.pop('create_colls', False)
        restrict_colls = validated_data.pop('restrict_colls', False)
        if create_colls and restrict_colls:
            coll_creation = lc.ZONE_COLLS_RESTRICT
        elif create_colls and not restrict_colls:
            coll_creation = lc.ZONE_COLLS_CREATE
        else:
            coll_creation = lc.ZONE_COLLS_NONE
        validated_data['coll_creation'] = coll_creation
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data['title'] = get_zone_title(validated_data.get('title'))
        validated_data['project'] = self.context['project']
        validated_data['user'] = self.context['request'].user
        validated_data['assay'] = Assay.objects.get(
            sodar_uuid=self.context['assay']
        )
        if 'create_colls' in validated_data:
            validated_data.pop('create_colls')
        if 'restrict_colls' in validated_data:
            validated_data.pop('restrict_colls')
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """
        Override to return coll_creation field depending on API version.
        NOTE: Requires request in context object!
        """
        ret = super().to_representation(instance)
        if parse_version(self.context['request'].version) < VERSION_1_1:
            ret.pop('coll_creation')
        return ret
