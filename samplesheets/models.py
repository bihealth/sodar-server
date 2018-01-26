import uuid

from django.contrib.postgres.fields import JSONField
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

    #: Ontology source references
    ontology_source_refs = JSONField(
        default=dict,
        help_text='Ontology source references')

    #: Comments
    comments = JSONField(
        default=dict,
        help_text='Comments')

    def __str__(self):
        return '{}: {}'.format(
            self.project.title,
            self.identifier)

    def __repr__(self):
        values = (
            self.project.title,
            self.identifier)
        return 'Investigation({})'.format(', '.join(repr(v) for v in values))


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

    #: Title of the study
    title = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='Title of the study')

    #: Study description
    description = models.TextField(
        unique=False,
        blank=True,
        help_text='Study description')

    #: Study design descriptors
    study_design = JSONField(
        default=dict,
        help_text='Study design descriptors')

    #: Study factors
    factors = JSONField(
        default=dict,
        help_text='Study factors')

    #: First process in the process sequence
    first_process = models.ForeignKey(
        'Process',
        related_name='study',
        null=True,  # This may be created before we have a process
        help_text='First process in the process sequence')

    class Meta:
        unique_together = ('investigation', 'identifier', 'title')

    def __str__(self):
        return '{}/{}'.format(
            self.investigation.identifier,
            self.identifier)

    def __repr__(self):
        values = (
            self.investigation.identifier,
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
            self.study.investigation.identifier,
            self.study.identifier,
            self.name)

    def __repr__(self):
        values = (
            self.study.investigation.identifier,
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
            self.study.investigation.identifier,
            self.study.identifier,
            self.file_name)

    def __repr__(self):
        values = (
            self.study.investigation.identifier,
            self.study.identifier,
            self.file_name)
        return 'Assay({})'.format(', '.join(repr(v) for v in values))


# Materials and data files -----------------------------------------------------


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

    #: Study to which the item belongs (optional, for sample collection)
    study = models.ForeignKey(
        Study,
        related_name='materials',
        null=True,
        help_text='Study to which the material belongs (optional)')

    #: Assay to which the material belongs (optional, for assay sequence)
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
        default=dict,
        help_text='Factor values for a sample')

    class Meta:
        pass    # TODO: Implement unique_together in validation functions

    def __str__(self):
        if hasattr(self, 'study'):
            return '{}/{}/{}'.format(
                self.study.investigation.identifier,
                self.study.identifier,
                self.name)
        else:
            return '{}/{}/{}/{}'.format(
                self.assay.study.investigation.identifier,
                self.assay.study.identifier,
                self.assay.file_name,
                self.name)

    def __repr__(self):
        if hasattr(self, 'study'):
            values = (
                self.study.investigation.identifier,
                self.study.identifier,
                self.name)

        else:
            values = (
                self.assay.study.investigation.identifier,
                self.assay.study.identifier,
                self.assay.file_name,
                self.name)
        return 'Process({})'.format(', '.join(repr(v) for v in values))


# Process ----------------------------------------------------------------------


class Process(BaseSampleSheet):
    """ISA model compatible process"""

    #: Process name
    name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        null=False,
        help_text='Process name')

    #: Protocol which the process executes
    protocol = models.ForeignKey(
        Protocol,
        related_name='processes',
        null=True,  # When under a study, protocol is not needed
        blank=True,
        help_text='Protocol which the process executes')

    #: Previous process (can be None for first process in sequence)
    previous_process = models.ForeignKey(
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
        unique_together = ('protocol', 'name')

    def __str__(self):
        if hasattr(self, 'study'):
            return '{}/{}/{}'.format(
                self.study.investigation.identifier,
                self.study.identifier,
                self.name)
        else:
            return '{}/{}/{}/{}'.format(
                self.assay.study.investigation.identifier,
                self.assay.study.identifier,
                self.assay.file_name,
                self.name)

    def __repr__(self):
        if hasattr(self, 'study'):
            values = (
                self.study.investigation.identifier,
                self.study.identifier,
                self.name)

        else:
            values = (
                self.assay.study.investigation.identifier,
                self.assay.study.identifier,
                self.assay.file_name,
                self.name)
        return 'Process({})'.format(', '.join(repr(v) for v in values))
