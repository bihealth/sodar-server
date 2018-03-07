import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
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

ARC_OBJ_SUFFIX_MAP = {
    'GenericMaterial': 'material',
    'Process': 'process'}

INVESTIGATION_STATUS_TYPES = [
    'OK',
    'IMPORTING',
    'RENDERING',
    'FAILED']


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

    # Custom row-level functions
    def get_study(self):
        """Return associated study if it exists"""
        if hasattr(self, 'assay') and self.assay:
            return self.assay.study

        elif hasattr(self, 'study') and self.study:
            return self.study


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

    #: Creation/editing status of investigation
    status = models.CharField(
        max_length=64,
        default='OK',
        unique=False,
        blank=True,
        null=True,
        help_text='Creation/editing status of investigation')

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

    #: Column headers
    header = JSONField(
        default=dict,
        help_text='Column headers')

    #: Pre-constructed study table for rendering
    render_table = JSONField(
        default=dict,
        help_text='Pre-constructed study table for rendering')

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

    def get_name(self):
        """Return simple printable name for Assay"""
        return self.title

    def get_sources(self):
        """Return study sources"""
        return GenericMaterial.objects.filter(
            study=self, item_type='SOURCE').order_by('name')

    def get_characteristic_cat(self, characteristic):
        """Return characteristic category"""
        # TODO: Refactor for altamISA, currently not implemented
        '''
        for c in self.characteristic_cat:
            if c['@id'] == characteristic['category']['@id']:
                return c['characteristicType']
        '''

    def get_unit_cat(self, unit):
        """Return unit category"""
        # TODO: Refactor for altamISA, currently not implemented
        '''
        for c in self.unit_cat:
            if c['@id'] == unit['@id']:
                return c
        '''

    def get_factor(self, factor_value):
        """Return factor definition"""
        # TODO: Refactor for altamISA, currently not implemented
        '''
        for f in self.factors:
            if f['@id'] == factor_value['category']['@id']:
                return f
        '''


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
        # TODO: Refactor for altamISA, currently not implemented
        """Return parameter definition"""
        '''
        for p in self.parameters:
            if p['parameterName']['@id'] == parameter_value['category']['@id']:
                return p
        '''


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

    #: Column headers
    header = JSONField(
        default=dict,
        help_text='Column headers')

    #: Pre-constructed assay table for rendering
    render_table = JSONField(
        default=dict,
        help_text='Pre-constructed assay table for rendering')

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

    def get_name(self):
        """Return simple printable name for Assay"""
        return self.file_name

    def get_samples(self):
        """Return samples used in assay"""
        return GenericMaterial.objects.filter(
            item_type='SAMPLE',
            arcs_as_tail__assay=self).order_by('name').distinct()

    def get_sources(self):
        """Return sources of samples used in this assay as a list"""
        sources = []

        for sample in self.get_samples():
            sources += sample.get_sources()

        return sorted(set(sources), key=lambda x: x.name)

    def get_arcs_by_sample(self, sample):
        """
        Return starting Arcs which take sample as initial tail
        :param sample: GenericMaterial object of type "SAMPLE"
        :return: QuerySet of Process objects (first process of each sequence)
        :raise: ValueError if input GenericMaterial is not of type "SAMPLE"
        """
        if sample.item_type != 'SAMPLE':
            raise ValueError('Input is not a sample')

        return Arc.objects.filter(assay=self, tail_material=sample)


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

        indexes = [
            models.Index(fields=['study', 'item_type'])]

    def __str__(self):
        return '{}/{}/{}/{}/{}'.format(
            self.get_study().investigation.title,
            self.get_study().title,
            self.assay.file_name if self.assay else 'N/A',
            self.item_type,
            self.name)

    def __repr__(self):
        values = (
            self.get_study().investigation.title,
            self.get_study().title,
            self.assay.file_name if self.assay else 'N/A',
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

        '''
        if self.item_type in ['DATA', 'MATERIAL'] and not self.material_type:
            raise ValidationError('Type of material missing')
        '''

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
        if self.item_type == 'SOURCE':
            return self

        def find_sources(arcs, sources):
            for a in arcs:
                if a.tail_material and a.tail_material.item_type == 'SOURCE':
                    sources.append(a.tail_material)

                else:
                    prev_arcs = a.go_back(include_study=True)

                    if prev_arcs:
                        sources += find_sources(prev_arcs, sources)

            return set(sources)

        material_arcs = Arc.objects.filter(study=self.study, tail_material=self)
        sources = find_sources(material_arcs, [])

        return sorted(sources, key=lambda x: x.name)

    def get_samples(self):
        """Return samples derived from source"""
        if self.item_type != 'SOURCE':
            return None

        def find_samples(arcs, samples):
            for a in arcs:
                if a.head_material and a.head_material.item_type == 'SAMPLE':
                    samples.append(a.head_material)

                else:
                    next_arcs = a.go_forward()

                    if next_arcs:
                        samples += find_samples(next_arcs, samples)

            return set(samples)

        source_arcs = Arc.objects.filter(study=self.study, tail_material=self)
        samples = find_samples(source_arcs, [])

        return sorted(samples, key=lambda x: x.name)


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

    #: Comments
    comments = JSONField(
        default=dict,
        help_text='Comments')

    class Meta:
        verbose_name_plural = 'processes'

    def __str__(self):
        # TODO: Refactor once we're using protocols again
        return '{}/{}/{}/{}'.format(
            self.get_study().investigation.title,
            self.get_study().title,
            self.assay.file_name if self.assay else 'N/A',
            self.name)

    def __repr__(self):
        # TODO: Refactor once we're using protocols again
        values = (
            self.get_study().investigation.title,
            self.get_study().title,
            self.assay.file_name if self.assay else 'N/A',
            self.name)
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


# Arc --------------------------------------------------------------------------


class Arc(BaseSampleSheet):
    """altamISA parser model compatible arc depicting a relationship between
    material and process"""

    #: Study to which the arc belongs (for study sequence)
    study = models.ForeignKey(
        Study,
        related_name='arcs',
        null=True,
        help_text='Study to which the arc belongs (for study sequence)')

    #: Assay to which the arc belongs (for assay sequence)
    assay = models.ForeignKey(
        Assay,
        related_name='arcs',
        null=True,
        help_text='Assay to which the arc belongs (for assay sequence)')

    #: Tail process (can be null if tail object is a material)
    tail_process = models.ForeignKey(
        Process,
        related_name='arcs_as_tail',
        null=True,
        on_delete=models.SET_NULL,
        help_text='Tail process (can be null if tail object is a material)')

    #: Tail material (can be null if tail object is a process)
    tail_material = models.ForeignKey(
        GenericMaterial,
        related_name='arcs_as_tail',
        null=True,
        on_delete=models.SET_NULL,
        help_text='Tail material (can be null if tail object is a process)')

    #: Head process (can be null if head object is a material)
    head_process = models.ForeignKey(
        Process,
        related_name='arcs_as_head',
        null=True,
        on_delete=models.SET_NULL,
        help_text='Head process (can be null if head object is a material)')

    #: Tail material (can be null if tail object is a process)
    head_material = models.ForeignKey(
        GenericMaterial,
        related_name='arcs_as_head',
        null=True,
        on_delete=models.SET_NULL,
        help_text='Head material (can be null if head object is a process)')

    class Meta:
        ordering = ('study', 'assay')

        indexes = [
            models.Index(fields=['study', 'head_process']),
            models.Index(fields=['study', 'head_material']),
            models.Index(fields=['assay', 'tail_process']),
            models.Index(fields=['assay', 'tail_material'])]

    def __str__(self):
        return '{}/{}/{}/{}->{}'.format(
            self.get_study().investigation.title,
            self.get_study().title,
            self.assay.file_name if self.assay else 'N/A',
            self.get_tail_obj().name,
            self.get_head_obj().name)

    def __repr__(self):
        values = (
            self.get_study().investigation.title,
            self.get_study().title,
            self.assay.file_name if self.assay else 'N/A',
            self.get_tail_obj().name,
            self.get_head_obj().name)
        return 'Arc({})'.format(', '.join(repr(v) for v in values))

    # Saving and validation

    def save(self, *args, **kwargs):
        """Override save() to include custom validation functions"""
        self._validate_tail()
        self._validate_head()
        super(Arc, self).save(*args, **kwargs)

    def _validate_tail(self):
        """Validate that one (and only one) type of tail object is present"""
        if (self.tail_material is None) == (self.tail_process is None):
            raise ValidationError('Exactly one tail object must be set')

    def _validate_head(self):
        """Validate that one (and only one) type of head object is present"""
        if (self.head_material is None) == (self.head_process is None):
            raise ValidationError('Exactly one head object must be set')

    # Custom row-level functions

    def get_tail_obj(self):
        """Return tail object"""
        if self.tail_process:
            return self.tail_process

        elif self.tail_material:
            return self.tail_material

    def get_head_obj(self):
        """Return head object"""
        if self.head_process:
            return self.head_process

        elif self.head_material:
            return self.head_material

    def go_back(self, include_study=False):
        """
        Traverse backward in arc.
        :param include_study: Allow traversal from assay to study if True
        :return: QuerySet of 0-N Arc objects
        """
        head_obj_arg = 'head_{}'.format(
            ARC_OBJ_SUFFIX_MAP[self.get_tail_obj().__class__.__name__])

        query_args = {
            'study': self.study,
            head_obj_arg: self.get_tail_obj()}

        # Special cases when reaching a sample
        if self.tail_material and self.tail_material.item_type == 'SAMPLE':
            if self.assay and not include_study:
                return Arc.objects.none()

        elif self.assay:
            query_args['assay'] = self.assay

        # print('query_args={}'.format(query_args))   # DEBUG
        return Arc.objects.filter(**query_args)

    def go_forward(self, assay=None):
        """
        Traverse forward in arc.
        :param assay: Allow traversal from study arc to specified assay if set
        :return: QuerySet of 0-N Arc objects
        """
        tail_obj_arg = 'tail_{}'.format(
            ARC_OBJ_SUFFIX_MAP[self.get_head_obj().__class__.__name__])

        query_args = {
            'study': self.study,
            tail_obj_arg: self.get_head_obj()}

        # Special cases when reaching a sample
        if self.head_material and self.head_material.item_type == 'SAMPLE':
            if not self.assay and not assay:
                return Arc.objects.none()

            elif assay:
                query_args['assay'] = assay

        elif self.assay:
            query_args['assay'] = self.assay

        # print('query_args={}'.format(query_args))   # DEBUG
        return Arc.objects.filter(**query_args)
