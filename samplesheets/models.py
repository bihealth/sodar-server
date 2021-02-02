import os

from altamisa.constants import table_headers as th
import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField, JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.timezone import localtime

# Projectroles dependency
from projectroles.models import Project

from samplesheets.utils import (
    get_alt_names,
    get_comment,
    get_config_name,
    ALT_NAMES_COUNT,
)


# Access Django user model
AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


# Local constants
DEFAULT_LENGTH = 255

GENERIC_MATERIAL_TYPES = {
    'SOURCE': 'Source',
    'MATERIAL': 'Material',
    'SAMPLE': 'Sample',
    'DATA': 'Data File',
}

# Map JSON attributes to altamISA headers
ATTR_HEADER_MAP = {
    'characteristics': th.CHARACTERISTICS,
    'comments': th.COMMENT,
    'factor_values': th.FACTOR_VALUE,
    'parameter_values': th.PARAMETER_VALUE,
}

# Special field attributes not a part of JSON attributes
SPECIAL_FIELD_ATTRS = [
    'extract_label',
    'first_dimension',
    'second_dimension',
]

GENERIC_MATERIAL_CHOICES = [(k, v) for k, v in GENERIC_MATERIAL_TYPES.items()]
NOT_AVAILABLE_STR = '(N/A)'
CONFIG_LABEL_CREATE = 'Created With Configuration'

ISATAB_TAGS = {
    'IMPORT': 'Imported from an ISAtab archive',
    'REPLACE': 'Replacing a previous ISAtab',
}


# Abstract base class ----------------------------------------------------------


class BaseSampleSheet(models.Model):
    """Abstract class with common SODAR sample sheet properties"""

    #: Internal UUID for the object
    sodar_uuid = models.UUIDField(
        default=uuid.uuid4, unique=True, help_text='SODAR UUID for the object'
    )

    #: Data sharing rules
    sharing_data = JSONField(default=dict, help_text='Data sharing rules')

    #: Consent retraction data
    retraction_data = JSONField(
        default=dict, help_text='Consent retraction data'
    )

    #: Comments
    comments = JSONField(default=dict, help_text='Comments')

    #: Headers for ISAtab parsing/writing
    headers = ArrayField(
        models.CharField(max_length=DEFAULT_LENGTH, blank=True),
        default=list,
        help_text='Headers for ISAtab parsing/writing',
    )

    class Meta:
        abstract = True

    # Custom row-level functions
    def get_study(self):
        """Return associated study if it exists"""
        if hasattr(self, 'assay') and self.assay:
            return self.assay.study

        elif hasattr(self, 'study') and self.study:
            return self.study

        elif type(self) == Study:
            return self

    def get_project(self):
        """Return associated project"""
        if type(self) == Investigation:
            return self.project

        elif type(self) == Study:
            return self.investigation.project

        elif type(self) == Protocol:
            return self.study.investigation.project

        elif type(self) in [Assay, GenericMaterial, Process]:
            if self.study:
                return self.study.investigation.project

            elif self.assay:
                return self.assay.study.investigation.project


# Investigation ----------------------------------------------------------------


class Investigation(BaseSampleSheet):
    """ISA model compatible investigation"""

    #: Locally unique identifier
    identifier = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='Locally unique identifier',
    )

    #: File name for exporting
    file_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='File name for exporting',
    )

    #: Project to which the investigation belongs
    project = models.ForeignKey(
        Project,
        null=False,
        related_name='investigations',
        help_text='Project to which the investigation belongs',
    )

    #: Investigation title (optional, can be derived from project)
    title = models.CharField(
        max_length=DEFAULT_LENGTH,
        blank=True,
        null=True,
        help_text='Title (optional, can be derived from project)',
    )

    #: Investigation description (optional, can be derived from project)
    description = models.TextField(
        blank=True,
        null=True,
        help_text='Investigation description (optional, can be derived from '
        'project)',
    )

    #: Submission date
    submission_date = models.DateField(null=True, help_text='Submission date')

    #: Public release date
    public_release_date = models.DateField(
        null=True, help_text='Public release date'
    )

    #: Ontology source references
    ontology_source_refs = JSONField(
        default=dict, help_text='Ontology source references'
    )

    #: Investigation publications
    publications = JSONField(
        default=dict, help_text='Investigation publications'
    )

    #: Investigation publications
    contacts = JSONField(default=dict, help_text='Investigation contacts')

    #: Active status of investigation (only one active per project)
    active = models.BooleanField(
        default=False,
        help_text='Active status of investigation (one active per project)',
    )

    # TODO: Update irods_status help_text in the next migration
    #: Status of iRODS collection structure creation
    irods_status = models.BooleanField(
        default=False, help_text='Status of iRODS directory structure creation'
    )

    #: Parser version
    parser_version = models.CharField(
        max_length=DEFAULT_LENGTH,
        blank=True,  # Blank/null = old version before this was introduced
        null=True,
        help_text='Parser version',
    )

    #: Parser warnings
    parser_warnings = JSONField(
        default=dict,
        help_text='Warnings from the previous parsing of the corresponding '
        'ISAtab',
    )

    #: File name of the original archive if imported
    archive_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='File name of the original archive if imported',
    )

    def __str__(self):
        return '{}: {}'.format(self.project.title, self.title)

    def __repr__(self):
        values = (self.project.title, self.title)
        return 'Investigation({})'.format(', '.join(repr(v) for v in values))

    # Custom row-level functions

    def get_configuration(self):
        """Return used configuration as string if found"""
        # TODO: Do this with a nice regex instead, too tired now
        if CONFIG_LABEL_CREATE not in self.comments:
            return None

        return get_config_name(get_comment(self, CONFIG_LABEL_CREATE))

    def get_material_count(self, item_type):
        """Return matieral count of a certain type within the investigation"""
        return GenericMaterial.objects.filter(
            Q(item_type=item_type),
            Q(study__investigation=self) | Q(assay__study__investigation=self),
        ).count()


# Study ------------------------------------------------------------------------


class Study(BaseSampleSheet):
    """ISA model compatible study"""

    #: Locally unique identifier
    identifier = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='Locally unique identifier',
    )

    #: File name for exporting
    file_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='File name for exporting',
    )

    #: Investigation to which the study belongs
    investigation = models.ForeignKey(
        Investigation,
        null=False,
        related_name='studies',
        help_text='Investigation to which the study belongs',
    )

    #: Title of the study (optional)
    title = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        help_text='Title of the study (optional)',
    )

    #: Study description (optional)
    description = models.TextField(
        unique=False, blank=True, help_text='Study description (optional)'
    )

    #: Submission date
    submission_date = models.DateField(null=True, help_text='Submission date')

    #: Public release date
    public_release_date = models.DateField(
        null=True, help_text='Public release date'
    )

    #: Study design descriptors
    study_design = JSONField(default=dict, help_text='Study design descriptors')

    #: Study publications
    publications = JSONField(default=dict, help_text='Study publications')

    #: Study factors
    factors = JSONField(default=dict, help_text='Study factors')

    #: Study contacts
    contacts = JSONField(default=dict, help_text='Study contacts')

    #: Study arcs
    arcs = ArrayField(
        ArrayField(models.CharField(max_length=DEFAULT_LENGTH, blank=True)),
        default=list,
        help_text='Study arcs',
    )

    class Meta:
        ordering = ['identifier']
        unique_together = ('investigation', 'identifier', 'title')
        verbose_name_plural = 'studies'

    def __str__(self):
        return '{}: {}'.format(self.get_project().title, self.get_name())

    def __repr__(self):
        values = (self.get_project().title, self.get_name())
        return 'Study({})'.format(', '.join(repr(v) for v in values))

    # Custom row-level functions

    def get_name(self):
        """Return simple printable name for study"""
        return self.title if self.title else self.identifier

    def get_display_name(self):
        """Return display name for study"""
        return self.title.strip('.').title() if self.title else self.identifier

    def get_nodes(self):
        """Return list of all nodes (materials and processes) for study"""
        return list(
            GenericMaterial.objects.filter(study=self).order_by('pk')
        ) + list(
            Process.objects.filter(study=self)
            .order_by('pk')
            .prefetch_related('protocol')
        )

    def get_sources(self):
        """Return sources used in study"""
        # TODO: Add tests
        return GenericMaterial.objects.filter(
            study=self, item_type='SOURCE'
        ).order_by('name')


# Protocol ---------------------------------------------------------------------


class Protocol(BaseSampleSheet):
    """ISA model compatible protocol"""

    #: Protocol name
    name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='Protocol name',
    )

    #: Study to which the protocol belongs
    study = models.ForeignKey(
        Study,
        related_name='protocols',
        help_text='Study to which the protocol belongs',
    )

    #: Protocol type
    protocol_type = JSONField(
        null=True, default=dict, help_text='Protocol type'
    )

    #: Protocol description
    description = models.TextField(
        unique=False, blank=True, help_text='Protocol description'
    )

    #: Protocol URI
    uri = models.CharField(
        max_length=2048, unique=False, help_text='Protocol URI'
    )

    #: Protocol version
    version = models.CharField(
        max_length=DEFAULT_LENGTH, unique=False, help_text='Protocol version'
    )

    #: Protocol parameters
    parameters = JSONField(default=dict, help_text='Protocol parameters')

    #: Protocol components
    components = JSONField(default=dict, help_text='Protocol components')

    class Meta:
        unique_together = ('study', 'name')

    def __str__(self):
        return '{}: {}/{}'.format(
            self.get_project().title, self.study.get_name(), self.name
        )

    def __repr__(self):
        values = (self.get_project().title, self.study.get_name(), self.name)
        return 'Protocol({})'.format(', '.join(repr(v) for v in values))


# Assay ------------------------------------------------------------------------


class Assay(BaseSampleSheet):
    """ISA model compatible assay"""

    #: File name for exporting
    file_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='File name for exporting',
    )

    #: Study to which the assay belongs
    study = models.ForeignKey(
        Study,
        related_name='assays',
        help_text='Study to which the assay belongs',
    )

    #: Technology platform (optional)
    technology_platform = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Technology platform (optional)',
    )

    #: Technology type
    technology_type = JSONField(default=dict, help_text='Technology type')

    #: Measurement type
    measurement_type = JSONField(default=dict, help_text='Measurement type')

    #: Assay arcs
    arcs = ArrayField(
        ArrayField(models.CharField(max_length=DEFAULT_LENGTH, blank=True)),
        default=list,
        help_text='Assay arcs',
    )

    class Meta:
        unique_together = ('study', 'file_name')
        ordering = ['study__file_name', 'file_name']

    def __str__(self):
        return '{}: {}/{}'.format(
            self.get_project().title, self.study.get_name(), self.get_name()
        )

    def __repr__(self):
        values = (
            self.get_project().title,
            self.study.get_name(),
            self.get_name(),
        )
        return 'Assay({})'.format(', '.join(repr(v) for v in values))

    # Custom row-level functions

    def get_name(self):
        """Return simple idenfitying name for assay"""
        return ''.join(str(self.file_name)[2:].split('.')[:-1])

    def get_display_name(self):
        """Return display name for assay"""
        return ' '.join(s for s in self.get_name().split('_')).title()


# Materials and data files -----------------------------------------------------


class NodeMixin:
    """
    Mixin for general row-level GenericMaterial and Process helpers.
    TODO: Eventually should go into a node base class (see issue #922)
    """

    def get_header_idx(self, header_name, header_type=None):
        """
        Return index of a header in headers.

        :param header_name: Header name (string)
        :param header_type: Header type (string, optional)
        :return: Integer or None
        """
        if not header_type or header_type in SPECIAL_FIELD_ATTRS:
            return self.headers.index(header_name)
        return self.headers.index(
            '{}[{}]'.format(ATTR_HEADER_MAP[header_type], header_name)
        )

    def is_ontology_field(self, header_name, header_type=None):
        """
        Return true if an ontology value is expected for a field according to
        the node header.

        :param header_type: Header type (string)
        :param header_name: Header name (string)
        :return: Boolean or None
        """
        idx = self.get_header_idx(header_name, header_type)

        if (
            idx
            and idx <= len(self.headers) - 3
            and self.headers[idx + 1]
            in [th.TERM_SOURCE_REF, th.TERM_ACCESSION_NUMBER]
        ):
            return True

    def has_unit(self, header_name, header_type=None):
        """
        Return true if a unit is expected for a field according to the node
        header.
        :param header_type: Header type (string)
        :param header_name: Header name (string)
        :return: Boolean or None
        """
        idx = self.get_header_idx(header_name, header_type)

        if (
            idx
            and idx <= len(self.headers) - 2
            and self.headers[idx + 1] == th.UNIT
        ):
            return True
        return False

    def has_ontology_unit(self, header_name, header_type=None):
        """
        Return true if an unit ontology reference is expected for a field
        according to the node header.

        :param header_type: Header type (string)
        :param header_name: Header name (string)
        :return: Boolean or None
        """
        idx = self.get_header_idx(header_name, header_type)

        if idx and self.is_ontology_field(header_name, header_type):
            idx += 2

        if (
            idx
            and idx <= len(self.headers) - 4
            and self.headers[idx + 1] == th.UNIT
            and self.headers[idx + 2]
            in [th.TERM_SOURCE_REF, th.TERM_ACCESSION_NUMBER]
        ):
            return True
        return False


class GenericMaterialManager(models.Manager):
    """Manager for custom table-level GenericMaterial queries"""

    def find(self, search_terms, keywords=None, item_types=None):
        """
        Return objects matching the query.

        :param search_terms: Search terms (list of strings)
        :param keywords: Optional search keywords as key/value pairs (dict)
        :param item_types: Restrict to zero or more specific item types (list)
        :return: QuerySet
        """

        # NOTE: Exclude intermediate materials and data files, at least for now
        objects = (
            super().get_queryset().exclude(item_type__in=['DATA', 'MATERIAL'])
        )

        if item_types:
            if not isinstance(item_types, list):
                item_types = [item_types]
            objects = objects.filter(item_type__in=item_types)

        # HACK for ArrayField
        # NOTE: Only look for alt_names as they also contain lowercase name
        # TODO: Why not just use iexact?
        term_query = Q()
        for i in range(0, ALT_NAMES_COUNT):
            for t in search_terms:
                term_query.add(
                    Q(**{'alt_names__{}'.format(i): t.lower()}), Q.OR
                )
        objects = objects.filter(term_query).order_by('name')

        return objects


class GenericMaterial(NodeMixin, BaseSampleSheet):
    """Generic model for materials in the ISA specification. Contains required
    properties for Source, Material, Sample and Data objects"""

    #: Type of item (SOURCE, MATERIAL, SAMPLE, DATA)
    item_type = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        null=False,
        default='MATERIAL',
        choices=GENERIC_MATERIAL_CHOICES,
        help_text='Type of item (SOURCE, MATERIAL, SAMPLE, DATA)',
    )

    #: Material name (common to all item types)
    name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='Material name',
    )

    #: Unique material name
    unique_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Unique material name',
    )

    #: Alternative names to aid lookup
    alt_names = ArrayField(
        models.CharField(max_length=DEFAULT_LENGTH, blank=True),
        default=list,
        db_index=True,
        help_text='Alternative names',
    )

    #: Material characteristics (NOT needed for DataFile)
    characteristics = JSONField(
        default=dict, help_text='Material characteristics'
    )

    #: Study to which the material belongs (for study sequence)
    study = models.ForeignKey(
        Study,
        related_name='materials',
        null=True,
        help_text='Study to which the material belongs (for study sequence)',
    )

    #: Assay to which the material belongs (for assay sequence)
    assay = models.ForeignKey(
        Assay,
        related_name='materials',
        null=True,
        help_text='Assay to which the material belongs (for assay sequence)',
    )

    #: Material type (from "type")
    material_type = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Material type (from "type")',
    )

    #: Extra material type (from "material_type")
    extra_material_type = JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text='Extra material type (from "material_type")',
    )

    #: Factor values for a sample (only for samples)
    factor_values = JSONField(
        default=list,
        blank=True,
        null=True,
        help_text='Factor values for a sample',
    )

    #: Extract label (JSON)
    extract_label = JSONField(
        default=dict, blank=True, null=True, help_text='Extract label'
    )

    # Set manager for custom queries
    objects = GenericMaterialManager()

    class Meta:
        ordering = ['name']
        verbose_name = 'material'
        verbose_name_plural = 'materials'

        indexes = [models.Index(fields=['unique_name'])]

    def __str__(self):
        return '{}: {}/{}/{}/{}'.format(
            self.get_project().title,
            self.get_study().title,
            self.assay.get_name() if self.assay else NOT_AVAILABLE_STR,
            self.item_type,
            self.unique_name,
        )

    def __repr__(self):
        values = (
            self.get_project().title,
            self.get_study().title,
            self.assay.get_name() if self.assay else NOT_AVAILABLE_STR,
            self.item_type,
            self.unique_name,
        )

        return 'GenericMaterial({})'.format(', '.join(repr(v) for v in values))

    # Saving and validation

    def save(self, *args, **kwargs):
        """Override save() to include custom validation functions"""
        self._validate_parent()
        self._validate_item_fields()

        if not self.alt_names:
            self.alt_names = get_alt_names(self.name)

        super().save(*args, **kwargs)

    def _validate_parent(self):
        """Validate the existence of a parent assay or study"""
        if not self.get_parent():
            raise ValidationError('Parent assay or study not set')

    def _validate_item_fields(self):
        """Validate fields related to specific material types"""

        if self.item_type == 'DATA' and self.characteristics:
            raise ValidationError(
                'Field "characteristics" should not be included for a data '
                'file'
            )

        if self.item_type != 'SAMPLE' and self.factor_values:
            raise ValidationError('Factor values included for a non-sample')

    # Custom row-level functions

    def get_parent(self):
        """Return parent assay or study"""
        if self.assay:
            return self.assay

        elif self.study:
            return self.study

        return None  # This should not happen and is caught during validation

    def get_sample_assays(self):
        """If the material is a SAMPLE, return assays where it is used, else
        None"""
        if self.item_type != 'SAMPLE':
            return None

        return Assay.objects.filter(
            study=self.study, arcs__contains=[self.unique_name]
        ).order_by('file_name')

    def get_samples(self):
        """Return samples for the current material"""
        # TODO: Add tests
        # NOTE: Only works for SOURCE type materials for now
        if self.item_type != 'SOURCE':
            return None

        # HACK: Only works if our naming scheme is followed
        return GenericMaterial.objects.filter(
            item_type='SAMPLE',
            study=self.study,
            name__startswith='{}-'.format(self.name),
        )


# Process ----------------------------------------------------------------------


class Process(NodeMixin, BaseSampleSheet):
    """ISA model compatible process"""

    #: Process name (optional)
    name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Process name (optional)',
    )

    #: Unique process name
    unique_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Unique process name',
    )

    #: Type of original name
    name_type = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Type of original name (e.g. Assay Name)',
    )

    #: Protocol which the process executes
    protocol = models.ForeignKey(
        Protocol,
        related_name='processes',
        null=True,  # When under a study, protocol is not needed
        blank=True,
        help_text='Protocol which the process executes',
    )

    #: Study to which the process belongs
    study = models.ForeignKey(
        Study,
        related_name='processes',
        null=True,
        help_text='Study to which the process belongs (for study sequence)',
    )

    #: Assay to which the process belongs (for assay sequence)
    assay = models.ForeignKey(
        Assay,
        related_name='processes',
        null=True,
        help_text='Assay to which the process belongs (for assay sequence)',
    )

    #: Process parameter values
    parameter_values = JSONField(
        default=dict, help_text='Process parameter values'
    )

    #: Process performer (optional)
    performer = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Process performer (optional)',
    )

    #: Process performing date (optional)
    perform_date = models.DateField(
        null=True, help_text='Process performing date (optional)'
    )

    #: Array design ref
    array_design_ref = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Array design ref',
    )

    #: First dimension
    first_dimension = JSONField(
        default=dict, help_text='First dimension (optional, for special case)'
    )

    #: Second dimension
    second_dimension = JSONField(
        default=dict, help_text='Second dimension (optional, for special case)'
    )

    class Meta:
        verbose_name_plural = 'processes'
        indexes = [models.Index(fields=['unique_name'])]

    def __str__(self):
        return '{}: {}/{}/{}'.format(
            self.get_project().title,
            self.get_study().get_name(),
            self.assay.get_name() if self.assay else NOT_AVAILABLE_STR,
            self.unique_name,
        )

    def __repr__(self):
        values = (
            self.get_project().title,
            self.get_study().get_name(),
            self.assay.get_name() if self.assay else NOT_AVAILABLE_STR,
            self.unique_name,
        )
        return 'Process({})'.format(', '.join(repr(v) for v in values))

    # Saving and validation

    def save(self, *args, **kwargs):
        """Override save() to include custom validation functions"""
        self._validate_parent()
        super().save(*args, **kwargs)

    def _validate_parent(self):
        """Validate the existence of a parent assay or study"""
        if not self.get_parent():
            raise ValidationError('Parent assay or study not set')

    # Custom row-level functions

    def get_parent(self):
        """Return parent assay or study"""
        if self.assay:
            return self.assay

        elif self.study:
            return self.study


# ISAtab File Saving -----------------------------------------------------------


class ISATab(models.Model):
    """Class for storing ISAtab files for one investigation, including its
    studies and assays"""

    #: Project to which the ISAtab belongs
    project = models.ForeignKey(
        Project,
        null=False,
        related_name='isatabs',
        help_text='Project to which the ISAtab belongs',
    )

    #: UUID of related Investigation object
    investigation_uuid = models.UUIDField(
        null=True,
        blank=True,
        unique=False,
        help_text='UUID of related Investigation',
    )
    # NOTE: No ForeignKey because the investigations may have been deleted

    #: File name of ISAtab archive (optional)
    archive_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='File name of ISAtab archive (optional)',
    )

    #: Data from ISAtab files as a dict
    data = JSONField(default=dict, help_text='Data from ISAtab files as a dict')

    #: Tags for categorizing the ISAtab
    tags = ArrayField(
        models.CharField(max_length=DEFAULT_LENGTH, blank=True),
        default=list,
        help_text='Tags for categorizing the ISAtab',
    )

    #: User saving of this ISAtab (optional)
    user = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='isatabs',
        null=True,
        help_text='User saving this ISAtab (optional)',
    )

    #: DateTime of ISAtab creation
    date_created = models.DateTimeField(
        auto_now=True, help_text='DateTime of ISAtab creation'
    )

    #: Version of altamISA used when processing this ISAtab
    parser_version = models.CharField(
        max_length=DEFAULT_LENGTH,
        blank=True,
        null=True,
        help_text='Version of altamISA used when processing this ISAtab',
    )

    #: Optional extra data
    extra_data = JSONField(default=dict, help_text='Optional extra data')

    #: Internal UUID for the object
    sodar_uuid = models.UUIDField(
        default=uuid.uuid4, unique=True, help_text='SODAR UUID for the object'
    )

    def __str__(self):
        return '{}: {} ({})'.format(
            self.project.title, self.archive_name, self.date_created
        )

    def __repr__(self):
        values = (self.project.title, self.archive_name, self.date_created)
        return 'ISATab({})'.format(', '.join(repr(v) for v in values))

    # Custom row-level functions

    def get_name(self):
        investigation = Investigation.objects.filter(
            sodar_uuid=self.investigation_uuid
        ).first()

        if investigation and investigation.title:
            name = investigation.title

        elif self.archive_name:
            name = self.archive_name.split('.')[0]

        else:
            name = self.project.title

        return name + ' ({})'.format(
            localtime(self.date_created).strftime('%Y-%m-%d %H:%M:%S')
        )


class IrodsAccessTicketActiveManager(models.Manager):
    """
    Manager to return only tickets that are not expired.
    """

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(Q(date_expires__gt=timezone.now()) | Q(date_expires=None))
        )


class IrodsAccessTicket(models.Model):
    """
    Model for managing tickets in irods
    """

    class Meta:
        ordering = ['-date_created']

    objects = models.Manager()
    active_objects = IrodsAccessTicketActiveManager()

    #: Internal UUID for the object
    sodar_uuid = models.UUIDField(
        default=uuid.uuid4, unique=True, help_text='SODAR UUID for the object'
    )

    #: Project the ticket belongs to
    project = models.ForeignKey(
        Project,
        related_name='irods_access_ticket',
        help_text='Project the ticket belongs to',
    )

    #: Study the ticket belongs to
    study = models.ForeignKey(
        Study,
        related_name='irods_access_ticket',
        help_text='Study the ticket belongs to',
    )

    #: Assay the ticket belongs to (optional)
    assay = models.ForeignKey(
        Assay,
        related_name='irods_access_ticket',
        null=True,
        blank=True,
        help_text='Assay the ticket belongs to (optional)',
    )

    #: Ticket token
    ticket = models.CharField(
        max_length=DEFAULT_LENGTH, help_text='Ticket token'
    )

    #: Path
    path = models.CharField(
        max_length=DEFAULT_LENGTH, help_text='Path to iRODS collection'
    )

    #: Label for ticket (optional)
    label = models.CharField(
        max_length=DEFAULT_LENGTH,
        null=True,
        blank=True,
        help_text='Ticket label (optional)',
    )

    #: User that created the ticket
    user = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='irods_access_ticket',
        null=True,
        help_text='User that created the ticket',
    )

    #: Date created
    date_created = models.DateTimeField(
        auto_now_add=True, help_text='DateTime of ticket creation'
    )

    #: Date ticket expires
    date_expires = models.DateTimeField(
        null=True,
        blank=True,
        help_text='DateTime of ticket expiration (leave unset to never '
        'expire; click x on righthand-side of field to unset)',
    )

    def get_track_hub_name(self):
        return os.path.basename(self.path)

    def get_date_created(self):
        return localtime(self.date_created).strftime('%Y-%m-%d %H:%M')

    def get_date_expires(self):
        if self.date_expires:
            return localtime(self.date_expires).strftime('%Y-%m-%d')
        return None

    def get_label(self):
        return self.label or self.get_date_created()

    def get_display_name(self):
        assay_name = ''
        if (
            Assay.objects.filter(
                study__investigation__project=self.project
            ).count()
            > 1
        ):
            assay_name = '{} / '.format(self.assay.get_display_name())
        return '{}{} / {}'.format(
            assay_name, self.get_track_hub_name(), self.get_label()
        )

    def get_webdav_link(self):
        return settings.IRODS_WEBDAV_URL_ANON_TMPL.format(
            user=settings.IRODS_WEBDAV_USER_ANON,
            ticket=self.ticket,
            path=self.path,
        )

    def is_active(self):
        return self.date_expires is None or self.date_expires >= timezone.now()

    def __str__(self):
        return '{} / {} / {} / {}'.format(
            self.project.title,
            self.assay.get_display_name(),
            self.get_track_hub_name(),
            self.get_label(),
        )

    def __repr__(self):
        values = (
            self.project.title,
            self.assay.get_display_name(),
            self.get_track_hub_name(),
            self.get_label(),
        )
        return 'IrodsAccessTicket({})'.format(
            ', '.join(repr(v) for v in values)
        )
