"""API view model serializers for the samplesheets app"""

from rest_framework import serializers
from drf_keyed_list import KeyedListSerializer

from samplesheets.models import Investigation, Study, Assay


# TODO: Move to SODAR Core
class SODARModelSerializer(serializers.ModelSerializer):
    """Base serializer for any SODAR model with a sodar_uuid field"""

    sodar_uuid = serializers.CharField(read_only=True)

    class Meta:
        pass


# TODO: Move to SODAR Core
class SODARNestedListSerializer(SODARModelSerializer):
    """Serializer for SODAR models in nested lists. To be used in cases where
    the object is not intended to be listed or modified on its own."""

    class Meta:
        list_serializer_class = KeyedListSerializer
        keyed_list_serializer_field = 'sodar_uuid'


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


class InvestigationSerializer(SODARModelSerializer):
    """Serializer for the Investigation model"""

    studies = StudySerializer(read_only=True, many=True)
    project = serializers.CharField(source='project.sodar_uuid')

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
