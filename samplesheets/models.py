import uuid

from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField, JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

# Projectroles dependency
from projectroles.models import Project


# Local constants
DEFAULT_LENGTH = 255

GENERIC_MATERIAL_TYPES = {
    'SOURCE': 'Source',
    'MATERIAL': 'Material',
    'SAMPLE': 'Sample',
    'DATA': 'Data File'}

GENERIC_MATERIAL_CHOICES = [(k, v) for k, v in GENERIC_MATERIAL_TYPES.items()]
NOT_AVAILABLE_STR = '(N/A)'


# Abstract base class ----------------------------------------------------------


class BaseSampleSheet(models.Model):
    """Abstract class with common ODM sample sheet properties"""

    #: Internal UUID for the object
    omics_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text='Internal UUID for the object')

    #: Data sharing rules
    sharing_data = JSONField(
        default=dict,
        help_text='Data sharing rules')

    #: Consent retraction data
    retraction_data = JSONField(
        default=dict,
        help_text='Consent retraction data')

    #: Comments
    comments = JSONField(
        default=dict,
        help_text='Comments')

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
        help_text='Locally unique identifier')

    #: File name for exporting
    file_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='File name for exporting')

    #: Project to which the investigation belongs
    project = models.ForeignKey(
        Project,
        null=False,
        related_name='investigations',
        help_text='Project to which the investigation belongs')

    #: Investigation title (optional, can be derived from project)
    title = models.CharField(
        max_length=DEFAULT_LENGTH,
        blank=True,
        null=True,
        help_text='Title (optional, can be derived from project)')

    #: Investigation description (optional, can be derived from project)
    description = models.TextField(
        blank=True,
        null=True,
        help_text='Investigation description (optional, can be derived from '
                  'project)')

    #: Ontology source references
    ontology_source_refs = JSONField(
        default=dict,
        help_text='Ontology source references')

    #: Status of iRODS directory structure creation
    irods_status = models.BooleanField(
        default=False,
        help_text='Status of iRODS directory structure creation')

    def __str__(self):
        return '{}: {}'.format(self.project.title, self.title)

    def __repr__(self):
        values = (
            self.project.title,
            self.title)
        return 'Investigation({})'.format(', '.join(repr(v) for v in values))


# Study ------------------------------------------------------------------------


class Study(BaseSampleSheet):
    """ISA model compatible study"""

    #: Locally unique identifier
    identifier = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='Locally unique identifier')

    #: File name for exporting
    file_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='File name for exporting')

    #: Investigation to which the study belongs
    investigation = models.ForeignKey(
        Investigation,
        null=False,
        related_name='studies',
        help_text='Investigation to which the study belongs')

    #: Title of the study (optional)
    title = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        help_text='Title of the study (optional)')

    #: Study description (optional)
    description = models.TextField(
        unique=False,
        blank=True,
        help_text='Study description (optional)')

    #: Study design descriptors
    study_design = JSONField(
        default=dict,
        help_text='Study design descriptors')

    #: Study factors
    factors = JSONField(
        default=dict,
        help_text='Study factors')

    #: Characteristic categories
    characteristic_cat = JSONField(
        default=dict,
        help_text='Characteristic categories')

    #: Unit categories
    unit_cat = JSONField(
        default=dict,
        help_text='Unit categories')

    #: Study arcs
    arcs = ArrayField(
        ArrayField(
            models.CharField(max_length=DEFAULT_LENGTH, blank=True)),
        default=list,
        help_text='Study arcs')

    #: Column headers
    header = JSONField(
        default=dict,
        help_text='Column headers')

    class Meta:
        ordering = ['identifier']
        unique_together = ('investigation', 'identifier', 'title')
        verbose_name_plural = 'studies'

    def __str__(self):
        return '{}: {}'.format(
            self.get_project().title,
            self.get_name())

    def __repr__(self):
        values = (
            self.get_project().title,
            self.get_name())
        return 'Study({})'.format(', '.join(repr(v) for v in values))

    # Custom row-level functions

    def get_name(self):
        """Return simple printable name for study"""
        return self.title if self.title else self.identifier

    def get_dir(self):
        """Return directory name for study"""
        return 'study_' + str(self.omics_uuid)


# Protocol ---------------------------------------------------------------------


class Protocol(BaseSampleSheet):
    """ISA model compatible protocol"""

    #: Protocol name
    name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='Protocol name')

    #: Study to which the protocol belongs
    study = models.ForeignKey(
        Study,
        related_name='protocols',
        help_text='Study to which the protocol belongs')

    #: Protocol type
    protocol_type = JSONField(
        null=True,
        default=dict,
        help_text='Protocol type')

    #: Protocol description
    description = models.TextField(
        unique=False,
        blank=True,
        help_text='Protocol description')

    #: Protocol URI
    uri = models.CharField(
        max_length=2048,
        unique=False,
        help_text='Protocol URI')

    #: Protocol version
    version = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        help_text='Protocol version')

    #: Protocol parameters
    parameters = JSONField(
        default=dict,
        help_text='Protocol parameters')

    #: Protocol components
    components = JSONField(
        default=dict,
        help_text='Protocol components')

    class Meta:
        unique_together = ('study', 'name')

    def __str__(self):
        return '{}: {}/{}'.format(
            self.get_project().title,
            self.study.get_name(),
            self.name)

    def __repr__(self):
        values = (
            self.get_project().title,
            self.study.get_name(),
            self.name)
        return 'Protocol({})'.format(', '.join(repr(v) for v in values))


# Assay ------------------------------------------------------------------------


class Assay(BaseSampleSheet):
    """ISA model compatible assay"""

    #: File name for exporting
    file_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='File name for exporting')

    #: Study to which the assay belongs
    study = models.ForeignKey(
        Study,
        related_name='assays',
        help_text='Study to which the assay belongs')

    #: Technology platform (optional)
    technology_platform = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Technology platform (optional)')

    #: Technology type
    technology_type = JSONField(
        default=dict,
        help_text='Technology type')

    #: Measurement type
    measurement_type = JSONField(
        default=dict,
        help_text='Measurement type')

    #: Characteristic categories
    characteristic_cat = JSONField(
        default=dict,
        help_text='Characteristic categories')

    #: Unit categories
    unit_cat = JSONField(
        default=dict,
        help_text='Unit categories')

    #: Assay arcs
    arcs = ArrayField(
        ArrayField(
            models.CharField(max_length=DEFAULT_LENGTH, blank=True)),
        default=list,
        help_text='Assay arcs')

    #: Column headers
    header = JSONField(
        default=dict,
        help_text='Column headers')

    class Meta:
        unique_together = ('study', 'file_name')

    def __str__(self):
        return '{}: {}/{}'.format(
            self.get_project().title,
            self.study.get_name(),
            self.get_name())

    def __repr__(self):
        values = (
            self.get_project().title,
            self.study.get_name(),
            self.get_name())
        return 'Assay({})'.format(', '.join(repr(v) for v in values))

    # Custom row-level functions

    def get_name(self):
        """Return simple idenfitying name for Assay"""
        return ''.join(str(self.file_name)[2:].split('.')[:-1])

    def get_dir(self, include_study=False):
        """
        Return directory name for assay
        :param include_study: Include parent study directory in string (bool)
        :return: String
        """

        return '{}assay_{}'.format(
            (self.study.get_dir() + '/') if include_study else '',
            self.omics_uuid)


# Materials and data files -----------------------------------------------------


class GenericMaterialManager(models.Manager):
    """Manager for custom table-level GenericMaterial queries"""

    def find(self, search_term, keywords=None, item_type=None):
        """
        Return objects matching the query.
        :param search_term: Search term (string)
        :param keywords: Optional search keywords as key/value pairs (dict)
        :param item_type: Restrict to a specific item_type
        :return: Python list of GenericMaterial objects
        """

        # NOTE: Exlude intermediate materials, at least for now
        objects = super(
            GenericMaterialManager, self).get_queryset().exclude(
            item_type='MATERIAL').order_by('name')

        objects = objects.filter(
            Q(name__icontains=search_term))     # TODO: TBD: Other fields?

        if item_type:
            objects = objects.filter(item_type=item_type)

        return objects


class GenericMaterial(BaseSampleSheet):
    """Generic model for materials in the ISA specification. Contains required
    properties for Source, Material, Sample and Data objects"""

    #: Type of item (Source, Material, Sample, Data)
    item_type = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        null=False,
        default='MATERIAL',
        choices=GENERIC_MATERIAL_CHOICES,
        help_text='')

    #: Material name (common to all item types)
    name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='Material name')

    #: Unique material name
    unique_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Unique material name')

    #: Material characteristics (NOT needed for DataFile)
    characteristics = JSONField(
        default=dict,
        help_text='Material characteristics')

    #: Study to which the material belongs (for study sequence)
    study = models.ForeignKey(
        Study,
        related_name='materials',
        null=True,
        help_text='Study to which the material belongs (for study sequence)')

    #: Assay to which the material belongs (for assay sequence)
    assay = models.ForeignKey(
        Assay,
        related_name='materials',
        null=True,
        help_text='Assay to which the material belongs (for assay sequence)')

    #: Material or data field type (only for materials and data files)
    material_type = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Material or data file type')

    #: Factor values for a sample (only for samples)
    factor_values = JSONField(
        default=list,
        blank=True,
        null=True,
        help_text='Factor values for a sample')

    #: Extract label
    extract_label = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Extract label')

    # Set manager for custom queries
    objects = GenericMaterialManager()

    class Meta:
        ordering = ['name']
        verbose_name = 'material'
        verbose_name_plural = 'materials'

        indexes = [
            models.Index(fields=['unique_name']),
            models.Index(fields=['study'])]

    def __str__(self):
        return '{}: {}/{}/{}/{}'.format(
            self.get_project().title,
            self.get_study().title,
            self.assay.get_name() if self.assay else NOT_AVAILABLE_STR,
            self.item_type,
            self.unique_name)

    def __repr__(self):
        values = (
            self.get_project().title,
            self.get_study().title,
            self.assay.get_name() if self.assay else NOT_AVAILABLE_STR,
            self.item_type,
            self.unique_name)

        return 'GenericMaterial({})'.format(', '.join(repr(v) for v in values))

    # Saving and validation

    def save(self, *args, **kwargs):
        """Override save() to include custom validation functions"""
        self._validate_parent()
        self._validate_item_fields()
        super(GenericMaterial, self).save(*args, **kwargs)

    def _validate_parent(self):
        """Validate the existence of a parent assay or study"""
        if not self.get_parent():
            raise ValidationError('Parent assay or study not set')

    def _validate_item_fields(self):
        """Validate fields related to specific material types"""

        if self.item_type == 'DATA' and self.characteristics:
            raise ValidationError(
                'Field "characteristics" should not be included for a data '
                'file')

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


# Process ----------------------------------------------------------------------


class Process(BaseSampleSheet):
    """ISA model compatible process"""

    #: Process name (optional)
    name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Process name (optional)')

    #: Unique process name
    unique_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Unique process name')

    #: Protocol which the process executes
    protocol = models.ForeignKey(
        Protocol,
        related_name='processes',
        null=True,  # When under a study, protocol is not needed
        blank=True,
        help_text='Protocol which the process executes')

    #: Study to which the process belongs
    study = models.ForeignKey(
        Study,
        related_name='processes',
        null=True,
        help_text='Study to which the process belongs (for study sequence)')

    #: Assay to which the process belongs (for assay sequence)
    assay = models.ForeignKey(
        Assay,
        related_name='processes',
        null=True,
        help_text='Assay to which the process belongs (for assay sequence)')

    #: Process parameter values
    parameter_values = JSONField(
        default=dict,
        help_text='Process parameter values')

    #: Process performer (optional)
    performer = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Process performer (optional)')

    #: Process performing date (optional)
    perform_date = models.DateField(
        null=True,
        help_text='Process performing date (optional)')

    #: Array design ref
    array_design_ref = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Array design ref')

    #: Scan name for special cases in ISAtab
    scan_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Scan name for special cases in ISAtab')

    class Meta:
        verbose_name_plural = 'processes'
        indexes = [
            models.Index(fields=['unique_name']),
            models.Index(fields=['study'])]

    def __str__(self):
        return '{}: {}/{}/{}'.format(
            self.get_project().title,
            self.get_study().get_name(),
            self.assay.get_name() if self.assay else NOT_AVAILABLE_STR,
            self.unique_name)

    def __repr__(self):
        values = (
            self.get_project().title,
            self.get_study().get_name(),
            self.assay.get_name() if self.assay else NOT_AVAILABLE_STR,
            self.unique_name)
        return 'Process({})'.format(', '.join(repr(v) for v in values))

    # Saving and validation

    def save(self, *args, **kwargs):
        """Override save() to include custom validation functions"""
        self._validate_parent()
        super(Process, self).save(*args, **kwargs)

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
