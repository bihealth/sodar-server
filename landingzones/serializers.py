"""API view model serializers for the landingzone app"""

from rest_framework import serializers

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.serializers import SODARProjectModelSerializer

# Samplesheets dependency
from samplesheets.models import Assay

from landingzones.models import LandingZone
from landingzones.utils import get_zone_title


class LandingZoneSerializer(SODARProjectModelSerializer):
    """Serializer for the LandingZone model"""

    title = serializers.CharField(required=False)
    user = serializers.ReadOnlyField(source='user.username')
    assay = serializers.CharField(source='assay.sodar_uuid')
    irods_path = serializers.SerializerMethodField(read_only=True)

    def validate(self, attrs):
        assay = Assay.objects.filter(
            sodar_uuid=attrs['assay']['sodar_uuid']
        ).first()

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

    class Meta:
        model = LandingZone
        fields = [
            'title',
            'project',
            'user',
            'assay',
            'status',
            'status_info',
            'date_modified',
            'description',
            'configuration',
            'config_data',
            'irods_path',
            'sodar_uuid',
        ]
        read_only_fields = ['status', 'status_info']

    def get_irods_path(self, obj):
        irods_backend = get_backend_api('omics_irods', conn=False)

        if irods_backend and obj.status not in [
            'MOVED',
            'DELETED',
            'NOT CREATED',
        ]:
            return irods_backend.get_path(obj)
