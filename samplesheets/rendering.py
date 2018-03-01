"""Rendering helpers for samplesheets"""


from .models import Process, GenericMaterial


# TODO: Refactor everything for altamISA import


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

    def add_char_headers(field_header, material):
        """Append characteristics columns to field header"""
        # TODO: Repetition between functions, unify
        char_count = 0

        for c in material.characteristics:
            field_header.append(c.capitalize())
            char_count += 1

        return char_count

    def add_chars(row, material):
        """Append material characteristics to row columns"""
        # TODO: Repetition between functions, unify
        for k, c in material.characteristics.items():
            val = ''

            if type(c['value']) == dict:
                if c['value']['ontology_name']:
                    val = c['value']['ontology_name'] + ': '
                val += k
                accession = c['value']['accession']

            else:
                val = c['value']
                accession = None

            add_val(row, val, link=accession)

    # TODO: Modify for altamISA
    def add_factor_header(field_header, material):
        """Append factor value columns to field header"""
        factor_count = 0

        for fv in material.factor_values:
            factor = assay.study.get_factor(fv)
            field_header.append(
                factor['factorName'].capitalize())
            factor_count += 1

        return factor_count

    # TODO: Modify for altamISA
    def add_factors(row, material):
        """Append factor values to row columns"""
        for fv in material.factor_values:
            val = ''
            unit = None
            link = None

            if type(fv['value']) == dict:
                if fv['value']['termSource']:
                    val = fv['value']['termSource'] + ': '

                val += fv['value']['annotationValue']
                link = fv['value']['termAccession']

            else:
                val = fv['value']

                if 'unit' in fv:
                    category = assay.study.get_unit_cat(fv['unit'])

                    # In case a factor value has been declared outside a sample
                    # (Should not be allowed but ISA-API fails to check for it)
                    if category:
                        unit = category['annotationValue']

            add_val(row, val, unit=unit, link=link)

    def add_param_headers(field_header, process):
        """Append parameter columns to field header"""
        param_count = 0

        for pv in process.parameter_values:
            field_header.append(pv.capitalize())
            param_count += 1

        return param_count

    def add_param_values(row, process):
        """Append parameter values of process to row"""
        for k, v in process.parameter_values.items():
            val = ''

            if type(v['value']) == dict:
                if v['value']['ontology_name']:
                    val = v['value']['ontology_name'] + ': '
                val += k
                accession = v['value']['accession']

            else:
                val = v['value']
                accession = None

            add_val(row, val, link=accession)

    # TODO: Modify for altamISA
    def add_material(row, top_header, field_header, first_seq, material):
        if material and material.item_type != 'SAMPLE':
            if first_seq:
                # Add material headers
                field_header.append('Name')  # Material name
                field_count = 1

                # Characteristics
                # field_count += add_char_headers(
                #     field_header, material)

                add_top_header(top_header, material.item_type, field_count)

            # Material columns
            add_val(row, material.name)  # Material name
            # add_chars(row, material)  # Characteristics

    ############
    # Rendering
    ############

    first_source = True
    first_sample = True
    first_arc = True

    ##########
    # Sources
    ##########
    sources = assay.get_sources()

    for source in sources:
        row = []
        source_section = []

        # Source header
        if first_source:
            field_header.append('Name')                 # Name
            field_count = 1
            field_count += add_char_headers(
                field_header, source)                   # Characteristics
            add_top_header(top_header, 'SOURCE', field_count)
            first_source = False

        # Source columns
        add_val(source_section, source.name)            # Name
        add_chars(source_section, source)               # Characteristics
        row += source_section

        ##########
        # Samples
        ##########
        first_sample_in_source = True

        for sample in [
                s for s in assay.get_samples() if source in s.get_sources()]:

            # Sample header
            if first_sample:
                field_header.append('Name')             # Name
                field_count = 1
                field_count += add_char_headers(
                    field_header, sample)               # Characteristics

                # Factor values
                # field_count += add_factor_header(field_header, sample)

                add_top_header(top_header, 'SAMPLE', field_count)
                first_sample = False

            if not first_sample_in_source:
                row = []
                # row += source_section
                add_repetition(row, top_header, 1)

            # Sample columns
            sample_section = []
            add_val(sample_section, sample.name)        # Name
            add_chars(sample_section, sample)           # Characteristics
            # add_factors(sample_section, sample)
            row += sample_section
            first_sample_in_source = False

            #############
            # Assay arcs
            #############
            first_arc_in_sample = True

            # Get sequences
            arcs = assay.get_arcs_by_sample(sample)

            # TODO: Pooling/splitting

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

                            field_count += add_param_headers(
                                field_header, col_obj)      # Param values

                            add_top_header(
                                top_header, 'PROCESS', field_count)

                        # Protocol name
                        if col_obj.protocol:
                            add_val(row, col_obj.protocol.name)

                        add_val(row, col_obj.name)          # Process name
                        add_param_values(row, col_obj)      # Param values

                    ###########
                    # Material
                    ###########
                    elif type(col_obj) == GenericMaterial:
                        # Material headers
                        if first_arc:
                            field_header.append('Name')     # Name
                            field_count = 1
                            field_count += add_char_headers(
                                field_header, col_obj)      # Characteristics

                            add_top_header(
                                top_header, col_obj.item_type, field_count)

                        add_val(row, col_obj.name)          # Name
                        add_chars(row, col_obj)             # Characteristics

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
