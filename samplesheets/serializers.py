"""API view model serializers for the samplesheets app"""

from typing import Optional

from django.utils import timezone

from rest_framework import serializers

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.serializers import (
    SODARProjectModelSerializer,
    SODARNestedListSerializer,
)

from samplesheets.forms import (
    IrodsDataRequestValidateMixin,
    IrodsAccessTicketValidateMixin,
)
from samplesheets.models import (
    Investigation,
    Study,
    Assay,
    IrodsDataRequest,
    IrodsAccessTicket,
)


class AssaySerializer(SODARNestedListSerializer):
    """Serializer for the Assay model"""

    irods_path = serializers.SerializerMethodField(read_only=True)

    class Meta(SODARNestedListSerializer.Meta):
        model = Assay
        fields = [
            'file_name',
            'technology_platform',
            'technology_type',
            'measurement_type',
            'comments',
            'irods_path',
            'sodar_uuid',
        ]
        read_only_fields = fields

    def get_irods_path(self, obj: Assay) -> Optional[str]:
        irods_backend = get_backend_api('omics_irods')
        if irods_backend and obj.study.investigation.irods_status:
            return irods_backend.get_path(obj)


class StudySerializer(SODARNestedListSerializer):
    """Serializer for the Study model"""

    irods_path = serializers.SerializerMethodField(read_only=True)
    assays = AssaySerializer(read_only=True, many=True)

    class Meta(SODARNestedListSerializer.Meta):
        model = Study
        fields = [
            'identifier',
            'file_name',
            'title',
            'description',
            # 'study_design',
            # 'factors',
            'comments',
            'irods_path',
            'assays',
            'sodar_uuid',
        ]
        read_only_fields = fields

    def get_irods_path(self, obj: Study) -> Optional[str]:
        irods_backend = get_backend_api('omics_irods')
        if irods_backend and obj.investigation.irods_status:
            return irods_backend.get_path(obj)


class InvestigationSerializer(SODARProjectModelSerializer):
    """Serializer for the Investigation model"""

    studies = StudySerializer(read_only=True, many=True)

    class Meta:
        model = Investigation
        fields = [
            'identifier',
            'file_name',
            'project',
            'title',
            'description',
            # 'ontology_source_refs',
            'irods_status',
            'parser_version',
            'archive_name',
            'comments',
            'studies',
            'sodar_uuid',
        ]
        read_only_fields = fields


class IrodsDataRequestSerializer(
    IrodsDataRequestValidateMixin, SODARProjectModelSerializer
):
    """Serializer for the IrodsDataRequest model"""

    user = serializers.SlugRelatedField(slug_field='sodar_uuid', read_only=True)

    class Meta:
        model = IrodsDataRequest
        fields = [
            'project',
            'action',
            'path',
            'target_path',
            'user',
            'status',
            'status_info',
            'description',
            'date_created',
            'sodar_uuid',
        ]
        read_only_fields = [
            f for f in fields if f not in ['path', 'description']
        ]

    def validate_path(self, value):
        irods_backend = get_backend_api('omics_irods')
        path = irods_backend.sanitize_path(value)
        try:
            self.validate_request_path(
                irods_backend, self.context['project'], self.instance, path
            )
        except Exception as ex:
            raise serializers.ValidationError(str(ex))
        return value

    def create(self, validated_data):
        validated_data['project'] = self.context['project']
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class IrodsAccessTicketSerializer(
    IrodsAccessTicketValidateMixin, serializers.ModelSerializer
):
    """Serializer for the IrodsAccessTicket model"""

    is_active = serializers.SerializerMethodField()
    user = serializers.SlugRelatedField(slug_field='sodar_uuid', read_only=True)

    class Meta:
        model = IrodsAccessTicket
        fields = [
            'study',
            'assay',
            'ticket',
            'path',
            'user',
            'date_created',
            'date_expires',
            'label',
            'is_active',
            'sodar_uuid',
        ]
        read_only_fields = [
            f for f in fields if f not in ['path', 'label', 'date_expires']
        ]

    def get_is_active(self, obj: IrodsAccessTicket) -> bool:
        if not obj.date_expires:
            return True
        return obj.date_expires > timezone.now()

    def validate(self, attrs):
        irods_backend = get_backend_api('omics_irods')
        if not self.instance:
            try:
                attrs['path'] = irods_backend.sanitize_path(attrs['path'])
                # Add assay from path
                attrs['assay'] = Assay.objects.get(
                    sodar_uuid=irods_backend.get_uuid_from_path(
                        attrs['path'], 'assay'
                    )
                )
            except Exception as ex:
                raise serializers.ValidationError(str(ex))
            # Add study from assay
            attrs['study'] = attrs['assay'].study
            # Add empty ticket
            attrs['ticket'] = ''
            # Add user from context
            attrs['user'] = self.context['user']
        else:  # Update
            attrs['path'] = self.instance.path
            attrs['assay'] = self.instance.assay

        error = self.validate_data(
            irods_backend, self.context['project'], self.instance, attrs
        )
        if error:
            raise serializers.ValidationError('{}: {}'.format(*error))
        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['study'] = str(instance.study.sodar_uuid)
        ret['assay'] = (
            str(instance.assay.sodar_uuid) if instance.assay else None
        )
        return ret
