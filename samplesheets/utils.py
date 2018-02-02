"""Utilities for the samplesheets app"""

import logging

from .models import Investigation, Study, Assay, GenericMaterial, Protocol, \
    Process


logger = logging.getLogger(__name__)


def add_material(material, parent, item_type):
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


def add_processes(sequence, parent):
    """
    Create processes of a process sequence in the database.
    :param sequence: Process sequence of a study or an assay
    :param parent: Parent study or assay
    :return: Process object (first_process)
    """
    prev_process = None
    parent_query_arg = parent.__class__.__name__.lower()
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
            # TODO: Make this a manager function in models.py
            try:
                input_material = GenericMaterial.objects.get(
                    **{parent_query_arg: parent, 'json_id': i['@id']})

            except GenericMaterial.DoesNotExist:    # Sample
                input_material = GenericMaterial.objects.get(
                    study=study, json_id=i['@id'])

            process.inputs.add(input_material)
            logging.debug('Linked input material "{}"'.format(
                input_material.json_id))

        # Link outputs
        for o in p['outputs']:
            try:
                output_material = GenericMaterial.objects.get(
                    **{parent_query_arg: parent, 'json_id': o['@id']})

            except GenericMaterial.DoesNotExist:    # Sample
                output_material = GenericMaterial.objects.get(
                    study=study, json_id=o['@id'])

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
    :param data: JSON data as a dictionary
    :param file_name: Name of the investigation file
    :param project: Project object
    :return: Investigation object
    """

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
            add_material(m, parent=study, item_type='SOURCE')

        # Create study samples
        for m in s['materials']['samples']:
            add_material(m, parent=study, item_type='SAMPLE')

        # Create other study materials
        for m in s['materials']['otherMaterials']:
            add_material(m, parent=study, item_type='MATERIAL')

        # Create study processes
        add_processes(s['processSequence'], parent=study)

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
                add_material(m, parent=assay, item_type='DATA')

            # Create other assay materials
            # NOTE: Samples were already created when parsing study
            for m in a['materials']['otherMaterials']:
                add_material(m, parent=assay, item_type='MATERIAL')

            # Create assay processes
            add_processes(a['processSequence'], parent=assay)

    return investigation
