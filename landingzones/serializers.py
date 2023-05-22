"""API view model serializers for the landingzone app"""

from rest_framework import serializers

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.serializers import (
    SODARProjectModelSerializer,
    SODARUserSerializer,
)

# Samplesheets dependency
from samplesheets.models import Assay

from landingzones.models import LandingZone
from landingzones.utils import get_zone_title


class LandingZoneSerializer(SODARProjectModelSerializer):
    """Serializer for the LandingZone model"""

    title = serializers.CharField(required=False)
    user = SODARUserSerializer(read_only=True)
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

    def get_status_locked(self, obj):
        return obj.is_locked()

    def get_irods_path(self, obj):
        irods_backend = get_backend_api('omics_irods')
        if irods_backend and obj.status not in [
            'MOVED',
            'DELETED',
            'NOT CREATED',
        ]:
            return irods_backend.get_path(obj)

    def validate(self, attrs):
        assay = Assay.objects.get(sodar_uuid=self.context['assay'])
        if not assay:
            raise serializers.ValidationError('Assay not found')
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
        # validated_data['assay'] = Assay.objects.get(
        #     sodar_uuid=validated_data['assay']['sodar_uuid']
        # )
        return super().update(instance, validated_data)
