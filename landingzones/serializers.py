"""API view model serializers for the landingzone app"""

from typing import Optional

from rest_framework import serializers
from rest_framework.exceptions import APIException

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.serializers import SODARProjectModelSerializer

# Samplesheets dependency
from samplesheets.models import Investigation, Assay

from landingzones.constants import (
    ZONE_STATUS_OK,
    ZONE_STATUS_DELETED,
    ZONE_STATUS_NOT_CREATED,
)
from landingzones.models import LandingZone
from landingzones.utils import get_zone_title


# Local constants
ZONE_NO_INV_MSG = 'No investigation found for project'


class LandingZoneSerializer(SODARProjectModelSerializer):
    """Serializer for the LandingZone model"""

    title = serializers.CharField(required=False)
    user = serializers.SlugRelatedField(slug_field='sodar_uuid', read_only=True)
    assay = serializers.CharField(source='assay.sodar_uuid')
    status_locked = serializers.SerializerMethodField(read_only=True)
    create_colls = serializers.BooleanField(write_only=True, default=False)
    restrict_colls = serializers.BooleanField(write_only=True, default=False)
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
            'configuration',
            'config_data',
            'irods_path',
            'sodar_uuid',
        ]
        read_only_fields = ['status', 'status_info']
        write_only_fields = ['create_colls', 'restrict_colls']

    def get_status_locked(self, obj: LandingZone) -> bool:
        return obj.is_locked()

    def get_irods_path(self, obj: LandingZone) -> Optional[str]:
        irods_backend = get_backend_api('omics_irods')
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
        return attrs

    def create(self, validated_data):
        validated_data['title'] = get_zone_title(validated_data.get('title'))
        validated_data['project'] = self.context['project']
        validated_data['user'] = self.context['request'].user
        validated_data['assay'] = Assay.objects.get(
            sodar_uuid=validated_data['assay']['sodar_uuid']
        )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data['title'] = get_zone_title(validated_data.get('title'))
        validated_data['project'] = self.context['project']
        validated_data['user'] = self.context['request'].user
        validated_data['assay'] = Assay.objects.get(
            sodar_uuid=self.context['assay']
        )
        return super().update(instance, validated_data)
