"""Assay app plugin for samplesheets"""

# Projectroles dependency
from projectroles.models import Project, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

from samplesheets.models import Assay
from samplesheets.plugins import SampleSheetAssayPluginPoint
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.utils import get_last_material_name, get_isa_field_name

# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets.assayapps.dna_sequencing'


class SampleSheetAssayPlugin(SampleSheetAssayPluginPoint):
    """Plugin for DNA sequencing assays in sample sheets"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_assay_dna_sequencing'

    #: Title
    title = 'DNA Sequencing Assay Plugin'

    # Properties defined in SampleSheetAssayPluginPoint ------------------

    #: App name for dynamic reference to app in e.g. caching
    app_name = APP_NAME

    #: Identifying assay fields (used to identify plugin by assay)
    assay_fields = [
        {
            'measurement_type': 'genome sequencing',
            'technology_type': 'nucleotide sequencing',
        },
        {
            'measurement_type': 'exome sequencing',
            'technology_type': 'nucleotide sequencing',
        },
        {
            'measurement_type': 'transcription profiling',
            'technology_type': 'nucleotide sequencing',
        },
        {
            'measurement_type': 'panel sequencing',
            'technology_type': 'nucleotide sequencing',
        },
    ]

    #: Description string
    description = 'Sample sheets DNA sequencing assay app'

    #: Template for assay addition (Assay object as "assay" in context)
    assay_template = None

    #: Required permission for accessing the plugin
    # TODO: TBD: Do we need this?
    permission = None

    #: Toggle displaying of row-based iRODS links in the assay table
    display_row_links = True

    def get_row_path(self, row, table, assay, assay_path):
        """Return iRODS path for an assay row in a sample sheet. If None,
        display default path.
        :param row: List of dicts (a row returned by SampleSheetTableBuilder)
        :param table: Full table with headers (dict returned by
                      SampleSheetTableBuilder)
        :param assay: Assay object
        :param assay_path: Root path for assay
        :return: String with full iRODS path or None
        """
        # Get the name of the last material
        last_material_name = get_last_material_name(row, table)

        if last_material_name:
            return assay_path + '/' + last_material_name

        return None

    def update_row(self, row, table, assay):
        """
        Update render table row with e.g. links. Return the modified row
        :param row: Original row (list of dicts)
        :param table: Full table (dict)
        :param assay: Assay object
        :return: List of dicts
        """
        return row

    def update_cache(self, name=None, project=None, user=None):
        """
        Update cached data for this app, limitable to item ID and/or project.

        :param name: Item name to limit update to (string, optional)
        :param project: Project object to limit update to (optional)
        :param user: User object to denote user triggering the update (optional)
        """
        if name and (
            name.split('/')[0] != 'irods' or name.split('/')[1] != 'rows'
        ):
            return

        try:
            cache_backend = get_backend_api('sodar_cache')
            irods_backend = get_backend_api('omics_irods')

        except Exception:
            return

        if not cache_backend or not irods_backend:
            return

        tb = SampleSheetTableBuilder()
        projects = (
            [project]
            if project
            else Project.objects.filter(type=PROJECT_TYPE_PROJECT)
        )
        all_assays = Assay.objects.filter(
            study__investigation__project__in=projects,
            study__investigation__irods_status=True,
        )
        config_assays = []

        # Filter assays by measurement and technology type
        for assay in all_assays:
            search_fields = {
                'measurement_type': get_isa_field_name(assay.measurement_type),
                'technology_type': get_isa_field_name(assay.technology_type),
            }

            if search_fields in self.assay_fields:
                config_assays.append(assay)

        # Iterate through studies so we don't have to rebuild too many tables
        studies = list(set([a.study for a in config_assays]))

        # Get assay paths
        for study in studies:
            study_tables = tb.build_study_tables(study)

            for assay in [a for a in study.assays.all() if a in config_assays]:
                assay_table = study_tables['assays'][str(assay.sodar_uuid)]
                assay_path = irods_backend.get_path(assay)
                row_paths = []
                item_name = 'irods/rows/{}'.format(assay.sodar_uuid)

                for row in assay_table['table_data']:
                    path = self.get_row_path(
                        row, assay_table, assay, assay_path
                    )

                    if path not in row_paths:
                        row_paths.append(path)

                # Build cache for paths
                cache_data = {'paths': {}}

                for path in row_paths:
                    try:
                        cache_data['paths'][
                            path
                        ] = irods_backend.get_object_stats(path)

                    except FileNotFoundError:
                        cache_data['paths'][path] = None

                cache_backend.set_cache_item(
                    name=item_name,
                    app_name=APP_NAME,
                    user=user,
                    data=cache_data,
                    project=assay.get_project(),
                )
