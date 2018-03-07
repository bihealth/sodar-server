"""Import and export utilities for the samplesheets app"""

from altamisa.isatab import InvestigationReader, StudyReader, AssayReader
import io
import logging
from typing import NamedTuple

from django.db import connection

from .models import Investigation, Study, Assay, GenericMaterial, Protocol, \
    Process, Arc


# Local constants
ALTAMISA_MATERIAL_TYPE_SAMPLE = 'Sample Name'

MATERIAL_TYPE_MAP = {
    'Source Name': 'SOURCE',
    'Sample Name': 'SAMPLE',
    'Extract Name': 'MATERIAL',
    'Labeled Extract Name': 'MATERIAL',
    'Raw Data File': 'DATA',        # HACK: File subtypes should be in their own
    'Derived Data File': 'DATA',    # field instead of material.type
    'Image File': 'DATA',
    'Acquisition Parameter Data File': 'DATA',
    'Derived Spectral Data File': 'DATA',
    'Protein Assignment File': 'DATA',
    'Raw Spectral Data File': 'DATA',
    'Peptide Assignment File': 'DATA',
    'Array Data File': 'DATA',
    'Derived Array Data File': 'DATA',
    'Post Translational Modification Assignment File': 'DATA',
    'Derived Array Data Matrix File': 'DATA',
    'Free Induction Decay Data File': 'DATA',
    'Metabolite Assignment File': 'DATA',
    'Array Data Matrix File': 'DATA'}


logger = logging.getLogger(__name__)


# Importing --------------------------------------------------------------------


def import_isa(isa_zip, project):
    """
    Import ISA investigation and its studies/assays from an ISAtab Zip archive
    into the Django database, utilizing the altamISA parser
    :param isa_zip: ZipFile (archive containing a single ISAtab investigation)
    :param project: Project object
    :return: Django Investigation object
    """

    # ASYNC HACK
    connection.close()

    logger.info('Importing investigation from a Zip archive..')

    ######################
    # Parse Zip archive
    ######################

    def get_file(zip_file, file_name):
        file = zip_file.open(str(file_name), 'r')
        return io.TextIOWrapper(file)

    # Parse investigation
    inv_file_name = get_inv_file_name(isa_zip)

    input_file = get_file(isa_zip, inv_file_name)
    isa_inv = InvestigationReader.from_stream(input_file).read()

    ###################
    # Helper functions
    ###################

    # TODO: Move inside get_ontology_vals?
    def get_multitype_val(o):
        """Get value where the member type can vary"""
        return o._asdict() if isinstance(o, tuple) else o

    def get_ontology_vals(vals):
        """Get value data from porential ontology references"""
        ret = {}

        for v in vals:
            ret[v.name] = {
                'unit': get_multitype_val(v.unit),
                'value': get_multitype_val(v.value)}

        return ret

    def get_tuple_list(tuples):
        """Get list of dicts from tuples for JSONField"""
        if type(tuples) == dict:
            return [get_multitype_val(v) for v in tuples.values()]

        elif type(tuples) in [tuple, list]:
            return[get_multitype_val(v) for v in tuples]

    def get_header(header):
        """Get list of dicts from an object list for JSONField"""
        ret = []

        for h in header:
            h_ret = h.__dict__

            if h_ret['term_source_ref_header']:
                h_ret['term_source_ref_header'] = \
                    h_ret['term_source_ref_header'].__dict__

            if h_ret['unit_header']:
                h_ret['unit_header'] = h_ret['unit_header'].__dict__

            ret.append(h_ret)

        return ret

    def import_materials(materials, db_parent):
        """
        Create material objects in Django database.
        :param materials: altamISA materials dict
        :param db_parent: Parent Django db object (Assay or Study)
        """
        for m in materials.values():
            item_type = MATERIAL_TYPE_MAP[m.type]

            # Common values
            values = {
                'api_id': id(m),     # TODO: Remove api_id?
                'item_type': item_type}

            # Name
            if hasattr(m, 'name'):
                values['name'] = m.name

            # Parent
            if type(db_parent) == Study:
                values['study'] = db_parent

            elif type(db_parent) == Assay:
                values['study'] = db_parent.study
                values['assay'] = db_parent

            # Type
            # HACK since file/extract subtype is in .type
            if item_type in ['DATA', 'MATERIAL'] or m.material_type:
                values['material_type'] = m.type

            # TODO: TBD: Separate field for label?
            elif m.label:
                values['material_type'] = m.label

            # Characteristics
            if m.characteristics:
                values['characteristics'] = get_ontology_vals(m.characteristics)

            # Factor values
            if m.factor_values:
                values['factor_values'] = get_ontology_vals(m.factor_values)

            material_obj = GenericMaterial(**values)
            material_obj.save()
            logger.debug('Added material "{}" ({}) to "{}"'.format(
                material_obj.name, item_type, db_parent.get_name()))

    def import_processes(processes, db_parent):
        """
        Create processes of a process sequence in the database.
        :param processes: Process sequence of a study or an assay in altamISA
        :param db_parent: Parent study or assay
        """
        study = db_parent if type(db_parent) == Study else db_parent.study

        for p in processes.values():
            # Link protocol
            protocol = None

            if p.protocol_ref != 'UNKNOWN':
                try:
                    protocol = Protocol.objects.get(
                        study=study,
                        name=p.protocol_ref)

                except Protocol.DoesNotExist:
                    logger.error(
                        'No protocol found for process "{}" '
                        'with ref "{}"'.format(
                            p.name, p.protocol_ref))

            else:
                logger.debug(
                    'Unknown protocol for process "{}"'.format(p.name))

            values = {
                'api_id': id(p),    # TODO: Remove api_id?
                'name': p.name,
                'protocol': protocol,
                'assay': db_parent if type(db_parent) == Assay else None,
                'study': db_parent if type(db_parent) == Study else None,
                'performer': p.performer,
                'perform_date': p.date,
                'array_design_ref': p.array_design_ref,
                'scan_name': p.scan_name,
                'comments': []}     # TODO

            # Parameter values
            if p.parameter_values:
                values['parameter_values'] = get_ontology_vals(
                    p.parameter_values)

            process = Process(**values)
            process.save()
            logger.debug('Added process "{}" to "{}"'.format(
                process.name, db_parent.get_name()))

    def import_arcs(arcs, db_parent):
        """
        Create process/material arcs according to the altamISA structure
        :param arcs: Tuple
        :param db_parent: Study or Assay object
        """
        def find_by_name(name):
            """
            Find GenericMaterial or Process object by name
            :param name: Name (string)
            :return: GenericMaterial or Process object
            :raise: ValueError if not found
            """
            query_params = {
                'name': name}

            # TODO: DEMO HACK: Recognize samples by name
            if name.find('sample') == 0:
                query_params['study'] = db_parent if \
                    type(db_parent) == Study else db_parent.study

            else:
                parent_query_arg = db_parent.__class__.__name__.lower()
                query_params[parent_query_arg] = db_parent

            try:
                return GenericMaterial.objects.get(**query_params)

            except GenericMaterial.DoesNotExist:
                try:
                    return Process.objects.get(**query_params)

                except Process.DoesNotExist:
                    raise ValueError(
                        'No GenericMaterial or Process found with '
                        'name={}'.format(name))

        for a in arcs:
            try:
                tail_obj = find_by_name(a.tail)
                head_obj = find_by_name(a.head)

            except ValueError as ex:
                raise ValueError('{} / arc = {}'.format(ex, a))

            # TODO: This is now done in two ways, see ARC_OBJ_SUFFIX_MAP
            tail_obj_arg = 'tail_{}'.format(
                'material' if type(tail_obj) == GenericMaterial else 'process')
            head_obj_arg = 'head_{}'.format(
                'material' if type(head_obj) == GenericMaterial else 'process')

            values = {
                'assay': db_parent if type(db_parent) == Assay else None,
                'study': db_parent if
                type(db_parent) == Study else db_parent.study,
                tail_obj_arg: tail_obj,
                head_obj_arg: head_obj}

            arc = Arc(**values)
            arc.save()
            logger.debug('Added arc "{} -> {}" to "{}"'.format(
                tail_obj.name, head_obj.name, db_parent.get_name()))

    #########
    # Import
    #########

    # Create investigation
    values = {
        'project': project,
        'identifier': isa_inv.info.identifier,
        'title': (isa_inv.info.title or project.title),
        'description': (isa_inv.info.description or project.description),
        'file_name': inv_file_name,
        'ontology_source_refs': get_tuple_list(isa_inv.ontology_source_refs),
        'comments': [],     # TODO
        'status': 'IMPORTING'}

    db_investigation = Investigation(**values)
    db_investigation.save()
    logger.debug('Created investigation "{}"'.format(db_investigation.title))

    # Create studies
    for s_i in isa_inv.studies:
        # Parse study file
        s = StudyReader.from_stream(
            isa_inv, get_file(isa_zip, s_i.info.path)).read()

        values = {
            'api_id': id(s),                    # TODO: Remove api_id?
            'identifier': s_i.info.identifier,
            'file_name': s_i.info.path,
            'investigation': db_investigation,
            'title': s_i.info.title,
            'study_design': s_i.designs,        # TODO
            'factors': s_i.factors,             # TODO
            'characteristic_cat': [],           # TODO
            'unit_cat': [],                     # TODO
            'comments': [],                     # TODO
            'header': get_header(s.header)}

        db_study = Study(**values)
        db_study.save()
        logger.debug('Added study "{}"'.format(db_study.title))

        # Create protocols
        # TODO: Comments
        for p_i in s_i.protocols.values():
            values = {
                'api_id': id(p_i),
                'name': p_i.name,
                'study': db_study,
                'protocol_type': get_multitype_val(p_i.type),
                'description': p_i.description,
                'uri': p_i.uri,
                'version': p_i.version,
                'parameters': get_tuple_list(p_i.parameters),
                'components': get_tuple_list(p_i.components)}

            protocol = Protocol(**values)
            protocol.save()
            logger.debug('Added protocol "{}" in study "{}"'.format(
                protocol.name, db_study.title))

        # Create study materials
        import_materials(
            s.materials, db_parent=db_study)

        # Create study processes
        import_processes(s.processes, db_parent=db_study)

        # Create study arcs
        import_arcs(s.arcs, db_parent=db_study)

        for a_i in s_i.assays.values():
            a = AssayReader.from_stream(
                isa_inv, get_file(isa_zip, a_i.path)).read()

            values = {
                'api_id': id(a),    # TODO: Remove api_id?
                'file_name': a_i.path,
                'study': db_study,
                'measurement_type': get_multitype_val(a_i.measurement_type),
                'technology_type': get_multitype_val(a_i.technology_type),
                'technology_platform': a_i.platform,
                'characteristic_cat': [],           # TODO
                'unit_cat': [],                     # TODO
                'comments': [],                     # TODO
                'header': get_header(a.header)}

            db_assay = Assay(**values)
            db_assay.save()
            logger.debug('Added assay "{}" in study "{}"'.format(
                db_assay.api_id, db_study.title))

            # Create assay materials (excluding sources and samples)
            assay_materials = {
                k: a.materials[k] for k in a.materials if
                MATERIAL_TYPE_MAP[a.materials[k].type] not in [
                    'SOURCE', 'SAMPLE']}
            import_materials(assay_materials, db_parent=db_assay)

            # Create assay processes
            import_processes(a.processes, db_parent=db_assay)

            # Create assay arcs
            import_arcs(a.arcs, db_parent=db_assay)

    logger.info('Import of investigation "{}" OK'.format(
        db_investigation.title))

    # Update investigation status
    db_investigation.status = 'OK'
    db_investigation.save()

    return db_investigation


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


# Exporting --------------------------------------------------------------------


# TODO: Export to ISAtab
