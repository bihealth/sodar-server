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
        char_count = 0

        for c in material.characteristics:
            category = assay.study.get_characteristic_cat(c)
            field_header.append(category['annotationValue'].capitalize())
            char_count += 1

        return char_count

    # TODO: Modify for altamISA
    def add_chars(row, material):
        """Append material characteristics to row columns"""
        for c in material.characteristics:
            val = ''

            if type(c['value']) == dict:
                if c['value']['termSource']:
                    val = c['value']['termSource'] + ': '
                val += c['value']['annotationValue']
                accession = c['value']['termAccession']

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

    # TODO: Modify for altamISA
    def add_param_headers(field_header, process):
        """Append parameter columns to field header"""
        param_count = 0

        for pv in process.parameter_values:
            param = process.protocol.get_parameter(pv)

            if param:
                field_header.append(
                    param['parameterName']['annotationValue'].capitalize())

            else:
                field_header.append('Unknown parameter')    # In case of failure

            param_count += 1

        return param_count

    # TODO: Modify for altamISA
    def add_param_values(row, process):
        """Append parameter values of process to row"""
        for pv in process.parameter_values:
            val = ''
            link = None

            if type(pv['value']) == dict:
                if pv['value']['termSource']:
                    val = pv['value']['termSource'] + ': '

                val += pv['value']['annotationValue']
                link = pv['value']['termAccession']

            else:
                val = pv['value']

            add_val(row, val, link=link)

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

        # Build source header
        if first_source:
            field_header.append('Name')                 # Name column
            field_count = 1
            # field_count += add_char_headers(field_header, source)
            add_top_header(top_header, 'SOURCE', field_count)
            first_source = False

        # Add source columns
        add_val(source_section, source.name)            # Name column
        # add_chars(source_section, source)               # Characteristics
        row += source_section

        ##########
        # Samples
        ##########
        first_sample_in_source = True

        for sample in [
                s for s in assay.get_samples() if source in s.get_sources()]:

            # Build sample header
            if first_sample:
                field_header.append('Name')             # Name column
                field_count = 1

                # Characteristics
                # field_count += add_char_headers(field_header, sample)

                # Factor values
                # field_count += add_factor_header(field_header, sample)

                add_top_header(top_header, 'SAMPLE', field_count)
                first_sample = False

            if not first_sample_in_source:
                row = []
                # row += source_section
                add_repetition(row, top_header, 1)

            # Add sample columns
            sample_section = []
            add_val(sample_section, sample.name)
            # add_chars(sample_section, sample)
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
                head_obj = arc.get_head_obj()

                while head_obj:
                    if not first_arc_in_sample:
                        row = []
                        # row += source_section
                        add_repetition(row, top_header, 1)
                        row += sample_section

                    ##########
                    # Process
                    ##########
                    if type(head_obj) == Process:
                        # Process headers
                        if first_arc:
                            field_header.append('Protocol')     # Protocol name
                            field_header.append('Name')         # Process name
                            field_count = 2

                            # TODO: Process header stuff
                            # field_count += add_param_headers(
                            # field_header, process)

                            add_top_header(
                                top_header, 'PROCESS', field_count)

                        # TODO: TBD: Just hide column if protocol is unknown?
                        protocol_name = head_obj.protocol.name if \
                            head_obj.protocol else 'UNKNOWN'

                        add_val(row, protocol_name)             # Protocol name
                        add_val(row, head_obj.name)             # Process name
                        # TODO: Other Process stuff

                    ###########
                    # Material
                    ###########
                    elif type(head_obj) == GenericMaterial:
                        # Material headers
                        if first_arc:
                            field_header.append('Name')
                            field_count = 1

                            # TODO: Material header stuff

                            add_top_header(
                                top_header, head_obj.item_type, field_count)

                        add_val(row, head_obj.name)     # Material name
                        # TODO: Other material stuff

                    next_arcs = arc.go_forward()

                    if next_arcs:
                        arc = arc.go_forward()[0]
                        head_obj = arc.get_head_obj()

                    else:
                        head_obj = None

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
