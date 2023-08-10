"""API view model serializers for the samplesheets app"""

import re

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from rest_framework import serializers

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.serializers import (
    SODARProjectModelSerializer,
    SODARNestedListSerializer,
    SODARUserSerializer,
)

from samplesheets.forms import IrodsDataRequestValidateMixin
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

    def get_irods_path(self, obj):
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

    def get_irods_path(self, obj):
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

    user = SODARUserSerializer(read_only=True)

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


class IrodsAccessTicketSerializer(serializers.ModelSerializer):
    """Serializer for the IrodsAccessTicket model"""

    is_active = serializers.SerializerMethodField()

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
            'sodar_uuid',
            'is_active',
        ]

    def get_is_active(self, obj):
        if not obj.date_expires:
            return True
        return obj.date_expires > timezone.now()

    def get_read_only_fields(self):
        return [
            'study',
            'assay',
            'ticket',
            'path',
            'user',
            'date_created',
            'is_active',
            'sodar_uuid',
        ]

    def validate(self, attrs):
        irods_backend = get_backend_api('omics_irods')
        # Validate path (only if creating)
        if not self.instance:
            project = self.context['project']
            try:
                attrs['path'] = irods_backend.sanitize_path(attrs['path'])
            except Exception as ex:
                raise serializers.ValidationError(
                    {'path': 'Invalid iRODS path: {}'.format(ex)}
                )
            # Ensure path is within project
            if not attrs['path'].startswith(irods_backend.get_path(project)):
                raise serializers.ValidationError(
                    {'path': 'Path is not within the project'}
                )
            # Ensure path is a collection
            with irods_backend.get_session() as irods:
                if not irods.collections.exists(attrs['path']):
                    raise serializers.ValidationError(
                        {
                            'path': 'Path does not point to a collection or the'
                            ' collection doesn\'t exist'
                        }
                    )
            # Ensure path is within a project assay
            match = re.search(
                r'/assay_([0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12})',
                attrs['path'],
            )
            if not match:
                raise serializers.ValidationError(
                    {'path': 'Not a valid assay path'}
                )
            else:
                try:
                    # Set assay if successful
                    attrs['assay'] = Assay.objects.get(
                        study__investigation__project=project,
                        sodar_uuid=match.group(1),
                    )
                except ObjectDoesNotExist:
                    raise serializers.ValidationError(
                        {'path': 'Assay not found in project'}
                    )
            # Ensure path is not assay root
            if attrs['path'] == irods_backend.get_path(attrs['assay']):
                raise serializers.ValidationError(
                    {
                        'path': 'Ticket creation for assay root path is not allowed'
                    }
                )

            # Add study from assay
            attrs['study'] = attrs['assay'].study
            # Add empty ticket
            attrs['ticket'] = ''
            # Add user from context
            attrs['user'] = self.context['user']
        else:  # Update
            attrs['path'] = self.instance.path
            attrs['assay'] = self.instance.assay
            attrs['study'] = self.instance.study
            attrs['ticket'] = self.instance.ticket
            attrs['user'] = self.instance.user

            # Check if expiry date is in the past
        if (
            attrs.get('date_expires')
            and attrs.get('date_expires') <= timezone.now()
        ):
            raise serializers.ValidationError(
                {'date_expires': 'Expiry date in the past not allowed'}
            )

            # Check if unexpired ticket already exists for path
        if (
            not self.instance
            and IrodsAccessTicket.objects.filter(path=attrs['path']).first()
        ):
            raise serializers.ValidationError(
                {'path': 'Ticket for path already exists'}
            )

        return attrs
