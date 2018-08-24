from django.urls import reverse

# Projectroles dependency
from projectroles.plugins import ProjectAppPluginPoint

from .models import File, Folder, HyperLink
from .urls import urlpatterns


class ProjectAppPlugin(ProjectAppPluginPoint):
    """Plugin for registering app with Projectroles"""

    # Properties required by django-plugins ------------------------------

    #: Name (slug-safe, used in URLs)
    name = 'filesfolders'

    #: Title (used in templates)
    title = 'Small Files'

    #: App URLs (will be included in settings by djangoplugins)
    urls = urlpatterns

    # Properties defined in ProjectAppPluginPoint -----------------------

    #: Project settings definition
    project_settings = {
        'allow_public_links': {
            'type': 'BOOLEAN',
            'default': False,
            'description': 'Allow generation of public links for files'}}

    #: FontAwesome icon ID string
    icon = 'file'

    #: Entry point URL ID (must take project omics_uuid as "project" argument)
    entry_point_url_id = 'filesfolders:list'

    #: Description string
    description = 'Smaller files (e.g., reports, spreadsheets, and ' \
                  'presentations)'

    #: Required permission for accessing the app
    app_permission = 'filesfolders.view_data'

    #: Enable or disable general search from project title bar
    search_enable = True

    #: List of search object types for the app
    search_types = [
        'file',
        'folder',
        'link']

    #: Search results template
    search_template = 'filesfolders/_search_results.html'

    #: App card template for the project details page
    details_template = 'filesfolders/_details_card.html'

    #: App card title for the project details page
    details_title = 'Small Files Overview'

    #: Position in plugin ordering
    plugin_ordering = 30

    def get_taskflow_sync_data(self):
        """
        Return data for syncing taskflow operations
        :return: List of dicts or None.
        """
        return None

    def get_object_link(self, model_str, uuid):
        """
        Return URL for referring to a object used by the app, along with a
        label to be shown to the user for linking.
        :param model_str: Object class (string)
        :param uuid: omics_uuid of the referred object
        :return: Dict or None if not found
        """
        obj = self.get_object(eval(model_str), uuid)

        if not obj:
            return None

        elif obj.__class__ == File:
            return {
                'url': reverse(
                    'filesfolders:file_serve',
                    kwargs={
                        'file': obj.omics_uuid,
                        'file_name': obj.name}),
                    'label': obj.name,
                    'blank': True}

        elif obj.__class__ == Folder:
            return {
                'url': reverse(
                    'filesfolders:list',
                    kwargs={'folder': obj.omics_uuid}),
                'label': obj.name}

        elif obj.__class__ == HyperLink:
            return {
                'url': obj.url,
                'label': obj.name,
                'blank': True}

        return None

    def search(self, search_term, user, search_type=None, keywords=None):
        """
        Return app items based on a search term, user, optional type and
        optional keywords
        :param search_term: String
        :param user: User object for user initiating the search
        :param search_type: String
        :param keywords: List (optional)
        :return: Dict
        """
        items = []

        if not search_type:
            files = File.objects.find(search_term, keywords)
            folders = Folder.objects.find(search_term, keywords)
            links = HyperLink.objects.find(search_term, keywords)
            items = list(files) + list(folders) + list(links)
            items.sort(key=lambda x: x.name.lower())

        elif search_type == 'file':
            items = File.objects.find(search_term, keywords).order_by('name')

        elif search_type == 'folder':
            items = Folder.objects.find(search_term, keywords).order_by('name')

        elif search_type == 'link':
            items = HyperLink.objects.find(
                search_term, keywords).order_by('name')

        if items:
            items = [
                x for x in items if
                user.has_perm('filesfolders.view_data', x.project)]

        return {
            'all': {
                'title': 'Small Files, Folders and Links',
                'search_types': ['file', 'folder', 'link'],
                'items': items}}
