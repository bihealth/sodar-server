import uuid

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models

# Projectroles dependency
from projectroles.models import Project


# Local constants
DEFAULT_LENGTH = 255

GENERIC_MATERIAL_CHOICES = [
    ('SOURCE', 'Source'),
    ('MATERIAL', 'Material'),
    ('SAMPLE', 'Sample'),
    ('DATA', 'Data')]


# Abstract base class ----------------------------------------------------------


class BaseSampleSheet(models.Model):
    """Abstract class with common ODM sample sheet properties"""

    #: JSON @id value
    json_id = models.CharField(
        max_length=DEFAULT_LENGTH,
        blank=True,
        null=True,
        help_text='JSON @id value')

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

    class Meta:
        abstract = True


# Investigation ----------------------------------------------------------------


class Investigation(BaseSampleSheet):
    """ISA model compatible investigation"""

    #: Locally unique identifier
    identifier = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=True,
        blank=False,
        help_text='Locally unique identifier')

    #: File name for exporting
    file_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=True,
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

    #: Comments
    comments = JSONField(
        default=dict,
        help_text='Comments')

    def __str__(self):
        return self.title

    def __repr__(self):
        return 'Investigation({})'.format(self.title)


# Study ------------------------------------------------------------------------


class Study(BaseSampleSheet):
    """ISA model compatible study"""

    #: Locally unique identifier
    identifier = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=True,
        blank=False,
        help_text='Locally unique identifier')

    #: File name for exporting
    file_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=True,
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

    #: Comments
    comments = JSONField(
        default=dict,
        help_text='Comments')

    #: First process in the process sequence
    first_process = models.ForeignKey(
        'Process',
        related_name='study',
        null=True,  # This may be created before we have a process
        help_text='First process in the process sequence')

    class Meta:
        unique_together = ('investigation', 'identifier', 'title')
        verbose_name_plural = 'studies'

    def __str__(self):
        return '{}/{}'.format(
            self.investigation.title,
            self.identifier)

    def __repr__(self):
        values = (
            self.investigation.title,
            self.identifier)
        return 'Study({})'.format(', '.join(repr(v) for v in values))


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
        default=dict,
        help_text='Protocol type')

    #: Protocol description
    description = models.TextField(
        unique=False,
        blank=True,
        help_text='Protocol description')

    #: Protocol URI
    uri = models.URLField(
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
        return '{}/{}/{}'.format(
            self.study.investigation.title,
            self.study.identifier,
            self.name)

    def __repr__(self):
        values = (
            self.study.investigation.title,
            self.study.identifier,
            self.name)
        return 'Protocol({})'.format(', '.join(repr(v) for v in values))


# Assay ------------------------------------------------------------------------


class Assay(BaseSampleSheet):
    """ISA model compatible assay"""

    #: File name for exporting
    file_name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=True,
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

    #: Comments
    comments = JSONField(
        default=dict,
        help_text='Comments')

    #: First process in the process sequence
    first_process = models.ForeignKey(
        'Process',
        related_name='assay',
        null=True,  # This may be created before we have a process
        help_text='First process in the process sequence')

    class Meta:
        unique_together = ('study', 'file_name')

    def __str__(self):
        return '{}/{}/{}'.format(
            self.study.investigation.title,
            self.study.identifier,
            self.file_name)

    def __repr__(self):
        values = (
            self.study.investigation.title,
            self.study.identifier,
            self.file_name)
        return 'Assay({})'.format(', '.join(repr(v) for v in values))


# Materials and data files -----------------------------------------------------


class GenericMaterialManager(models.Manager):
    """Manager for custom table-level GenericMaterial queries"""

    def find_child(self, parent, json_id):
        """Find child material of a parent with a specific json_id"""
        parent_query_arg = parent.__class__.__name__.lower()
        study = parent if type(parent) == Study else parent.study

        try:
            return super(GenericMaterialManager, self).get_queryset().get(
                **{parent_query_arg: parent, 'json_id': json_id})

        except GenericMaterial.DoesNotExist:  # Sample, get from study
            return super(GenericMaterialManager, self).get_queryset().get(
                study=study, json_id=json_id)


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

    #: Material characteristics (NOT needed for DataFile)
    characteristics = JSONField(
        default=dict,
        help_text='Material characteristics')

    #: Study to which the material belongs (for study sequence)
    study = models.ForeignKey(
        Study,
        related_name='materials',
        null=True,
        help_text='Study to which the material belongs')

    #: Assay to which the material belongs (for assay sequence)
    assay = models.ForeignKey(
        Assay,
        related_name='materials',
        null=True,
        help_text='Assay to which the material belongs (optional)')

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
        help_text='Factor values for a sample')

    # Set manager for custom queries
    objects = GenericMaterialManager()

    class Meta:
        verbose_name = 'material'
        verbose_name_plural = 'materials'

    def __str__(self):
        if self.assay:
            return '{}/{}/{}/{}'.format(
                self.assay.study.investigation.title,
                self.assay.study.identifier,
                self.assay.file_name,
                self.name)

        elif self.study:
            return '{}/{}/{}'.format(
                self.study.investigation.title,
                self.study.identifier,
                self.name)

        else:
            return self.name

    def __repr__(self):
        if self.assay:
            values = (
                self.assay.study.investigation.title,
                self.assay.study.identifier,
                self.assay.file_name,
                self.name)

        elif self.study:
            values = (
                self.study.investigation.title,
                self.study.identifier,
                self.name)

        else:
            values = (
                self.name)

        return 'GenericMaterial({})'.format(', '.join(repr(v) for v in values))

    def save(self, *args, **kwargs):
        """Override save() to include custom validation functions"""
        self._validate_parent()
        self._validate_item_fields()
        super(GenericMaterial, self).save(*args, **kwargs)

    def _validate_parent(self):
        """Validate existence of a parent study/assay"""
        if not self.study and not self.assay:
            raise ValidationError(
                'Material must provide either a parent study or assay')

    def _validate_item_fields(self):
        """Validate fields related to specific material types"""

        if self.item_type == 'DATA' and self.characteristics:
            raise ValidationError(
                'Field "characteristics" should not be included for a data '
                'file')

        if self.item_type in ['DATA', 'MATERIAL'] and not self.material_type:
            raise ValidationError('Type of material missing')

        if self.item_type != 'SAMPLE' and self.factor_values:
            raise ValidationError('Factor values included for a non-sample')


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

    #: Protocol which the process executes
    protocol = models.ForeignKey(
        Protocol,
        related_name='processes',
        null=True,  # When under a study, protocol is not needed
        blank=True,
        help_text='Protocol which the process executes')

    #: Previous process (can be None for first process in sequence)
    previous_process = models.OneToOneField(
        'Process',
        related_name='next_process',
        null=True,
        help_text='Previous process (can be None for first process in '
                  'sequence)')

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

    #: Comments
    comments = JSONField(
        default=dict,
        help_text='Comments')

    #: Material and data file inputs
    inputs = models.ManyToManyField(
        GenericMaterial,
        related_name='material_targets',
        help_text='Material and data file inputs')

    #: Material inputs
    outputs = models.ManyToManyField(
        GenericMaterial,
        related_name='material_sources',
        help_text='Material and data file outputs')

    class Meta:
        verbose_name_plural = 'processes'

    def __str__(self):
        return '{}/{}/{}/{}'.format(
            self.protocol.study.investigation.title,
            self.protocol.study.json_id,
            self.protocol.json_id,
            self.json_id)

    def __repr__(self):
        values = (
            self.protocol.study.investigation.title,
            self.protocol.study.json_id,
            self.protocol.json_id,
            self.json_id)
        return 'Process({})'.format(', '.join(repr(v) for v in values))
