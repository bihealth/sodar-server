"""API view model serializers for the samplesheets app"""

import re
from django.conf import settings
from projectroles.models import Project
from rest_framework import serializers

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.serializers import (
    SODARProjectModelSerializer,
    SODARNestedListSerializer,
)

from samplesheets.forms import ERROR_MSG_EXISTING, ERROR_MSG_INVALID_PATH
from samplesheets.models import Investigation, Study, Assay, IrodsDataRequest


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


class IrodsRequestSerializer(SODARProjectModelSerializer):
    """Serializer for the IrodsDataRequest model"""

    class Meta:
        model = IrodsDataRequest
        fields = ['path', 'description']

    def validate_path(self, value):
        irods_backend = get_backend_api('omics_irods')
        # Remove trailing slashes as irodspython client does not recognize
        # this as a collection
        path = value.rstrip('/')

        old_request = IrodsDataRequest.objects.filter(
            path=path, status__in=['ACTIVE', 'FAILED']
        ).first()
        if old_request and old_request != self.instance:
            raise serializers.ValidationError(ERROR_MSG_EXISTING)

        path_re = re.compile(
            '^' + irods_backend.get_projects_path() + '/[0-9a-f]{2}/'
            '(?P<project_uuid>[0-9a-f-]{36})/'
            + settings.IRODS_SAMPLE_COLL
            + '/study_(?P<study_uuid>[0-9a-f-]{36})/'
            'assay_(?P<assay_uuid>[0-9a-f-]{36})/.+$'
        )
        match = re.search(
            path_re,
            path,
        )
        if not match:
            raise serializers.ValidationError(ERROR_MSG_INVALID_PATH)
        try:
            Project.objects.get(sodar_uuid=match.group('project_uuid'))
        except Project.DoesNotExist:
            raise serializers.ValidationError('Project not found')
        try:
            Study.objects.get(
                sodar_uuid=match.group('study_uuid'),
                investigation__project__sodar_uuid=match.group('project_uuid'),
            )
        except Study.DoesNotExist:
            raise serializers.ValidationError(
                'Study not found in project with UUID'
            )
        try:
            Assay.objects.get(
                sodar_uuid=match.group('assay_uuid'),
                study__sodar_uuid=match.group('study_uuid'),
            )
        except Assay.DoesNotExist:
            raise serializers.ValidationError(
                'Assay not found in this project with UUID'
            )

        with irods_backend.get_session() as irods:
            if not (
                irods.data_objects.exists(path)
                or irods.collections.exists(path)
            ):
                raise serializers.ValidationError(
                    'Path to collection or data object doesn\'t exist in iRODS'
                )
        return value
