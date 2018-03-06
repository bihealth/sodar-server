"""Rendering helpers for samplesheets"""


from .models import Process, GenericMaterial


HEADER_COLOURS = {
    'SOURCE': 'info',
    'SAMPLE': 'warning',
    'PROCESS': 'danger',
    'MATERIAL': 'success',
    'DATA': 'success'}

HEADER_LEGEND = {
    'SOURCE': 'Source',
    'SAMPLE': 'Sample',
    'PROCESS': 'Process',
    'MATERIAL': 'Material',
    'DATA': 'Data File'}

STUDY_HIDEABLE_CLASS = 'omics-ss-hideable-study'


# General/helper functions -----------------------------------------------------


def add_top_header(
        top_header, item_type, colspan, classes=list(), hiding={}):
    """Append columns to top header"""
    top_header.append({
        'legend': HEADER_LEGEND[item_type],
        'colour': HEADER_COLOURS[item_type],
        'colspan': colspan,
        'hiding': hiding})


def add_header(field_header, value, classes=list()):
    """
    Add column header value
    :param field_header: Header to be appended
    :param value: Value to be displayed
    :param classes: Optional extra classes
    """
    field_header.append({
        'value': value,
        'classes': classes})


def add_cell(
        row, value=None, unit=None, repeat=False, link=None, tooltip=None,
        classes=list()):
    """
    Add cell data
    :param row: Row in which the cell is added (list)
    :param value: Value to be displayed in the cell
    :param unit: Unit to be displayed in the cell
    :param repeat: Whether this is a repeating column (boolean)
    :param link: Link from the value (URL string)
    :param tooltip: Tooltip to be shown on mouse hover (string)
    :param classes: Optional extra classes
    """
    row.append({
        'value': value,
        'unit': unit,
        'repeat': repeat,
        'link': link,
        'tooltip': tooltip,
        'classes': classes})


def add_repetition(row, top_header, sections):
    """Append repetition columns"""
    for i in range(0, sum([x['colspan'] for x in top_header[0:sections]])):
        add_cell(row, repeat=True)


def add_annotation_headers(field_header, annotations, classes=list()):
    """Append annotation columns to field header"""
    a_count = 0

    for a in annotations:
        add_header(field_header, a.capitalize(), classes)
        a_count += 1

    return a_count


def add_annotations(row, annotations, classes=list()):
    """Append annotations to row columns"""
    if not annotations:
        return None

    for k, v in annotations.items():
        val = ''
        unit = None
        link = None
        tooltip = None

        if type(v['value']) == dict:
            if v['value']['ontology_name']:
                tooltip = v['value']['ontology_name']

            val += v['value']['name']
            link = v['value']['accession']

        else:
            val = v['value']

        # TODO: Test unit
        if 'unit' in v:
            if type(v['unit']) == dict:
                unit = v['value']['name']

            else:
                unit = v['unit']

        add_cell(
            row, val, unit=unit, link=link, tooltip=tooltip, classes=classes)


def add_element(
        row, top_header, field_header, obj, first_row,
        study_data_in_assay=False):
    """Append GenericMaterial or Protocol element to row"""
    hideable = [STUDY_HIDEABLE_CLASS] if study_data_in_assay else list()

    # Headers
    if first_row:
        field_count = 0
        hideable_count = 0

        # Material headers
        if type(obj) == GenericMaterial:
            add_header(field_header, 'Name')            # Name
            field_count += 1
            # NOTE: No study data hiding of name field

            a_header_count = add_annotation_headers(
                field_header, obj.characteristics,
                hideable)                               # Characteristics
            field_count += a_header_count

            if hideable:
                hideable_count += a_header_count

            if obj.item_type == 'SAMPLE':
                a_header_count = add_annotation_headers(
                    field_header, obj.factor_values,
                    hideable)                           # Factor values
                field_count += a_header_count

                if hideable:
                    hideable_count += a_header_count

            top_header_type = obj.item_type

        # Process headers
        # NOTE: No hiding of processes
        else:   # type(obj) == Process
            if obj.protocol:
                add_header(field_header, 'Protocol')    # Protocol
                field_count += 1

            add_header(field_header, 'Name')            # Name
            field_count += 1

            field_count += add_annotation_headers(
                field_header, obj.parameter_values)     # Parameter values

            top_header_type = 'PROCESS'

        add_top_header(top_header, top_header_type, field_count, hiding={
            STUDY_HIDEABLE_CLASS: hideable_count})

    # Material data
    if type(obj) == GenericMaterial:
        add_cell(row, obj.name)  # Name
        add_annotations(
            row, obj.characteristics, hideable)         # Characteristics

        if obj.item_type == 'SAMPLE':
            add_annotations(
                row, obj.factor_values, hideable)       # Factor values

    # Process data
    elif type(obj) == Process:
        if obj.protocol:
            add_cell(row, obj.protocol.name)            # Protocol

        add_cell(row, obj.name)  # Name
        add_annotations(row, obj.parameter_values)      # Parameter values


# Table building ---------------------------------------------------------------


# TODO: Repetition between get_study_table() and get_assay_table(), unify?


def get_study_table(study):
    """
    Return data grid for an HTML study table
    :param study: Study object
    :return: Dict
    """

    table_data = []
    top_header = []
    field_header = []
    first_row = True

    ##########
    # Sources
    ##########
    for source in study.get_sources():
        row = []
        source_section = []

        add_element(
            source_section, top_header, field_header, source, first_row)
        row += source_section

        ##########
        # Samples
        ##########
        samples = source.get_samples()

        if samples:
            for sample in samples:
                sample_section = []

                add_element(
                    sample_section, top_header, field_header, sample, first_row)
                row += sample_section

                # Add row to table
                table_data.append(row)
                first_row = False

        else:
            table_data.append(row)
            first_row = False

    return {
        'top_header': top_header,
        'field_header': field_header,
        'table_data': table_data}


def get_assay_table(assay):
    """
    Return data grid for an HTML assay table
    :param assay: Assay object
    :return: Dict
    """

    table_data = []
    top_header = []
    field_header = []
    first_row = True

    ##########
    # Sources
    ##########
    sources = assay.get_sources()

    for source in sources:
        row = []
        source_section = []

        add_element(
            source_section, top_header, field_header, source, first_row,
            study_data_in_assay=True)
        row += source_section

        ##########
        # Samples
        ##########
        for sample in source.get_samples():
            sample_section = []

            add_element(
                sample_section, top_header, field_header, sample, first_row,
                study_data_in_assay=True)
            row += sample_section

            #############
            # Assay arcs
            #############
            first_arc_in_sample = True

            # Get sequences
            arcs = assay.get_arcs_by_sample(sample)

            # Iterate through arcs
            for arc in arcs:
                col_obj = arc.get_head_obj()

                while col_obj:
                    if not first_arc_in_sample:
                        row = []
                        # row += source_section
                        add_repetition(row, top_header, 1)
                        row += sample_section

                    ###########
                    # Material
                    ###########
                    if type(col_obj) == GenericMaterial:
                        add_element(
                            row, top_header, field_header, col_obj, first_row)

                    ##########
                    # Process
                    ##########
                    elif type(col_obj) == Process:
                        add_element(
                            row, top_header, field_header, col_obj, first_row)

                    next_arcs = arc.go_forward()

                    if next_arcs:
                        # TODO: Support splitting (copy preceding row)
                        arc = arc.go_forward()[0]
                        col_obj = arc.get_head_obj()

                    else:
                        col_obj = None

                # Add row to table
                # print('Row: {}'.format(row))    # DEBUG
                table_data.append(row)
                first_arc_in_sample = False
                first_row = False

    return {
        'top_header': top_header,
        'field_header': field_header,
        'table_data': table_data}


# HTML rendering ---------------------------------------------------------------


def render_top_header(section):
    """
    Render section of top header
    :param section: Header section (dict)
    :return: String (contains HTML)
    """
    return '<th class="bg-{} text-nowrap text-white omics-ss-top-header" ' \
           'colspan="{}" original-colspan="{}" {}>{}</th>\n'.format(
            section['colour'],
            section['colspan'],     # Actual colspan
            section['colspan'],     # Original colspan
            ''.join(['{}-cols="{}" '.format(k, v) for
                     k, v in section['hiding'].items()]),
            section['legend'])


def render_header(header):
    """
    Render data table column header
    :param header: Header dict
    :return: String (contains HTML)
    """
    return '<th class="{}">{}</th>\n'.format(
        ' '.join(header['classes']),
        header['value'])


def render_cell(cell):
    """
    Return data table cell as HTML
    :param cell: Cell dict
    :return: String (contains HTML)
    """
    # TODO: refactor use of cell['classes']
    if cell['repeat']:
        return '<td class="bg-light text-muted text-center {}">' \
               '"</td>\n'.format(' '.join(cell['classes']))

    if cell['tooltip']:
        ret = '<td class="{}" title="{}" data-toggle="tooltip" ' \
              'data-placement="top">'.format(
                ' '.join(cell['classes']),
                cell['tooltip'])

    else:
        ret = '<td class="{}">'.format(' '.join(cell['classes']))

    if cell['value']:
        if cell['link']:
            ret += '<a href="{}" target="_blank">{}</a>'.format(
                cell['link'], cell['value'])

        else:
            ret += cell['value']

    else:   # Empty value
        ret += '-'

    if cell['unit']:
        ret += '<span class="pull-right text-muted">{}</span>'.format(
            cell['unit'])

    ret += '</td>\n'
    return ret


def render_links_top_header():
    return '<th class="bg-dark text-nowrap text-white omics-ss-top-header ' \
           'omics-ss-data-cell-links">Links</th>'


def render_links_header():
    """
    Render data table links column header
    :return: String (contains HTML)
    """
    return '<th class="bg-white omics-ss-data-cell-links">iRODS</th>\n'


def render_links_cell(row):
    """
    Return links cell for row as HTML
    :param row: Row (list of dicts)
    :return: String (contains HTML)
    """
    # TODO: Add actual links
    # TODO: Refactor/cleanup, this is a quick screenshot HACK

    def get_button(link, fa_class):
        return '<a role="button" class="btn btn-secondary ' \
               'btn-sm omics-ss-data-table-btn" href="{}">' \
               '<i class="fa {}"></i></a>'.format(link, fa_class)

    buttons = [
        get_button('#', 'fa-folder-open-o'),
        get_button('#', 'fa-terminal'),
        get_button('#', 'fa-desktop')]

    return '<td class="bg-light omics-ss-data-cell-links">' \
           '{}</td>\n'.format('&nbsp;'.join(buttons))
