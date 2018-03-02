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
    'DATA': 'Data File'
}


def get_assay_table(assay):
    """
    Return data grid for a "simple" HTML assay table
    :param assay: Assay object
    :return: Dict
    """

    table_data = []
    top_header = []
    field_header = []

    def add_top_header(top_header, item_type, colspan):
        """Append columns to top header"""
        top_header.append({
            'legend': HEADER_LEGEND[item_type],
            'colour': HEADER_COLOURS[item_type],
            'colspan': colspan})

    def add_val(
            row, value=None, unit=None, repeat=False, link=None, tooltip=None):
        """Append column value to row"""
        row.append({
            'value': value,
            'unit': unit,
            'repeat': repeat,
            'link': link,
            'tooltip': tooltip})

    def add_repetition(row, top_header, sections):
        """Append repetition columns"""
        for i in range(0, sum([x['colspan'] for x in top_header[0:sections]])):
            add_val(row, repeat=True)

    def add_annotation_headers(field_header, annotations):
        """Append annotation columns to field header"""
        a_count = 0

        for a in annotations:
            field_header.append(a.capitalize())
            a_count += 1

        return a_count

    def add_annotations(row, annotations):
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

            add_val(row, val, unit=unit, link=link, tooltip=tooltip)

    # TODO: Expand to support Process objects
    def add_element(row, top_header, field_header, material, first_row):
        if first_row:
            # Add material headers
            field_header.append('Name')  # Material name
            field_count = 1

            # Characteristics
            field_count += add_annotation_headers(
                field_header, material.characteristics)

            # Factor values
            if material.item_type == 'SAMPLE':
                field_count += add_annotation_headers(
                    field_header, material.factor_values)

            add_top_header(top_header, material.item_type, field_count)

        # Material columns
        add_val(row, material.name)  # Material name
        add_annotations(row, material.characteristics)  # Characteristics

        if material.item_type == 'SAMPLE':
            add_annotations(row, material.factor_values)

    ############
    # Rendering
    ############

    first_row = True
    first_arc = True

    ##########
    # Sources
    ##########
    sources = assay.get_sources()

    for source in sources:
        row = []
        source_section = []

        add_element(
            source_section, top_header, field_header, source, first_row)
        row += source_section

        ##########
        # Samples
        ##########

        for sample in [
                s for s in assay.get_samples() if source in s.get_sources()]:
            sample_section = []

            add_element(
                sample_section, top_header, field_header, sample, first_row)
            row += sample_section

            #############
            # Assay arcs
            #############
            first_arc_in_sample = True

            # Get sequences
            arcs = assay.get_arcs_by_sample(sample)

            # TODO: Ensure correct pooling/splitting

            # TODO: Refactor arcs

            # Iterate through arcs
            for arc in arcs:
                col_obj = arc.get_head_obj()

                while col_obj:
                    if not first_arc_in_sample:
                        row = []
                        # row += source_section
                        add_repetition(row, top_header, 1)
                        row += sample_section

                    ##########
                    # Process
                    ##########
                    if type(col_obj) == Process:
                        # TODO: Build using add_element
                        # Process headers
                        if first_arc:
                            field_count = 0

                            # Protocol name
                            if col_obj.protocol:
                                field_header.append('Protocol')
                                field_count += 1

                            # Process name
                            field_header.append('Name')     # Name
                            field_count += 1

                            # Param values
                            field_count += add_annotation_headers(
                                field_header, col_obj.parameter_values)

                            add_top_header(
                                top_header, 'PROCESS', field_count)

                        # Protocol name
                        if col_obj.protocol:
                            add_val(row, col_obj.protocol.name)

                        add_val(row, col_obj.name)          # Process name
                        # Param values
                        add_annotations(row, col_obj.parameter_values)

                    ###########
                    # Material
                    ###########
                    elif type(col_obj) == GenericMaterial:
                        # TODO: Build using add_element
                        # Material headers
                        if first_arc:
                            field_header.append('Name')     # Name
                            field_count = 1
                            # Characteristics
                            field_count += add_annotation_headers(
                                field_header, col_obj.characteristics)

                            add_top_header(
                                top_header, col_obj.item_type, field_count)

                        add_val(row, col_obj.name)          # Name
                        # Characteristics
                        add_annotations(row, col_obj.characteristics)

                    next_arcs = arc.go_forward()

                    if next_arcs:
                        arc = arc.go_forward()[0]
                        col_obj = arc.get_head_obj()

                    else:
                        col_obj = None

                # Add row to table
                # print('Row: {}'.format(row))    # DEBUG
                table_data.append(row)
                first_arc = False
                first_arc_in_sample = False
                first_row = False

    return {
        'top_header': top_header,
        'field_header': field_header,
        'table_data': table_data}


def render_top_header(section):
    """
    Render section of top header
    :param section: Header section (dict)
    :return: String (contains HTML)
    """
    return '<th class="bg-{} text-nowrap text-white" colspan="{}">' \
           '{}</th>\n'.format(
            section['colour'],
            section['colspan'],
            section['legend'])


def render_assay_cell(cell):
    """
    Return assay table cell as HTML
    :param cell: Assay cell
    :return: String (contains HTML)
    """
    if cell['repeat']:
        return '<td class="bg-light text-muted text-center">"</td>\n'

    if cell['tooltip']:
        ret = '<td title="{}" data-toggle="tooltip" ' \
              'data-placement="top">'.format(cell['tooltip'])

    else:
        ret = '<td>'

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
