from django.urls import reverse

# Projectroles dependency
from projectroles.plugins import ProjectAppPluginPoint

from .models import Investigation
from .urls import urlpatterns
# from .utils import get_irods_dirs


class ProjectAppPlugin(ProjectAppPluginPoint):
    """Plugin for registering app with Projectroles"""

    # Properties required by django-plugins ------------------------------

    #: Name (slug-safe, used in URLs)
    name = 'samplesheets'

    #: Title (used in templates)
    title = 'Sample Sheets'

    #: App URLs (will be included in settings by djangoplugins)
    urls = urlpatterns

    # Properties defined in ProjectAppPluginPoint -----------------------

    #: Project settings definition
    project_settings = {}

    #: FontAwesome icon ID string
    icon = 'flask'

    #: Entry point URL ID (must take project omics_uuid as "project" argument)
    entry_point_url_id = 'samplesheets:project_sheets'

    #: Description string
    description = 'Sample sheets contain your donors/patients, samples, and ' \
                  'links to assays (such as NGS data), with ISA-Tools ' \
                  'compatibility'

    #: Required permission for accessing the app
    app_permission = 'samplesheets.view_sheet'

    #: Enable or disable general search from project title bar
    search_enable = True

    #: List of search object types for the app
    search_types = [
        'source',
        'sample',
        'file']

    #: Search results template
    search_template = 'samplesheets/_search_results.html'

    #: App card title for the main search page
    search_title = 'Sample Sheet Sources, Samples and Files'

    #: App card template for the project details page
    details_template = 'samplesheets/_details_card.html'

    #: App card title for the project details page
    details_title = 'Sample Sheets Overview'

    #: Position in plugin ordering
    plugin_ordering = 10

    def get_info(self, pk):
        """
        Return app information to be displayed on the project details page
        :param pk: Project ID
        :returns: List of tuples
        """

        '''
        try:
            sheet = SampleSheet.objects.get(project=pk)
            sheet_type = sheet.sheet_type
            irods_dirs = sheet.irods_dirs

        except SampleSheet.DoesNotExist:
            sheet_type = 'N/A'
            irods_dirs = False

        info = []
        info.append(
            ('Sheet Type', sheet_type))
        info.append((
            'Available in iRODS', irods_dirs))

        return info
        '''
        return []

    '''
    def get_taskflow_sync_data(self):
        """
        Return data for syncing taskflow operations
        :return: List of dicts or None.
        """
        sync_flows = []

        # NOTE: This only syncs previously created dirs
        for sheet in SampleSheet.objects.filter(irods_dirs=True):
            dirs, dirs_html = get_irods_dirs(sheet)
            flow = {
                'flow_name': 'sheet_dirs_create',
                'project_pk': sheet.project.pk,
                'flow_data': {'dirs': dirs}}
            sync_flows.append(flow)

        return sync_flows
    '''

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

        # The only possible model is SampleSheet, directing to entry point
        return {
            'url': reverse(
                'samplesheets:project_sheets',
                kwargs={'project': obj.project.omics_uuid}),
            'label': obj.title}
