"""API view model serializers for the samplesheets app"""

# Projectroles dependency
from projectroles.serializers import (
    SODARProjectModelSerializer,
    SODARNestedListSerializer,
)

from samplesheets.models import Investigation, Study, Assay


class AssaySerializer(SODARNestedListSerializer):
    """Serializer for the Assay model"""

    class Meta(SODARNestedListSerializer.Meta):
        model = Assay
        fields = [
            'file_name',
            'technology_platform',
            'technology_type',
            'measurement_type',
            'comments',
            'sodar_uuid',
        ]
        read_only_fields = fields


class StudySerializer(SODARNestedListSerializer):
    """Serializer for the Study model"""

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
            'assays',
            'sodar_uuid',
        ]
        read_only_fields = fields


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
