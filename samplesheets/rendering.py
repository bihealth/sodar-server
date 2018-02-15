"""Rendering helpers for samplesheets"""


HEADER_COLOURS = {
    'source': 'info',
    'sample': 'warning',
    'process': 'danger',
    'material': 'success'}


def get_assay_table(assay):
    """
    Return data grid for a "simple" HTML assay table
    :param assay: Assay object
    :return: Dict
    """

    assay_table = []
    top_header = []
    field_header = []

    def add_top_header(top_header, title, colspan):
        """Append columns to top header"""
        top_header.append({
            'title': title,
            'colour': HEADER_COLOURS[title.lower()],
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

    def add_repetition(row, colspan):
        """Append repetition columns"""
        for i in range(0, colspan):
            add_val(row, repeat=True)

    def add_char_header(field_header, material):
        """Append characteristics columns to field header"""
        char_count = 0

        for c in material.characteristics:
            category = assay.study.get_characteristic_cat(c)
            field_header.append(category['annotationValue'])
            char_count += 1

        return char_count

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

    def add_factor_header(field_header, material):
        """Append factor value columns to field header"""
        factor_count = 0

        for fv in material.factor_values:
            factor = assay.study.get_factor(fv)
            field_header.append(
                factor['factorName'].capitalize())
            factor_count += 1

        return factor_count

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

    first_source = True
    first_sample = True
    first_seq = True

    ##########
    # Sources
    ##########
    sources = assay.get_sources()

    for source in sources:
        row = []

        # Build source header
        if first_source:
            field_header.append('Name')     # Name column
            field_count = add_char_header(field_header, source) + 1
            add_top_header(top_header, 'source', field_count)
            first_source = False

        # Add source columns
        add_val(row, source.name)    # Name column
        add_chars(row, source)       # Characteristics

        ################
        # Source Samples
        ################
        first_sample_in_source = True

        for sample in [
                s for s in assay.get_samples() if source in s.get_sources()]:

            # Build sample header
            if first_sample:
                field_header.append('Name')     # Name column
                field_count = 1

                # Characteristics
                field_count += add_char_header(field_header, sample)

                # Factor values
                field_count += add_factor_header(field_header, sample)

                add_top_header(top_header, 'sample', field_count)
                first_sample = False

            if not first_sample_in_source:
                row = []
                add_repetition(row, top_header['sources']['colspan'])

            # Add sample columns
            add_val(row, sample.name)
            add_chars(row, sample)
            add_factors(row, sample)

            ##################
            # Assay sequences
            ##################
            if first_seq:
                add_top_header(top_header, 'process', 1)
                field_header.append('Something')    # TODO
                first_seq = False

            add_val(row, 'some value')

            # Add row to table
            # print('Row: {}'.format(row))    # DEBUG
            first_sample_in_source = False
            assay_table.append(row)

    # Apparently Django doesn't support multiple return objects from a tag
    return {
        'top_header': top_header,
        'field_header': field_header,
        'assay_table': assay_table}


def render_top_header(section):
    """
    Render section of top header
    :param section: Header section (dict)
    :return: String (contains HTML)
    """
    return '<th class="bg-{} text-white" colspan="{}">{}</th>\n'.format(
        section['colour'],
        section['colspan'],
        section['title'].capitalize())


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

    if cell['unit']:
        ret += '<span class="pull-right text-muted">{}</span>'.format(
            cell['unit'])

    ret += '</td>\n'
    return ret
