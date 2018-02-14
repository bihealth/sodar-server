"""Utilities for the samplesheets app"""

import datetime as dt
from isatools.model import OntologyAnnotation, OntologySource
import logging

from .models import Investigation, Study, Assay, GenericMaterial, Protocol, \
    Process


logger = logging.getLogger(__name__)


# Importing --------------------------------------------------------------------


def import_isa(isa_inv, file_name, project):
    """
    Import ISA investigation from an ISA-API object structure into the Django
    database.
    :param isa_inv: ISA-API investigation object
    :param file_name: Name of the investigation file
    :param project: Project object
    :return: Django Investigation object
    """
    logger.debug('Importing investigation from ISA-API object structure..')

    ###################
    # Helper functions
    ###################

    def get_comments(obj):
        """Return comments from an ISA-API object as a dict for JSONfield"""
        ret = []

        for c in obj.comments:
            ret.append({'@id': id(c), 'name': c.name, 'value': c.value})

        return ret

    def get_annotation(obj):
        """Return ontology annotation dict for JSONfield"""
        if not obj.term:    # Sometimes the API produces an empty object here
            logger.debug('Empty annotation object: {}'.format(id(obj)))
            return None

        return {
            '@id': id(obj),
            'annotationValue': obj.term,
            'termAccession': obj.term_accession,
            'termSource': obj.term_source.name if
            type(obj.term_source) == OntologySource else obj.term_source}

    def import_material(material, parent, item_type):
        """
        Create a material object in Django database.
        :param material: ISA-API material object
        :param parent: Parent database object (Assay or Study)
        :param item_type: Type of GenericMaterial
        :return: GenericMaterial object
        """

        # Common values
        values = {
            'api_id': id(material),
            'item_type': item_type}

        # Name
        # For data files, the value for "name" is stored under "filename"
        if hasattr(material, 'name'):
            values['name'] = material.name

        elif hasattr(material, 'filename'):
            values['name'] = material.filename

        # Parent
        if type(parent) == Study:
            values['study'] = parent

        elif type(parent) == Assay:
            values['assay'] = parent

        # Type/label
        # For data files, "type" is included as "label"
        if hasattr(material, 'type'):
            values['material_type'] = material.type

        elif hasattr(material, 'label'):
            values['material_type'] = material.label

        if hasattr(material, 'characteristics'):
            values['characteristics'] = [{
                'category': {'@id': id(x.category)},
                'value': get_annotation(x.value) if
                type(x.value) == OntologyAnnotation else x.value} for
                x in material.characteristics]

        if hasattr(material, 'factor_values'):
            factor_values = []

            for fv in material.factor_values:
                export_value = {
                    'category': {
                        '@id': id(fv.factor_name)}}

                if type(fv.value) == OntologyAnnotation:
                    export_value['value'] = get_annotation(fv.value)

                else:
                    export_value['value'] = str(fv.value)

                if fv.unit:
                    export_value['unit'] = {'@id': id(fv.unit)}

                factor_values.append(export_value)

            values['factor_values'] = factor_values

        material_obj = GenericMaterial(**values)
        material_obj.save()
        logger.debug('Added material "{}" ({})'.format(
            material_obj.name, item_type))

        return material_obj

    def import_processes(sequence, parent):
        """
        Create processes of a process sequence in the database.
        :param sequence: Process sequence of a study or an assay
        :param parent: Parent study or assay
        :return: Process object (first process)
        """
        first_process = None
        prev_process = None
        study = parent if type(parent) == Study else parent.study

        for p in sequence:
            protocol = Protocol.objects.get(
                study=study,
                api_id=id(p.executes_protocol))

            values = {
                'api_id': id(p),
                'name': p.name,
                'protocol': protocol,
                'assay': parent if type(parent) == Assay else None,
                'study': parent if type(parent) == Study else None,
                'previous_process': prev_process,
                'performer': p.performer,
                'perform_date': (
                    dt.datetime.strptime(p.date, '%Y-%m-%d').date() if
                    p.date else None),
                'comments': get_comments(p)}

            if p.parameter_values:
                param_values = []

                for pv in p.parameter_values:
                    export_value = {
                        'category': {
                            '@id': id(pv.category.parameter_name)}}

                    if type(pv.value) == OntologyAnnotation:
                        export_value['value'] = get_annotation(pv.value)

                    else:
                        export_value['value'] = str(pv.value)

                    if pv.unit:
                        export_value['unit'] = {'@id': id(pv.unit)}

                    param_values.append(export_value)

                values['parameter_values'] = param_values

            process = Process(**values)
            process.save()
            logger.debug('Added process "{}" to "{}"'.format(
                process.api_id, parent.api_id))

            if not first_process:
                first_process = process

            # Link inputs
            for i in p.inputs:
                input_material = GenericMaterial.objects.find_child(
                    parent, id(i))

                process.inputs.add(input_material)
                logger.debug('Linked input material "{}"'.format(
                    input_material.api_id))

            # Link outputs
            for o in p.outputs:
                output_material = GenericMaterial.objects.find_child(
                    parent, id(o))

                process.outputs.add(output_material)
                logger.debug('Linked output material "{}"'.format(
                    output_material.api_id))

            prev_process = process

        return first_process

    ############
    # Importing
    ############

    # Create investigation
    values = {
        'project': project,
        'identifier': isa_inv.identifier,
        'title': (isa_inv.title or project.title),
        'description': (isa_inv.description or project.description),
        'file_name': file_name,
        'ontology_source_refs': [],
        'comments': get_comments(isa_inv)}

    # Add ontology source refs
    for name in isa_inv.get_ontology_source_reference_names():
        ref = isa_inv.get_ontology_source_reference(name)
        values['ontology_source_refs'].append({
            'name': ref.name,
            'description': ref.description,
            'file': ref.file,
            'version': ref.version})

    investigation = Investigation(**values)
    investigation.save()
    logger.debug('Created investigation "{}"'.format(investigation.title))

    # Create studies
    for s in isa_inv.studies:
        values = {
            'api_id': id(s),
            'identifier': s.identifier,
            'file_name': s.filename,
            'investigation': investigation,
            'title': s.title,
            'study_design': [
                get_annotation(x) for x in s.design_descriptors],
            'factors': [{
                '@id': id(x),
                'factorName': x.name,
                'factorType': get_annotation(x.factor_type)} for
                x in s.factors],
            'characteristic_cat': [{
                '@id': id(x),
                'characteristicType': get_annotation(x)} for
                x in s.characteristic_categories],
            'unit_cat': [get_annotation(x) for x in s.units],
            'comments': get_comments(s)}

        study = Study(**values)
        study.save()
        logger.debug('Added study "{}"'.format(study.api_id))

        # Create protocols
        for p in s.protocols:
            values = {
                'api_id': id(p),
                'name': p.name,
                'study': study,
                'protocol_type': get_annotation(p.protocol_type),
                'description': p.description,
                'uri': p.uri,
                'version': p.version,
                'parameters': [{
                    '@id': id(x),
                    'parameterName': get_annotation(x.parameter_name)} for
                    x in p.parameters],
                'components': []}   # TODO: TBD: Support components?

            protocol = Protocol(**values)
            protocol.save()
            logger.debug('Added protocol "{}" in study "{}"'.format(
                protocol.name, study.file_name))

        # Create study sources
        for m in s.sources:
            import_material(m, parent=study, item_type='SOURCE')

        # Create study samples
        for m in s.samples:
            import_material(m, parent=study, item_type='SAMPLE')

        # Create other study materials
        for m in s.other_material:
            import_material(m, parent=study, item_type='MATERIAL')

        # Create study processes
        import_processes(s.process_sequence, parent=study)

        # Create assays
        for a in s.assays:
            values = {
                'api_id': id(a),
                'file_name': a.filename,
                'study': study,
                'measurement_type': get_annotation(a.measurement_type),
                'technology_type': get_annotation(a.technology_type),
                'technology_platform': a.technology_platform,
                'characteristic_cat': [
                    get_annotation(x) for x in a.characteristic_categories],
                'unit_cat': [get_annotation(x) for x in s.units],
                'comments': get_comments(a)}

            assay = Assay(**values)
            assay.save()
            logger.debug('Added assay "{}" in study "{}"'.format(
                assay.api_id, study.api_id))

            # Create assay data files
            for m in a.data_files:
                import_material(m, parent=assay, item_type='DATA')

            # Create other assay materials
            # NOTE: Samples were already created when parsing study
            for m in a.other_material:
                import_material(m, parent=assay, item_type='MATERIAL')

            # Create assay processes
            import_processes(a.process_sequence, parent=assay)

    logger.debug('Import OK')
    return investigation


# Exporting --------------------------------------------------------------------


# TODO: DEPRECATED, TO BE REPLACED


def export_isa_json(investigation):
    """
    Export ISA investigation into a dictionary corresponding to ISA JSON
    :param investigation: Investigation object
    :return: Dictionary
    """

    def get_reference(obj):
        """
        Return reference to an object for exporting
        :param obj: Any object inheriting BaseSampleSheet
        :return: Reference value as dict
        """
        return {'@id': obj.api_id}

    def export_materials(parent_obj, parent_data):
        """
        Export materials from a parent into output dict
        :param parent_obj: Study or Assay object
        :param parent_data: Parent study or assay in output dict
        """
        for material in parent_obj.materials.all():
            material_data = {
                '@id': material.api_id,
                'name': material.name}

            # Characteristics for all material types except data files
            if material.item_type != 'DATA':
                material_data['characteristics']: material.characteristics

            # Source
            if material.item_type == 'SOURCE':
                parent_data['materials']['sources'].append(material_data)

            # Sample
            elif material.item_type == 'SAMPLE':
                material_data['factorValues'] = material.factor_values
                parent_data['materials']['samples'].append(material_data)

            # Other materials
            elif material.item_type == 'MATERIAL':
                material_data['type'] = material.material_type
                parent_data['materials']['otherMaterials'].append(material_data)

            # Data files
            elif material.item_type == 'DATA':
                material_data['type'] = material.material_type
                parent_data['dataFiles'].append(material_data)

            logger.debug('Added material "{}" ({})'.format(
                material.name, material.item_type))

    def export_processes(parent_obj, parent_data):
        """
        Export process sequence from a parent into output dict
        :param parent_obj: Study or Assay object
        :param parent_data: Parent study or assay in output dict
        """
        process = parent_obj.get_first_process()

        while process:
            process_data = {
                '@id': process.api_id,
                'executesProtocol': get_reference(process.protocol),
                'parameterValues': process.parameter_values,
                'performer': process.performer,
                'date': str(
                    process.perform_date) if process.perform_date else '',
                'comments': process.comments,
                'inputs': [],
                'outputs': []}

            # The name string seems to be optional
            if process.name:
                process_data['name'] = process.name

            if hasattr(process, 'next_process') and process.next_process:
                process_data['nextProcess'] = get_reference(
                    process.next_process)

            if hasattr(process,
                       'previous_process') and process.previous_process:
                process_data['previousProcess'] = get_reference(
                    process.previous_process)

            for i in process.inputs.all():
                process_data['inputs'].append(get_reference(i))

            for o in process.outputs.all():
                process_data['outputs'].append(get_reference(o))

            parent_data['processSequence'].append(process_data)
            logger.debug('Added process "{}"'.format(process.name))

            if hasattr(process, 'next_process'):
                process = process.next_process

            else:
                process = None

    logger.debug('Exporting ISA data into JSON dict..')

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
    logger.debug('Added investigation "{}"'.format(investigation.title))

    # Studies
    for study in investigation.studies.all():
        study_data = {
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
            'materials': {
                'sources': [],
                'samples': [],
                'otherMaterials': []
            },
            'assays': [],
            'processSequence': []}

        if study.api_id:
            study_data['@id'] = study.api_id

        logger.debug('Added study "{}"'.format(study.title))

        # Protocols
        for protocol in study.protocols.all():
            protocol_data = {
                '@id': protocol.api_id,
                'name': protocol.name,
                'protocolType': protocol.protocol_type,
                'description': protocol.description,
                'uri': protocol.uri,
                'version': protocol.version,
                'parameters': protocol.parameters,
                'components': protocol.components}
            study_data['protocols'].append(protocol_data)
            logger.debug('Added protocol "{}"'.format(protocol.name))

        # Materials
        export_materials(study, study_data)

        # Processes
        export_processes(study, study_data)

        # Assays
        for assay in study.assays.all():
            assay_data = {
                'filename': assay.file_name,
                'technologyPlatform': assay.technology_platform,
                'technologyType': assay.technology_type,
                'measurementType': assay.measurement_type,
                'characteristicCategories': assay.characteristic_cat,
                'unitCategories': assay.unit_cat,
                'comments': assay.comments,
                'processSequence': [],
                'dataFiles': [],
                'materials': {
                    'samples': [],
                    'otherMaterials': []}}

            if assay.api_id:
                assay_data['@id'] = assay.api_id

            logger.debug('Added assay "{}"'.format(assay.file_name))

            # Assay materials and data files
            export_materials(assay, assay_data)

            # Assay processes
            export_processes(assay, assay_data)

            study_data['assays'].append(assay_data)

        ret['studies'].append(study_data)

    logger.debug('Export to dict OK')
    return ret


# Misc -------------------------------------------------------------------------

def get_inv_file_name(zip_file):
    """
    Return investigation file name, or None if not found
    :param zip_file: ZipFile
    :return: string or None
    """
    # TODO: HACK: Quick and ugly way, improve
    for file_name in zip_file.namelist():
        if file_name.find('i_') == 0:
            return file_name
