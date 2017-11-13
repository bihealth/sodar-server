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
            'description': 'Allow generation of public links for files'},
        }

    #: FontAwesome icon ID string
    icon = 'file'

    #: Entry point URL ID (must take project pk as "project" argument)
    entry_point_url_id = 'project_files'

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
        'link']

    #: Search results template
    search_template = 'filesfolders/_search_results.html'

    #: App card title for the main search page
    search_title = 'Small Files and Links'

    #: App card template for the project details page
    details_template = 'filesfolders/_details_card.html'

    #: App card title for the project details page
    details_title = 'Small Files Overview'

    #: App card position
    details_position = 20

    def get_taskflow_sync_data(self):
        """
        Return data for syncing taskflow operations
        :return: List of dicts or None.
        """
        return None

    def get_object_link(self, model_str, pk):
        """
        Return URL for referring to a object used by the app, along with a
        label to be shown to the user for linking.
        :param model_str: Object class (string)
        :param pk: Pk of the referred object
        :return: Dict or None if not found
        """
        obj = self.get_object(eval(model_str), pk)

        if not obj:
            return None

        elif obj.__class__ == File:
            return {
                'url': reverse(
                    'file_serve',
                    kwargs={
                        'project': obj.project.pk,
                        'pk': obj.pk,
                        'file_name': obj.name}),
                    'label': obj.name,
                    'blank': True}

        elif obj.__class__ == Folder:
            return {
                'url': reverse(
                    'project_files',
                    kwargs={
                        'project': obj.project.pk,
                        'folder': obj.pk}),
                'label': obj.name}

        elif obj.__class__ == HyperLink:
            return {
                'url': obj.url,
                'label': obj.name,
                'blank': True}

        return None
