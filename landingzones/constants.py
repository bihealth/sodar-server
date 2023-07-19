"""Constants for the landingzones app"""

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
STATUS_ALLOW_UPDATE = [ZONE_STATUS_ACTIVE, ZONE_STATUS_FAILED]

# Status types for zones for which activities have finished
STATUS_FINISHED = [
    ZONE_STATUS_MOVED,
    ZONE_STATUS_NOT_CREATED,
    ZONE_STATUS_DELETED,
]

# Status types which lock the project in Taskflow
STATUS_LOCKING = [
    ZONE_STATUS_PREPARING,
    ZONE_STATUS_VALIDATING,
    ZONE_STATUS_MOVING,
]

# Status types for busy landing zones
STATUS_BUSY = [
    ZONE_STATUS_CREATING,
    ZONE_STATUS_PREPARING,
    ZONE_STATUS_VALIDATING,
    ZONE_STATUS_MOVING,
    ZONE_STATUS_DELETING,
]

# Status types during which file lists and stats should be displayed
STATUS_DISPLAY_FILES = [
    ZONE_STATUS_ACTIVE,
    ZONE_STATUS_PREPARING,
    ZONE_STATUS_VALIDATING,
    ZONE_STATUS_MOVING,
    ZONE_STATUS_FAILED,
]
