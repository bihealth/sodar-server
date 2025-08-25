"""Sample sheet edit and display configuration management"""

import logging

from packaging import version

from django.conf import settings

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI

from samplesheets.models import Protocol
from samplesheets.rendering import SampleSheetTableBuilder


app_settings = AppSettingAPI()
logger = logging.getLogger(__name__)
table_builder = SampleSheetTableBuilder()


# Local constants
APP_NAME = 'samplesheets'
ONTOLOGY_COLS = {
    'hpo terms': {'allow_list': True, 'ontologies': ['HP']},
    'omim disease': {'allow_list': False, 'ontologies': ['OMIM']},
    'orphanet disease': {'allow_list': False, 'ontologies': ['ORDO']},
}


class SheetConfigAPI:
    """API for sample sheet edit and display configuration management"""

    @classmethod
    def _get_default_protocol(cls, investigation, render_table, idx):
        """
        Get UUID of a default protocol for a column.

        :param investigation: Investigation object
        :param render_table: Table from SampleSheetTableBuilder (dict)
        :param idx: Index for lookup (int)
        :return: String or None
        """
        p_name = None
        p_found = False
        protocol = None
        for row in render_table['table_data']:
            if not p_name and row[idx]['value']:
                p_name = row[idx]['value']
                p_found = True
            elif p_name and row[idx]['value'] != p_name:
                p_found = False
                break
        if p_found:
            protocol = Protocol.objects.filter(
                study__investigation=investigation,
                name=p_name,
            ).first()
        if protocol:
            return str(protocol.sodar_uuid)

    @classmethod
    def _restore_config_table(
        cls, investigation, render_table, config_table, start_idx=0
    ):
        """
        Update sheet config for a restore action for a single study/assay table.

        :param investigation: Investigation object
        :param render_table: Table from SampleSheetTableBuilder (dict)
        :param config_table: Table in an existing sheet config (dict)
        :param start_idx: Starting index for table
        """
        i = start_idx
        for node in config_table['nodes']:
            for field in node['fields']:
                if field.get('type') == 'protocol':
                    field['default'] = cls._get_default_protocol(
                        investigation, render_table, i
                    )
                    field['format'] = 'protocol'
                i += 1
        return config_table

    def get_sheet_config(self, investigation, inv_tables=None):
        """
        Get or build a sheet edit configuration for an investigation.

        :param investigation: Investigation object
        :param inv_tables: Render tables for investigation (optional)
        :return: Dict
        """
        sheet_config = app_settings.get(
            APP_NAME, 'sheet_config', project=investigation.project
        )
        sheet_ok = False
        msg = None
        if sheet_config:
            try:
                self.validate_sheet_config(sheet_config)
                sheet_ok = True
            except ValueError as ex:
                # TODO: Implement updating invalid configs if possible?
                msg = f'Invalid config, rebuilding.. Exception: "{ex}"'
        else:
            msg = 'No sheet configuration found, building..'

        if not sheet_ok:
            logger.info(msg)
            if not inv_tables:
                inv_tables = table_builder.build_inv_tables(
                    investigation, use_config=False
                )
            sheet_config = self.build_sheet_config(investigation, inv_tables)
            app_settings.set(
                APP_NAME,
                'sheet_config',
                sheet_config,
                project=investigation.project,
            )
            logger.info(
                f'Sheet configuration built for investigation '
                f'(UUID={investigation.sodar_uuid})'
            )
        return sheet_config

    @classmethod
    def build_sheet_config(cls, investigation, inv_tables):
        """
        Build sample sheet edit configuration.
        NOTE: Will be built from configuration template(s) eventually

        :param investigation: Investigation object
        :param inv_tables: Render tables for investigation studies and assays
        :return: Dict
        """
        ret = {
            'version': settings.SHEETS_CONFIG_VERSION,
            'investigation': {},
            'studies': {},
        }

        def _build_nodes(study_tables, assay_uuid=None):
            nodes = []
            sample_found = False
            ti = 0
            if not assay_uuid:
                table = study_tables['study']
            else:
                table = study_tables['assays'][assay_uuid]
            for th in table['top_header']:
                if not assay_uuid or sample_found:
                    node = {'header': th['value'], 'fields': []}
                    for i in range(ti, ti + th['colspan']):
                        h = table['field_header'][i]
                        f = {'name': h['name']}
                        if h['type']:
                            f['type'] = h['type']
                        # Set up default protocol if only one option in data
                        if h['type'] == 'protocol':
                            f['format'] = 'protocol'
                            f['default'] = cls._get_default_protocol(
                                investigation, table, i
                            )
                        # Set up ontology config
                        elif h['col_type'] == 'ONTOLOGY':
                            f['format'] = 'ontology'
                            # Special cases
                            if h['name'].lower() in ONTOLOGY_COLS:
                                f.update(ONTOLOGY_COLS[h['name'].lower()])
                            else:
                                f['allow_list'] = False
                                f['ontologies'] = []
                        # Set up external links
                        elif h['col_type'] == 'EXTERNAL_LINKS':
                            f['format'] = 'external_links'
                        node['fields'].append(f)
                    nodes.append(node)
                # Leave out study columns for assays
                if assay_uuid and th['value'] == 'Sample':
                    sample_found = True
                ti += th['colspan']
            return nodes

        # Add studies
        for study, study_tables in inv_tables.items():
            # Build tables (disable use_config in case we are replacing sheets)
            study_data = {
                'display_name': study.get_display_name(),
                # For human readability
                'nodes': _build_nodes(study_tables, None),
                'assays': {},
            }
            # Add study assays
            for assay in study.assays.all().order_by('pk'):
                assay_uuid = str(assay.sodar_uuid)
                study_data['assays'][assay_uuid] = {
                    'display_name': assay.get_display_name(),
                    'nodes': _build_nodes(study_tables, assay_uuid),
                }
            ret['studies'][str(study.sodar_uuid)] = study_data
        return ret

    @classmethod
    def validate_sheet_config(cls, config):
        """
        Validate sheet edit configuration.

        :param config: Dict
        :raise: ValueError if config is invalid.
        """
        if not config:
            raise ValueError('No configuration provided')
        if not config.get('version'):
            raise ValueError('Unknown configuration version')
        cfg_version = version.parse(config['version'])
        min_version = version.parse(settings.SHEETS_CONFIG_VERSION)
        if cfg_version < min_version:
            raise ValueError(
                f'Version "{cfg_version}" is below minimum version '
                f'"{min_version}"'
            )

    @classmethod
    def restore_sheet_config(cls, investigation, inv_tables, sheet_config):
        """
        Update sheet config on sample sheet restore.

        :param investigation: Investigation object
        :param inv_tables: Render tables for investigation studies and assays
        :param sheet_config: Sheet editing configuration (dict)
        """
        logger.info('Updating restored sheet config..')
        for study, study_tables in inv_tables.items():
            s_uuid = str(study.sodar_uuid)
            sheet_config['studies'][s_uuid] = cls._restore_config_table(
                investigation,
                study_tables['study'],
                sheet_config['studies'][s_uuid],
            )
            for assay in study.assays.all():
                a_uuid = str(assay.sodar_uuid)
                sheet_config['studies'][s_uuid]['assays'][a_uuid] = (
                    cls._restore_config_table(
                        investigation,
                        study_tables['assays'][a_uuid],
                        sheet_config['studies'][s_uuid]['assays'][a_uuid],
                        start_idx=len(study_tables['study']['field_header']),
                    )
                )
        app_settings.set(
            APP_NAME,
            'sheet_config',
            sheet_config,
            project=investigation.project,
        )
        logger.info('Restored sheet config updated')

    @classmethod
    def build_display_config(cls, inv_tables, sheet_config):
        """
        Build default display config for project sample sheet columns.

        :param inv_tables: Render tables for investigation studies and assays
        :param sheet_config: Sheet editing configuration (dict)
        :return: Dict
        """
        ret = {'investigation': {}, 'studies': {}}

        def _build_node(config_node, table, idx, assay_mode=False):
            display_node = {'header': config_node['header'], 'fields': []}
            n_idx = 0
            for config_field in config_node['fields']:
                display_field = {'name': config_field['name'], 'visible': False}
                if n_idx == 0 or (
                    not assay_mode
                    and (
                        config_field.get('editable')
                        or table['col_values'][idx] > 0
                    )
                ):
                    display_field['visible'] = True
                display_node['fields'].append(display_field)
                idx += 1
                n_idx += 1
            return display_node, idx

        # Add studies
        for study, study_tables in inv_tables.items():
            study_uuid = str(study.sodar_uuid)
            h_idx = 0
            study_data = {'nodes': [], 'assays': {}}

            for config_node in sheet_config['studies'][study_uuid]['nodes']:
                display_node, h_idx = _build_node(
                    config_node, study_tables['study'], h_idx
                )
                study_data['nodes'].append(display_node)

            # Add study assays
            for assay in study.assays.all().order_by('pk'):
                assay_uuid = str(assay.sodar_uuid)
                assay_table = study_tables['assays'][assay_uuid]
                h_idx = 0
                assay_data = {'nodes': []}

                # Add study nodes to assay table with only first field visible
                for config_node in sheet_config['studies'][study_uuid]['nodes']:
                    node, h_idx = _build_node(
                        config_node,
                        study_tables['study'],
                        h_idx,
                        assay_mode=True,
                    )
                    assay_data['nodes'].append(node)

                # Add actual assay nodes
                for config_node in sheet_config['studies'][study_uuid][
                    'assays'
                ][assay_uuid]['nodes']:
                    node, h_idx = _build_node(config_node, assay_table, h_idx)
                    assay_data['nodes'].append(node)

                study_data['assays'][assay_uuid] = assay_data
            ret['studies'][study_uuid] = study_data
        return ret
