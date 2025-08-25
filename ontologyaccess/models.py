"""Models for the ontologyaccess app"""

import uuid

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models

# Local constants
DEFAULT_LENGTH = 255
DEFAULT_TERM_URL = 'http://purl.obolibrary.org/obo/{id_space}_{local_id}'
TERM_URL_HELP = (
    'Format string for term accession URL. Supports {id_space} '
    'and {local_id}.'
)


class OBOFormatOntology(models.Model):
    """Ontology originating from the Open Biological and Biomedical Ontologies
    (OBO) format"""

    #: Ontology name
    name = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=True,
        blank=False,
        default='ONTOLOGY',  # Needed for migration
        help_text='Ontology name as it appears in sample sheets',
    )

    #: Ontology file name or URL
    file = models.CharField(
        max_length=2000,
        unique=False,
        blank=True,
        null=True,
        help_text='Ontology file name or URL',
    )

    #: Ontology ID
    ontology_id = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=True,
        blank=False,
        help_text='Ontology ID',
    )

    #: Ontology title (optional)
    title = models.CharField(
        max_length=DEFAULT_LENGTH,
        blank=True,
        null=True,
        help_text='Ontology title (optional)',
    )

    #: Ontology description (optional)
    description = models.TextField(
        blank=True,
        null=True,
        help_text='Ontology description (optional)',
    )

    #: Format version
    format_version = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='Format version',
    )

    #: Data version
    data_version = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Data version',
    )

    #: Default namespace
    default_namespace = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Default namespace',
    )

    #: Format string for term accession URL
    term_url = models.CharField(
        max_length=2000,
        blank=False,
        null=False,
        unique=False,
        default=DEFAULT_TERM_URL,
        help_text=TERM_URL_HELP,
    )

    #: SODAR version during ontology parsing
    sodar_version = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=False,
        help_text='SODAR version during ontology parsing',
    )

    #: DateTime of ontology creation in SODAR
    date_created = models.DateTimeField(
        auto_now=True, help_text='DateTime of ontology creation in SODAR'
    )

    #: SODAR UUID for the object
    sodar_uuid = models.UUIDField(
        default=uuid.uuid4, unique=True, help_text='SODAR UUID for the object'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name}: {self.title} ({self.ontology_id})'

    def __repr__(self):
        values = [self.name, self.title, self.ontology_id]
        return 'OBOFormatOntology({})'.format(
            ', '.join(repr(v) for v in values)
        )

    def save(self, *args, **kwargs):
        """Version of save() to include custom validation"""
        self._validate_name_case()
        super().save(*args, **kwargs)

    def _validate_name_case(self):
        """Validate name_case"""
        if not self.name.isupper():
            raise ValidationError(
                f'Ontology name "{self.name}" is not in upper case'
            )

    # Custom row-level functions

    def get_term_by_id(self, term_id):
        """
        Retrun ontology term by id or None if not found

        :param term_id: String
        :return: OBOFormatOntologyTerm
        """
        return OBOFormatOntologyTerm.objects.filter(
            ontology=self, term_id=term_id
        ).first()


class OBOFormatOntologyTerm(models.Model):
    """Ontology term belonging into an OBO ontology"""

    #: Ontology to which the term belongs
    ontology = models.ForeignKey(
        OBOFormatOntology,
        null=False,
        related_name='terms',
        help_text='Ontology to which the term belongs',
        on_delete=models.CASCADE,
    )

    #: Term ID
    term_id = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=True,
        blank=False,
        help_text='Term ID',
    )

    #: Alternative Term IDs
    alt_ids = ArrayField(
        models.CharField(max_length=DEFAULT_LENGTH, blank=True),
        default=list,
        help_text='Alternative Term IDs',
    )

    #: Term name
    name = models.CharField(
        max_length=1024,
        unique=False,
        blank=False,
        help_text='Term name',
    )

    #: Term definition
    definition = models.TextField(
        unique=False,
        blank=True,
        null=True,
        help_text='Term definition',
    )

    #: Term synonyms
    synonyms = ArrayField(
        models.CharField(max_length=DEFAULT_LENGTH, blank=True),
        default=list,
        help_text='Term synonyms',
    )

    #: Namespace
    namespace = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Namespace',
    )

    #: Term comment
    comment = models.TextField(
        unique=False,
        blank=True,
        null=True,
        help_text='Term comment',
    )

    #: Obsolete or deprecated term
    is_obsolete = models.BooleanField(
        default=False,
        help_text='Obsolete or deprecated term',
    )

    #: Replaced by ID in case of an obsolete term
    replaced_by = models.CharField(
        max_length=DEFAULT_LENGTH,
        unique=False,
        blank=True,
        null=True,
        help_text='Replaced by ID in case of an obsolete term',
    )

    #: SODAR UUID for the object
    sodar_uuid = models.UUIDField(
        default=uuid.uuid4, unique=True, help_text='SODAR UUID for the object'
    )

    # Custom row-level functions

    def get_id_space(self):
        """Return ID space for term name"""
        return self.term_id.split(':')[0]

    def get_local_id(self):
        """Return local ID for term name"""
        return self.term_id.split(':')[1]

    def get_url(self):
        """Return URL for this specific term"""
        return self.ontology.term_url.format(
            id_space=self.get_id_space(), local_id=self.get_local_id()
        )

    class Meta:
        pass

    def __str__(self):
        return f'{self.term_id} ({self.name})'

    def __repr__(self):
        values = [self.ontology.name, self.term_id, self.name]
        return 'OBOFormatOntologyTerm({})'.format(
            ', '.join(repr(v) for v in values)
        )
