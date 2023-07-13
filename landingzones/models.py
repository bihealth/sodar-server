import uuid

from django.conf import settings
from django.db import models

# Projectroles dependency
from projectroles.models import Project

# Samplesheets dependency
from samplesheets.models import Assay

# Access Django user model
AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


# Status types for landing zones
ZONE_STATUS_OK = 'OK'
ZONE_STATUS_CREATING = 'CREATING'
ZONE_STATUS_NOT_CREATED = 'NOT CREATED'
ZONE_STATUS_ACTIVE = 'ACTIVE'
ZONE_STATUS_PREPARING = 'PREPARING'
ZONE_STATUS_VALIDATING = 'VALIDATING'
ZONE_STATUS_MOVING = 'MOVING'
ZONE_STATUS_MOVED = 'MOVED'
ZONE_STATUS_FAILED = 'FAILED'
ZONE_STATUS_DELETING = 'DELETING'
ZONE_STATUS_DELETED = 'DELETED'

ZONE_STATUS_TYPES = [
    ZONE_STATUS_CREATING,
    ZONE_STATUS_NOT_CREATED,
    ZONE_STATUS_ACTIVE,
    ZONE_STATUS_PREPARING,
    ZONE_STATUS_VALIDATING,
    ZONE_STATUS_MOVING,
    ZONE_STATUS_MOVED,
    ZONE_STATUS_FAILED,
    ZONE_STATUS_DELETING,
    ZONE_STATUS_DELETED,
]

DEFAULT_STATUS_INFO = {
    ZONE_STATUS_CREATING: 'Creating landing zone in iRODS',
    ZONE_STATUS_NOT_CREATED: 'Creating landing zone in iRODS failed (unknown problem)',
    ZONE_STATUS_ACTIVE: 'Available with write access for user',
    ZONE_STATUS_PREPARING: 'Preparing transaction for validation and moving',
    ZONE_STATUS_VALIDATING: 'Validation in progress, write access disabled',
    ZONE_STATUS_MOVING: 'Validation OK, moving files into sample data repository',
    ZONE_STATUS_MOVED: 'Files moved successfully, landing zone removed',
    ZONE_STATUS_FAILED: 'Validation/moving failed (unknown problem)',
    ZONE_STATUS_DELETING: 'Deleting landing zone',
    ZONE_STATUS_DELETED: 'Landing zone deleted',
}
STATUS_INFO_DELETE_NO_COLL = (
    'No iRODS collection for zone found, marked as deleted'
)

STATUS_STYLES = {
    ZONE_STATUS_CREATING: 'bg-warning',
    ZONE_STATUS_NOT_CREATED: 'bg-danger',
    ZONE_STATUS_ACTIVE: 'bg-info',
    ZONE_STATUS_PREPARING: 'bg-warning',
    ZONE_STATUS_VALIDATING: 'bg-warning',
    ZONE_STATUS_MOVING: 'bg-warning',
    ZONE_STATUS_MOVED: 'bg-success',
    ZONE_STATUS_FAILED: 'bg-danger',
    ZONE_STATUS_DELETING: 'bg-warning',
    ZONE_STATUS_DELETED: 'bg-secondary',
}

# Status types for which zone validation, moving and deletion are allowed
STATUS_ALLOW_UPDATE = ['ACTIVE', 'FAILED']

# Status types for zones for which activities have finished
STATUS_FINISHED = ['MOVED', 'NOT CREATED', 'DELETED']

# Status types which lock the project in Taskflow
STATUS_LOCKING = ['PREPARING', 'VALIDATING', 'MOVING']

# Status types for busy landing zones
STATUS_BUSY = ['CREATING', 'PREPARING', 'VALIDATING', 'MOVING', 'DELETING']

# Status types during which file lists and stats should be displayed
STATUS_DISPLAY_FILES = ['ACTIVE', 'PREPARING', 'VALIDATING', 'MOVING', 'FAILED']


class LandingZone(models.Model):
    """Class representing an user's iRODS landing zone for an assay"""

    #: Title of the landing zone
    title = models.CharField(
        max_length=255, unique=False, help_text='Title of the landing zone'
    )

    #: Project in which the landing zone belongs
    project = models.ForeignKey(
        Project,
        related_name='landing_zones',
        help_text='Project in which the landing zone belongs',
        on_delete=models.CASCADE,
    )

    #: User who owns the landing zone
    user = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='landing_zones',
        help_text='User who owns the landing zone',
        on_delete=models.CASCADE,
    )

    #: Assay for which the landing zone belongs
    assay = models.ForeignKey(
        Assay,
        related_name='landing_zones',
        help_text='Assay for which the landing zone belongs',
        on_delete=models.CASCADE,
    )

    #: Status of landing zone
    status = models.CharField(
        max_length=64,
        null=False,
        blank=False,
        default='CREATING',
        help_text='Status of landing zone',
    )

    #: Additional status information
    status_info = models.CharField(
        max_length=1024,
        null=True,
        blank=True,
        default=DEFAULT_STATUS_INFO['CREATING'],
        help_text='Additional status information',
    )

    #: DateTime of last folder modification
    date_modified = models.DateTimeField(
        auto_now=True, help_text='DateTime of last landing zone modification'
    )

    #: Landing zone description (optional)
    description = models.TextField(
        unique=False,
        blank=True,
        help_text='Landing zone description (optional)',
    )

    #: Message displayed to project members on zone move (optional)
    user_message = models.CharField(
        max_length=1024,
        unique=False,
        blank=True,
        help_text='Message displayed to project members on successful zone '
        'moving if member notifications are enabled (optional)',
    )

    #: Special configuration
    configuration = models.CharField(
        max_length=64,
        unique=False,
        blank=True,
        null=True,
        help_text='Special configuration (optional, leave blank for a '
        'standard landing zone)',
    )

    #: Configuration data (for storing plugin-specific settings)
    config_data = models.JSONField(
        default=dict,
        help_text='Configuration data (for storing plugin-specific settings)',
    )

    #: Landing zone SODAR UUID
    sodar_uuid = models.UUIDField(
        default=uuid.uuid4, unique=True, help_text='Landing zone SODAR UUID'
    )

    class Meta:
        ordering = ['project', 'assay__file_name', 'title']
        # Ensure name is unique within project and user
        unique_together = ('title', 'project', 'user')

    def __str__(self):
        return '{}: {}/{}'.format(
            self.project.title, self.user.username, self.title
        )

    def __repr__(self):
        values = (self.project.title, self.user.username, self.title)
        return 'LandingZone({})'.format(', '.join(repr(v) for v in values))

    # Custom row-level functions

    def get_project(self):
        """Get project in cases where multiple object types may be included"""
        return self.project

    def set_status(self, status, status_info=None):
        """Set zone status"""
        if status not in ZONE_STATUS_TYPES:
            raise TypeError('Unknown status "{}"'.format(status))
        self.status = status
        if status_info:
            self.status_info = status_info
        else:
            self.status_info = DEFAULT_STATUS_INFO[status][:1024]
        self.save()

    def is_locked(self):
        """
        Return True/False depending whether write access to zone is currently
        locked.
        """
        return self.status in STATUS_LOCKING

    def can_display_files(self):
        """
        Return True/False depending whether file info should be displayed.
        """
        return self.status in STATUS_DISPLAY_FILES
