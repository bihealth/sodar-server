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


# TODO: Add repetition with full data but repeat=True so the values can be used
#       in filtering (e.g. add as "hidden" attributes)

# TODO: Refactor addition funcs so that we return the row instead


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


def add_repetition(row, colspan, study_data_in_assay=False):
    """Append repetition columns"""
    for i in range(0, colspan):
        add_cell(
            row,
            repeat=True,
            classes=[STUDY_HIDEABLE_CLASS] if (
                    i > 0 and study_data_in_assay) else list())
        # NOTE: First field is not hidden


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
                unit = v['unit']['name']

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
        add_cell(row, obj.name)                         # Name
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
            first_sample_in_source = True

            for sample in samples:
                sample_section = []

                if not first_sample_in_source:
                    # add_repetition(row, len(source_section))
                    row += source_section

                first_sample_in_source = False

                add_element(
                    sample_section, top_header, field_header, sample, first_row)
                row += sample_section

                # Add row to table
                table_data.append(row)
                row = []
                first_row = False

        else:
            table_data.append(row)
            row = []
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
    samples = assay.get_samples()

    # Store sample sources
    sample_sources = {}

    for sample in samples:
        sample_sources[sample.unique_name] = sample.get_sources()

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
        first_sample_in_source = True

        # TODO: Optimize this: fixes multi-assay rendering but is VERY slow
        for sample in [
                s for s in samples if source in sample_sources[s.unique_name]]:
            sample_section = []

            if not first_sample_in_source:
                row += source_section
                # add_repetition(
                #     row, len(source_section), study_data_in_assay=True)

            first_sample_in_source = False

            add_element(
                sample_section, top_header, field_header, sample, first_row,
                study_data_in_assay=True)

            row += sample_section

            #############
            # Assay arcs
            #############

            # Get sequences
            arcs = assay.get_arcs_by_sample(sample)
            first_arc_in_sample = True

            # Iterate through arcs
            for arc in arcs:
                col_obj = arc.get_head_obj()

                if not first_arc_in_sample:
                    row += source_section
                    # add_repetition(
                    #     row, len(source_section), study_data_in_assay=True)
                    row += sample_section
                    # add_repetition(
                    #     row, len(sample_section), study_data_in_assay=True)

                first_arc_in_sample = False

                while col_obj:
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
                row = []
                first_row = False

            # row = []    # Clear out row even if we could not find arcs

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
    td_class_str = ' '.join(cell['classes'])

    # If repeating cell, return that
    if cell['repeat']:
        return '<td class="bg-light text-muted text-center {}">' \
               '"</td>\n'.format(td_class_str)

    # Right aligning
    def is_num(x):
        try:
            float(x)
            return True

        except ValueError:
            return False

    if cell['value'] and is_num(cell['value']):
        td_class_str += ' text-right'

    # Build <td>
    if cell['tooltip']:
        ret = '<td class="{}" title="{}" data-toggle="tooltip" ' \
              'data-placement="top">'.format(td_class_str, cell['tooltip'])

    else:
        ret = '<td class="{}">'.format(td_class_str)

    if cell['value']:
        if cell['link']:
            ret += '<a href="{}" target="_blank">{}</a>'.format(
                cell['link'], cell['value'])

        else:
            ret += cell['value']

        if cell['unit']:
            ret += '&nbsp;<span class=" text-muted">{}</span>'.format(
                cell['unit'])

    else:   # Empty value
        ret += '-'

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
    return '<th class="bg-white omics-ss-data-cell-links">&nbsp;</th>\n'


def render_links_cell(row):
    """
    Return links cell for row as HTML
    :param row: Row (list of dicts)
    :return: String (contains HTML)
    """
    # TODO: Add actual links
    # TODO: Refactor/cleanup, this is a quick screenshot HACK

    return '<td class="bg-light omics-ss-data-cell-links">\n' \
           '  <div class="btn-group omics-ss-data-btn-group">\n' \
           '    <button class="btn btn-secondary dropdown-toggle btn-sm ' \
           '                   omics-edit-dropdown"' \
           '                   type="button" data-toggle="dropdown" ' \
           '                   aria-expanded="false">' \
           '                   <i class="fa fa-external-link"></i>' \
           '    </button>' \
           '  </div>\n' \
           '</td>\n'
