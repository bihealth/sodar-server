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

    #: ISA API object id
    api_id = models.CharField(
        max_length=DEFAULT_LENGTH,
        blank=True,
        null=True,
        help_text='ISA API object id')

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

    #: Comments
    comments = JSONField(
        default=dict,
        help_text='Comments')

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

    #: Comments
    comments = JSONField(
        default=dict,
        help_text='Comments')

    class Meta:
        ordering = ['identifier']
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

    # Custom row-level functions

    def get_characteristic_cat(self, characteristic):
        """Return characteristic category"""
        for c in self.characteristic_cat:
            if c['@id'] == characteristic['category']['@id']:
                return c['characteristicType']

    def get_unit_cat(self, unit):
        """Return unit category"""
        for c in self.unit_cat:
            if c['@id'] == unit['@id']:
                return c

    def get_factor(self, factor_value):
        """Return factor definition"""
        for f in self.factors:
            if f['@id'] == factor_value['category']['@id']:
                return f


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

    # Custom row-level functions

    def get_parameter(self, parameter_value):
        """Return parameter definition"""
        for p in self.parameters:
            if p['parameterName']['@id'] == parameter_value['category']['@id']:
                return p


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

    #: Comments
    comments = JSONField(
        default=dict,
        help_text='Comments')

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

    # Custom row-level functions

    def get_samples(self):
        """Return assay samples"""
        return GenericMaterial.objects.filter(
            item_type='SAMPLE', material_targets__assay=self).distinct()

    def get_sources(self):
        """Return sources of samples used in this assay as a list"""
        sources = []

        for sample in self.get_samples():
            sources += sample.get_sources()

        return sorted(set(sources), key=lambda x: x.name)

    def get_sequences_by_sample(self, sample):
        """
        Return process sequences which take sample as initial input
        :param sample: GenericMaterial object of type "SAMPLE"
        :return: QuerySet of Process objects (first process of each sequence)
        :raise: ValueError if input GenericMaterial is not of type "SAMPLE"
        """
        if sample.item_type != 'SAMPLE':
            raise ValueError('Input is not a sample')

        return Process.objects.filter(
            assay=self, previous_process=None, inputs=sample)


# Materials and data files -----------------------------------------------------


class GenericMaterialManager(models.Manager):
    """Manager for custom table-level GenericMaterial queries"""

    def find_child(self, parent, api_id):
        """Find child material of a parent with a specific api_id"""
        parent_query_arg = parent.__class__.__name__.lower()
        study = parent if type(parent) == Study else parent.study

        try:
            return super(GenericMaterialManager, self).get_queryset().get(
                **{parent_query_arg: parent, 'api_id': api_id})

        except GenericMaterial.DoesNotExist:  # Sample, get from study
            return super(GenericMaterialManager, self).get_queryset().get(
                study=study, api_id=api_id)


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
        help_text='Factor values for a sample')

    # Set manager for custom queries
    objects = GenericMaterialManager()

    class Meta:
        ordering = ['name']
        verbose_name = 'material'
        verbose_name_plural = 'materials'

    def __str__(self):
        if self.assay:
            return '{}/{}/{}/{}'.format(
                self.item_type,
                self.assay.study.investigation.title,
                self.assay.study.identifier,
                self.assay.file_name,
                self.name)

        elif self.study:
            return '{}/{}/{}'.format(
                self.item_type,
                self.study.investigation.title,
                self.study.identifier,
                self.name)

        else:
            return '{}/{}'.format(self.item_type, self.name)

    def __repr__(self):
        if self.assay:
            values = (
                self.item_type,
                self.assay.study.investigation.title,
                self.assay.study.identifier,
                self.assay.file_name,
                self.name)

        elif self.study:
            values = (
                self.item_type,
                self.study.investigation.title,
                self.study.identifier,
                self.name)

        else:
            values = (
                self.item_type,
                self.name)

        return 'GenericMaterial({})'.format(', '.join(repr(v) for v in values))

    # Saving and validation

    def save(self, *args, **kwargs):
        """Override save() to include custom validation functions"""
        self._validate_parent()
        self._validate_api_id()
        self._validate_item_fields()
        super(GenericMaterial, self).save(*args, **kwargs)

    def _validate_parent(self):
        """Validate the existence of a parent assay or study"""
        if not self.get_parent():
            raise ValidationError('Parent assay or study not set')

    def _validate_api_id(self):
        """Validate api_id uniqueness within parent"""
        if (GenericMaterial.objects.filter(
                study=self.study,
                assay=self.assay,
                api_id=self.api_id).count() != 0):
            raise ValidationError(
                'Material id "{}" not unique within parent'.format(
                    self.api_id))

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

    # Custom row-level functions

    def get_parent(self):
        """Return parent assay or study"""
        if self.assay:
            return self.assay

        elif self.study:
            return self.study

        return None  # This should not happen and is caught during validation

    def get_sources(self):
        """Return sources of material as a list"""

        def find_sources(material, sources):
            if material.item_type == 'SOURCE':
                sources.append(material)

            elif hasattr(material, 'material_sources'):
                for source_process in material.material_sources.all():
                    for input_material in source_process.inputs.all():
                        if input_material.item_type == 'SOURCE':
                            sources.append(input_material)

                        else:
                            sources += find_sources(input_material, sources)

            return set(sources)

        sources = find_sources(self, [])
        return sorted(sources, key=lambda x: x.name)


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

    #: Previous process (can be None for first process in sequence)
    previous_process = models.ForeignKey(
        'Process',
        related_name='next',
        null=True,
        help_text='Previous process (can be None for first process in '
                  'sequence)')

    #: Next process (can be None for the last process in sequence)
    next_process = models.ForeignKey(
        'Process',
        related_name='previous',
        null=True,
        help_text='Next process (can be None for the last process in sequence)')

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
            self.protocol.study.api_id,
            self.protocol.api_id,
            self.api_id)

    def __repr__(self):
        values = (
            self.protocol.study.investigation.title,
            self.protocol.study.api_id,
            self.protocol.api_id,
            self.api_id)
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

    def get_next_process(self):
        """Return next process or None if it doesn't exist"""
        return self.next_process if (
            hasattr(self, 'next_process') and
            self.next_process) else None

    def get_parent(self):
        """Return parent assay or study"""
        if self.assay:
            return self.assay

        elif self.study:
            return self.study

        return None  # This should not happen and is caught during validation
