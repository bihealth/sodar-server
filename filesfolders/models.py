import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from db_file_storage.model_utils import delete_file, delete_file_if_needed

# Projectroles dependency
from projectroles.models import Project


# Access Django user model
AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


# Local constants
FILESFOLDERS_FLAGS = {
    'IMPORTANT': {
        'icon': 'exclamation-circle',
        'label': 'Important',
        'color': 'warning'},
    'FLAG': {
        'icon': 'flag',
        'label': 'Flagged',
        'color': 'info'},
    'FLAG_HEART': {
        'icon': 'heart',
        'label': 'Flagged (Heart)',
        'color': 'danger'},
    'REVOKED': {
        'icon': 'undo',
        'label': 'Revoked',
        'color': 'secondary'},
    'SUPERSEDED': {
        'icon': 'history',
        'label': 'Superseded',
        'color': 'dark'}}

FLAG_CHOICES = [
    (k, FILESFOLDERS_FLAGS[k]['label']) for k in sorted(FILESFOLDERS_FLAGS)]


# Base class -------------------------------------------------------------


class FilesfoldersManager(models.Manager):
    """Manager for custom table-level BaseFilesfoldersClass queries"""
    def find(self, search_term, keywords=None):
        """
        Return objects or links matching the query.
        :param search_term: Search term (string)
        :param keywords: Optional search keywords as key/value pairs (dict)
        :return: Python list of BaseFilesfolderClass objects
        """
        objects = super(
            FilesfoldersManager, self).get_queryset().order_by('name')

        objects = objects.filter(
            Q(name__icontains=search_term) |
            Q(description__icontains=search_term))

        return objects


class BaseFilesfoldersClass(models.Model):
    """Abstract class for all filesfolders objects"""

    #: Folder name
    name = models.CharField(
        max_length=255,
        unique=False,
        help_text='Name for the object')

    #: Project in which the folder belongs
    project = models.ForeignKey(
        Project,
        related_name='%(app_label)s_%(class)s_objects',
        help_text='Project in which the object belongs')

    #: Folder under which object exists (null if root folder)
    folder = models.ForeignKey(
        'Folder',
        related_name='%(app_label)s_%(class)s_children',
        null=True,
        blank=True,
        help_text='Folder under which object exists (null if root folder)')

    #: User who owns the object
    owner = models.ForeignKey(
        AUTH_USER_MODEL,
        help_text='User who owns the object')

    #: DateTime of last modification
    date_modified = models.DateTimeField(
        auto_now=True,
        help_text='DateTime of last modification')

    #: Flag
    flag = models.CharField(
        max_length=64,
        unique=False,
        blank=True,
        null=True,
        choices=FLAG_CHOICES,
        help_text='Flag')

    #: Description (optional)
    description = models.CharField(
        max_length=255,
        unique=False,
        blank=True,
        help_text='Description (optional)')

    #: Omics UUID
    omics_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text='Omics UUID')

    # Set manager for custom queries
    objects = FilesfoldersManager()

    class Meta:
        abstract = True


# Folder -----------------------------------------------------------------


class Folder(BaseFilesfoldersClass):
    """Folder which stores filefolders objects"""

    class Meta:
        ordering = ['project', 'name']
        # Ensure name is unique within parent folder
        unique_together = ('project', 'folder', 'name')

    def __str__(self):
        return '{}: {}{}'.format(
            self.project.title,
            self.folder.get_path() if self.folder else 'root/',
            self.name)

    def __repr__(self):
        values = (
            self.project.title,
            self.name,
            self.folder if self.folder else '/')

        return 'Folder({})'.format(', '.join(repr(v) for v in values))

    def get_path(self):
        """Return full path as str"""
        if self.folder:
            ret = self.folder.get_path()

        else:
            ret = 'root/'

        ret += '{}/'.format(self.name)
        return ret

    def is_empty(self):
        """Return True if the folder contains no subfolders, files or links"""
        return (
            self.filesfolders_folder_children.count() == 0 and
            self.filesfolders_file_children.count() == 0 and
            self.filesfolders_hyperlink_children.count() == 0)

    def has_in_path(self, folder):
        """Return True if folder exists in this folder's parent path"""
        if self.folder == folder:
            return True

        elif self.folder:
            return self.folder.has_in_path(folder)

        return False


# File -------------------------------------------------------------------


class FileData(models.Model):
    """Class for storing actual file data in the Postgres database, needed by
    django-db-file-storage"""

    #: File data
    bytes = models.TextField()

    #: File name
    file_name = models.CharField(max_length=255)

    # Content type
    content_type = models.CharField(max_length=255)


class FileManager(FilesfoldersManager):
    """Manager for custom table-level File queries"""

    def get_folder_readme(self, project_pk, folder_pk):
        """
        Return readme file for a folder, or None if it wasn't found.
        :param project_pk: Pk of the Project
        :param folder_pk: Pk of the Folder or None if root
        :return: File object or None
        """
        try:
            return File.objects.get(
                name__istartswith='readme',
                project=project_pk,
                folder=folder_pk)

        except File.DoesNotExist:
            return None


class File(BaseFilesfoldersClass):
    """Small file uploaded using the filesfolders app"""

    #: Uploaded file using django-db-file-storage
    file = models.FileField(
        blank=True,
        null=True,
        upload_to='filesfolders.FileData/bytes/file_name/content_type',
        help_text='Uploaded file')

    #: Allow providing a public URL for the file
    public_url = models.BooleanField(
        default=False,
        help_text='Allow providing a public URL for the file')

    #: Secret string for creating public URL (auto created by form)
    secret = models.CharField(
        max_length=255,
        unique=True,
        blank=False,
        null=False,
        help_text='Secret string for creating public URL')

    # Set manager for custom queries
    objects = FileManager()

    class Meta:
        ordering = ['folder', 'name']
        # Ensure file/folder combination is unique
        unique_together = ('project', 'folder', 'name')

    def __str__(self):
        return '{}: {}{}'.format(
            self.project.title,
            self.folder.get_path() if self.folder else 'root/',
            self.name)

    def __repr__(self):
        values = (
            self.project.title,
            self.name,
            self.folder if self.folder else '/')
        return 'File({})'.format(', '.join(repr(v) for v in values))

    def save(self, *args, **kwargs):
        """Override save for deleting file from database if needed"""
        delete_file_if_needed(self, 'file')
        super(File, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Override delete for deleting file from database"""
        super(File, self).delete(*args, **kwargs)
        delete_file(self, 'file')


class HyperLink(BaseFilesfoldersClass):
    """Hyperlink saved using the filesfolders app"""

    #: URL for the link
    url = models.URLField(
        max_length=2000,
        blank=False,
        null=False,
        help_text='URL for the link')

    class Meta:
        ordering = ['folder', 'name']
        # Ensure link/folder combination is unique
        unique_together = ('project', 'folder', 'name')

    def __str__(self):
        return '{}: {}{}'.format(
            self.project.title,
            self.folder.name + ' / ' if self.folder else '',
            self.name)

    def __repr__(self):
        values = (
            self.project.title,
            self.name,
            self.folder if self.folder else '')
        return 'HyperLink({})'.format(', '.join(repr(v) for v in values))
