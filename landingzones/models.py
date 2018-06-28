import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models

# Projectroles dependency
from projectroles.models import Project

# Samplesheets dependency
from samplesheets.models import Assay

# Access Django user model
AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


ZONE_STATUS_TYPES = [
    'CREATING',
    'NOT CREATED',
    'ACTIVE',
    'PREPARING',
    'VALIDATING',
    'MOVING',
    'FAILED',
    'MOVED',
    'DELETING',
    'DELETED']

DEFAULT_STATUS_INFO = {
    'CREATING': 'Creating landing zone in iRODS',
    'NOT CREATED': 'Creating landing zone in iRODS failed (unknown problem)',
    'ACTIVE': 'Available with write access for user',
    'PREPARING': 'Preparing transaction for validation and moving',
    'VALIDATING': 'Validation in progress, write access disabled',
    'MOVING': 'Validation OK, moving files into bio_samples',
    'MOVED': 'Files moved successfully, landing zone removed',
    'FAILED': 'Validation/moving failed (unknown problem)',
    'DELETING': 'Deleting landing zone',
    'DELETED': 'Landing zone deleted'}

STATUS_STYLES = {
    'CREATING': 'bg-warning',
    'NOT CREATED': 'bg-danger',
    'ACTIVE': 'bg-info',
    'PREPARING': 'bg-warning',
    'VALIDATING': 'bg-warning',
    'MOVING': 'bg-warning',
    'MOVED': 'bg-success',
    'FAILED': 'bg-danger',
    'DELETING': 'bg-warning',
    'DELETED': 'bg-secondary'}


class LandingZone(models.Model):
    """Class representing an user's iRODS landing zone for an assay"""

    #: Title of the landing zone
    title = models.CharField(
        max_length=255,
        unique=False,
        help_text='Title of the landing zone')

    #: Project in which the landing zone belongs
    project = models.ForeignKey(
        Project,
        related_name='landing_zones',
        help_text='Project in which the landing zone belongs')

    #: User who owns the landing zone
    user = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='landing_zones',
        help_text='User who owns the landing zone')

    #: Assay for which the landing zone belongs
    assay = models.ForeignKey(
        Assay,
        related_name='landing_zones',
        help_text='Assay for which the landing zone belongs')

    #: Status of landing zone
    status = models.CharField(
        max_length=64,
        null=False,
        blank=False,
        default='CREATING',
        help_text='Status of landing zone')

    #: Additional status information
    status_info = models.CharField(
        max_length=1024,
        null=True,
        blank=True,
        default=DEFAULT_STATUS_INFO['CREATING'],
        help_text='Additional status information')

    #: DateTime of last folder modification
    date_modified = models.DateTimeField(
        auto_now=True,
        help_text='DateTime of last landing zone modification')

    #: Landing zone description (optional)
    description = models.TextField(
        unique=False,
        blank=True,
        help_text='Landing zone description (optional)')

    #: Special configuration
    configuration = models.CharField(
        max_length=64,
        unique=False,
        blank=True,
        null=True,
        help_text='Special configuration (optional, leave blank for a '
                  'standard landing zone)')

    #: Configuration data (for storing plugin-specific settings)
    config_data = JSONField(
        default=dict,
        help_text='Configuration data (for storing plugin-specific settings)')

    #: Landing zone Omics UUID
    omics_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text='Landing zone Omics UUID')

    class Meta:
        ordering = ['project', 'assay__file_name', 'title']
        # Ensure name is unique within project and user
        unique_together = ('title', 'project', 'user')

    def __str__(self):
        return '{}: {}/{}'.format(
            self.project.title,
            self.user.username,
            self.title)

    def __repr__(self):
        values = (
            self.project.title,
            self.user.username,
            self.title)
        return 'LandingZone({})'.format(', '.join(repr(v) for v in values))

    # Custom row-level functions

    def get_project(self):
        """Get project in cases where multiple object types may be included"""
        return self.project

    def set_status(self, status, status_info=None):
        if status not in ZONE_STATUS_TYPES:
            raise TypeError('Unknown status "{}"'.format(status))

        self.status = status

        if status_info:
            self.status_info = status_info

        else:
            self.status_info = DEFAULT_STATUS_INFO[status][:1024]

        self.save()
