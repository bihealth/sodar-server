"""Utilities for the samplesheets app"""

import logging

from .models import Investigation, Study, Assay, GenericMaterial, Protocol, \
    Process


logger = logging.getLogger(__name__)


# Importing --------------------------------------------------------------------


def import_material(material, parent, item_type):
    """
    Create a material object in Django database.
    :param material: Material dictionary from ISA JSON
    :param parent: Parent database object (Assay or Study)
    :param item_type: Type of GenericMaterial
    :return: GenericMaterial object
    """

    # Common values
    values = {
        'json_id': material['@id'],
        'item_type': item_type,
        'name': material['name'],
        'characteristics': (material['characteristics'] if
                            item_type != 'DATA' else dict())}

    if type(parent) == Study:
        values['study'] = parent

    elif type(parent) == Assay:
        values['assay'] = parent
        values['study'] = parent.study

    if 'type' in material:
        values['material_type'] = material['type']

    if 'characteristics' in material:
        values['characteristics'] = material['characteristics']

    if 'factor_values' in material:
        values['factor_values'] = material['factorValues']

    material_obj = GenericMaterial(**values)
    material_obj.save()
    logging.debug('Added material "{}" ({})'.format(
        material_obj.name, item_type))

    return material_obj


def import_processes(sequence, parent):
    """
    Create processes of a process sequence in the database.
    :param sequence: Process sequence of a study or an assay
    :param parent: Parent study or assay
    :return: Process object (first_process)
    """
    prev_process = None
    study = parent if type(parent) == Study else parent.study

    for p in sequence:
        protocol = Protocol.objects.get(
            study=study,
            json_id=p['executesProtocol']['@id'])

        values = {
            'json_id': p['@id'],
            'protocol': protocol,
            'previous_process': prev_process,
            'parameter_values': p['parameterValues'],
            'performer': p['performer'],
            'perform_date': None,  # TODO
            'comments': p['comments']}

        process = Process(**values)
        process.save()
        logging.debug('Added process "{}" to "{}"'.format(
            process.json_id, parent.json_id))

        # Link inputs
        for i in p['inputs']:
            input_material = GenericMaterial.objects.find_child(
                parent, i['@id'])

            process.inputs.add(input_material)
            logging.debug('Linked input material "{}"'.format(
                input_material.json_id))

        # Link outputs
        for o in p['outputs']:
            output_material = GenericMaterial.objects.find_child(
                parent, o['@id'])

            process.outputs.add(output_material)
            logging.debug('Linked output material "{}"'.format(
                output_material.json_id))

        if not prev_process:
            parent.first_process = process
            parent.save()
            logging.debug('Set process "{}" as first_process in "{}"'.format(
                process.json_id, parent.json_id))

        prev_process = process


def import_isa(data, file_name, project):
    """
    Import ISA investigation from JSON data and create relevant objects in
    the Django database.
    :param file_name: Name of the investigation file
    :param project: Project object
    :return: Investigation object
    """
    logging.debug('Importing investigation..')

    # Create investigation
    values = {
        'project': project,
        'identifier': data['identifier'],
        'title': (data['title'] or project.title),
        'description': (data['description'] or
                        project.description),
        'file_name': file_name,
        'ontology_source_refs': data['ontologySourceReferences'],
        'comments': data['comments']}

    investigation = Investigation(**values)
    investigation.save()
    logging.debug('Created investigation "{}"'.format(investigation.title))

    # Create studies
    for s in data['studies']:
        values = {
            'json_id': s['@id'],
            'identifier': s['identifier'],
            'file_name': s['filename'],
            'investigation': investigation,
            'title': s['title'],
            'study_design': s['studyDesignDescriptors'],
            'factors': s['factors'],
            'characteristic_cat': s['characteristicCategories'],
            'unit_cat': s['unitCategories'],
            'comments': s['comments']}

        study = Study(**values)
        study.save()
        logging.debug('Added study "{}"'.format(study.json_id))

        # Create protocols
        for p in s['protocols']:
            values = {
                'json_id': p['@id'],
                'name': p['name'],
                'study': study,
                'protocol_type': p['protocolType'],
                'description': p['description'],
                'uri': p['uri'],
                'version': p['version'],
                'parameters': p['parameters'],
                'components': p['components']}

            protocol = Protocol(**values)
            protocol.save()
            logging.debug('Added protocol "{}" in study "{}"'.format(
                protocol.json_id, study.json_id))

        # Create study sources
        for m in s['materials']['sources']:
            import_material(m, parent=study, item_type='SOURCE')

        # Create study samples
        for m in s['materials']['samples']:
            import_material(m, parent=study, item_type='SAMPLE')

        # Create other study materials
        for m in s['materials']['otherMaterials']:
            import_material(m, parent=study, item_type='MATERIAL')

        # Create study processes
        import_processes(s['processSequence'], parent=study)

        # Create assays
        for a in s['assays']:
            values = {
                'json_id': a['@id'],
                'file_name': a['filename'],
                'study': study,
                'measurement_type': a['measurementType'],
                'technology_type': a['technologyType'],
                'technology_platform': a['technologyPlatform'],
                'characteristic_cat': a['characteristicCategories'],
                'unit_cat': a['unitCategories'],
                'comments': a['comments'] if 'comments' in a else []}

            assay = Assay(**values)
            assay.save()
            logging.debug('Added assay "{}" in study "{}"'.format(
                assay.json_id, study.json_id))

            # Create assay data files
            for m in a['dataFiles']:
                import_material(m, parent=assay, item_type='DATA')

            # Create other assay materials
            # NOTE: Samples were already created when parsing study
            for m in a['materials']['otherMaterials']:
                import_material(m, parent=assay, item_type='MATERIAL')

            # Create assay processes
            import_processes(a['processSequence'], parent=assay)

    logging.debug('Import OK')
    return investigation


# Exporting --------------------------------------------------------------------


def get_reference(obj):
    """
    Return reference to an object for exporting
    :param obj: Any object inheriting BaseSampleSheet
    :return: Reference value as dict
    """
    return {'@id': obj.json_id}


def export_materials(parent_obj, parent_data):
    """
    Export materials from a parent into output dict
    :param parent_obj: Study or Assay object
    :param parent_data: Parent study or assay in output dict
    """
    for material in parent_obj.materials:
        material_data = {
            '@id': material.json_id,
            'mame': material.name}

        # Characteristics for all material types except data files
        if material.item_type != 'DATA':
            material_data['characteristics']: material.characteristics

        # Source
        if material.item_type == 'SOURCE':
            parent_data['sources'].append(material_data)

        # Sample
        elif material.item_type == 'SAMPLE':
            material_data['factorValues'] = material.factor_values
            parent_data['samples'].append(material_data)

        # Other materials
        elif material.item_type == 'MATERIAL':
            material_data['type'] = material.material_type
            parent_data['otherMaterials'].append(material_data)

        # Data files
        elif material.item_type == 'DATA':
            material_data['type'] = material.material_type
            parent_data['dataFiles'].append(material_data)

        logging.debug('Added material "{}" ({})'.format(
            material.name, material.item_type))


def export_processes(parent_obj, parent_data):
    """
    Export process sequence from a parent into output dict
    :param parent_obj: Study or Assay object
    :param parent_data: Parent study or assay in output dict
    """
    process = parent_obj.first_process

    while process:
        process_data = {
            '@id': process.json_id,
            'name': process.name,
            'executesProtocol': get_reference(process.protocol),
            'parameterValues': process.parameter_values,
            'performer': process.performer,
            'date': process.perform_date,
            'comments': process.comments,
            'inputs': [],
            'outputs': []}

        if process.next_process:
            process_data['nextProcess'] = get_reference(process.next_process)

        if process.previous_process:
            process_data['previousProcess'] = get_reference(
                process.previous_process)

        for i in process.inputs:
            process_data['inputs'].append(get_reference(i))

        for o in process.outputs:
            process_data['outputs'].append(get_reference(o))

        parent_data['processSequence'].append(process_data)
        logging.debug('Added process "{}"'.format(process.name))
        process = process.next_process


def export_isa(investigation):
    """
    Export ISA investigation into a dictionary corresponding to ISA JSON
    :param investigation: Investigation object
    :return: Dictionary
    """
    logging.debug('Exporting ISA data..')

    # Investigation properties
    ret = {
        'identifier': investigation.identifier,
        'title': investigation.title,
        'description': investigation.description,
        'filename': investigation.file_name,
        'ontologySourceReferences': investigation.ontology_source_refs,
        'comments': investigation.comments,
        'submissionDate': '',
        'publicReleaseDate': '',
        'studies': [],
        'publications': [],
        'people': []}
    logging.debug('Added investigation "{}"'.format(investigation.title))

    # Studies
    for study in investigation.studies:
        study_data = {
            '@id': study.json_id,
            'identifier': study.identifier,
            'filename': study.file_name,
            'title': study.title,
            'description': study.description,
            'studyDesignDescriptors': study.study_design,
            'factors': study.factors,
            'characteristicCategories': study.characteristic_cat,
            'unitCategories': study.unit_cat,
            'submissionDate': '',
            'publicReleaseDate': '',
            'comments': study.comments,
            'protocols': [],
            'sources': [],
            'samples': [],
            'otherMaterials': [],
            'assays': [],
            'processSequence': []}
        logging.debug('Added study "{}"'.format(study.title))

        # Protocols
        for protocol in study.protocols:
            protocol_data = {
                '@id': protocol.json_id,
                'name': protocol.name,
                'protocolType': protocol.protocol_type,
                'description': protocol.description,
                'uri': protocol.uri,
                'version': protocol.version,
                'parameters': protocol.parameters,
                'components': protocol.components}
            study_data['protocols'].append(protocol_data)
            logging.debug('Added protocol "{}"'.format(protocol.name))

        # Materials
        export_materials(study, study_data)

        # Processes
        export_processes(study, study_data)

        # Assays
        for assay in study.assays:
            assay_data = {
                '@id': assay.json_id,
                'filename': assay.file_name,
                'technologyPlatform': assay.technology_platform,
                'technologyType': assay.technology_type,
                'measurementType': assay.measurement_type,
                'characteristicCategories': assay.characteristic_cat,
                'unitCategories': assay.unit_cat,
                'comments': assay.comments,
                'processSequence': [],
                'dataFiles': []}
            logging.debug('Added assay "{}"'.format(assay.filename))

            # Assay materials and data files
            export_materials(assay, assay_data)

            # Assay processes
            export_processes(assay, assay_data)

            study_data['assays'].append(assay_data)

        ret['studies'].append(study_data)

    logging.debug('Export to dict OK')
    return ret
