"""Import and export utilities for the samplesheets app"""

from altamisa.isatab import InvestigationReader, StudyReader, AssayReader
import io
import logging
import time

from django.db import connection

from .models import Investigation, Study, Assay, GenericMaterial, Protocol, \
    Process, Arc, ARC_OBJ_SUFFIX_MAP

from .rendering import render_investigation


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

SAMPLE_SEARCH_SUBSTR = '-sample-'


logger = logging.getLogger(__name__)


# Importing --------------------------------------------------------------------


def import_isa(isa_zip, project, async=False):
    """
    Import ISA investigation and its studies/assays from an ISAtab Zip archive
    into the Django database, utilizing the altamISA parser
    :param isa_zip: ZipFile (archive containing a single ISAtab investigation)
    :param project: Project object
    :param async: Async HACK enabled (boolean)
    :return: Django Investigation object
    """
    t_start = time.time()

    # ASYNC HACK, to be replaced
    if async:
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
    isa_inv = InvestigationReader.from_stream(
        input_file=input_file).read()

    ###################
    # Helper functions
    ###################

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

    def import_materials(materials, db_parent, obj_lookup):
        """
        Create material objects in Django database.
        :param materials: altamISA materials dict
        :param db_parent: Parent Django db object (Assay or Study)
        :param obj_lookup: Dictionary for in-memory lookup
        """
        for m in materials.values():
            item_type = MATERIAL_TYPE_MAP[m.type]

            # Common values
            values = {
                'item_type': item_type}

            # Name
            if hasattr(m, 'name'):
                values['name'] = m.name

            # Unique name
            if hasattr(m, 'unique_name'):
                values['unique_name'] = m.unique_name

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
            elif m.extract_label:
                values['material_type'] = m.extract_label

            # Characteristics
            if m.characteristics:
                values['characteristics'] = get_ontology_vals(m.characteristics)

            # Factor values
            if m.factor_values:
                values['factor_values'] = get_ontology_vals(m.factor_values)

            # Comments
            values['comments'] = get_ontology_vals(m.comments)

            material_obj = GenericMaterial(**values)
            material_obj.save()
            obj_lookup[material_obj.unique_name] = material_obj
            logger.debug('Added material "{}" ({}) to "{}"'.format(
                material_obj.unique_name, item_type, db_parent.get_name()))

    def import_processes(processes, db_parent, obj_lookup):
        """
        Create processes of a process sequence in the database.
        :param processes: Process sequence of a study or an assay in altamISA
        :param db_parent: Parent study or assay
        :param obj_lookup: Dictionary for in-memory lookup
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
                    logger.warning(
                        'No protocol found for process "{}" '
                        'with ref "{}"'.format(
                            p.unique_name, p.protocol_ref))

            else:
                logger.debug(
                    'Unknown protocol for process "{}"'.format(p.unique_name))

            values = {
                'name': p.name,
                'unique_name': p.unique_name,
                'protocol': protocol,
                'assay': db_parent if type(db_parent) == Assay else None,
                'study': db_parent if type(db_parent) == Study else None,
                'performer': p.performer,
                'perform_date': p.date,
                'array_design_ref': p.array_design_ref,
                'scan_name': p.scan_name,
                'comments': get_ontology_vals(p.comments)}

            # Parameter values
            if p.parameter_values:
                values['parameter_values'] = get_ontology_vals(
                    p.parameter_values)

            process = Process(**values)
            process.save()
            obj_lookup[process.unique_name] = process
            logger.debug('Added process "{}" to "{}"'.format(
                process.unique_name, db_parent.get_name()))

    def import_arcs(arcs, db_parent, obj_lookup):
        """
        Create process/material arcs according to the altamISA structure
        :param arcs: Tuple
        :param db_parent: Study or Assay object
        :param obj_lookup: Lookup dict for materials and processes
        """
        def find_by_name(unique_name):
            """
            Find GenericMaterial or Process object by name
            :param unique_name: Name (string)
            :return: GenericMaterial or Process object
            :raise: ValueError if not found
            """
            try:
                return obj_lookup[unique_name]

            except KeyError:
                raise ValueError(
                    'No GenericMaterial or Process found with '
                    'unique_name={}'.format(unique_name))

        for a in arcs:
            try:
                tail_obj = find_by_name(a.tail)
                head_obj = find_by_name(a.head)

            except ValueError as ex:
                raise ValueError('{} / arc = {}'.format(ex, a))

            tail_obj_arg = 'tail_{}'.format(
                ARC_OBJ_SUFFIX_MAP[tail_obj.__class__.__name__])
            head_obj_arg = 'head_{}'.format(
                ARC_OBJ_SUFFIX_MAP[head_obj.__class__.__name__])

            values = {
                'assay': db_parent if type(db_parent) == Assay else None,
                'study': db_parent if
                type(db_parent) == Study else db_parent.study,
                tail_obj_arg: tail_obj,
                head_obj_arg: head_obj}

            arc = Arc(**values)
            arc.save()
            logger.debug('Added arc "{} -> {}" to "{}"'.format(
                tail_obj.unique_name,
                head_obj.unique_name,
                db_parent.get_name()))

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
        'comments': get_ontology_vals(isa_inv.info.comments),
        'status': 'IMPORTING'}

    db_investigation = Investigation(**values)
    db_investigation.save()
    logger.debug('Created investigation "{}"'.format(db_investigation.title))
    study_count = 0

    # Create studies
    for s_i in isa_inv.studies:
        obj_lookup = {}  # Lookup dict for study materials and processes
        study_id = 'p{}-s{}'.format(project.pk, study_count)

        # Parse study file
        s = StudyReader.from_stream(
            isa_inv,
            input_file=get_file(isa_zip, s_i.info.path),
            study_id=study_id).read()

        values = {
            'identifier': s_i.info.identifier,
            'file_name': s_i.info.path,
            'investigation': db_investigation,
            'title': s_i.info.title,
            'study_design': s_i.designs,        # TODO
            'factors': s_i.factors,             # TODO
            'characteristic_cat': [],           # TODO
            'unit_cat': [],                     # TODO
            'comments': get_ontology_vals(s_i.info.comments),
            'header': get_header(s.header)}

        db_study = Study(**values)
        db_study.save()
        logger.debug('Added study "{}"'.format(db_study.title))

        # Create protocols
        for p_i in s_i.protocols.values():
            values = {
                'name': p_i.name,
                'study': db_study,
                'protocol_type': get_multitype_val(p_i.type),
                'description': p_i.description,
                'uri': p_i.uri,
                'version': p_i.version,
                'parameters': get_tuple_list(p_i.parameters),
                'components': get_tuple_list(p_i.components),
                'comments': get_ontology_vals(p_i.comments)}

            protocol = Protocol(**values)
            protocol.save()
            logger.debug('Added protocol "{}" in study "{}"'.format(
                protocol.name, db_study.title))

        # Create study materials
        import_materials(s.materials, db_study, obj_lookup)

        # Create study processes
        import_processes(s.processes, db_study, obj_lookup)

        # Create study arcs
        import_arcs(s.arcs, db_study, obj_lookup)

        assay_count = 0

        for a_i in s_i.assays.values():
            assay_id = 'a{}'.format(project.pk, study_count, assay_count)

            a = AssayReader.from_stream(
                isa_inv,
                input_file=get_file(isa_zip, a_i.path),
                study_id=study_id,
                assay_id=assay_id).read()

            values = {
                'file_name': a_i.path,
                'study': db_study,
                'measurement_type': get_multitype_val(a_i.measurement_type),
                'technology_type': get_multitype_val(a_i.technology_type),
                'technology_platform': a_i.platform,
                'characteristic_cat': [],           # TODO
                'unit_cat': [],                     # TODO
                'comments': get_ontology_vals(a_i.comments),
                'header': get_header(a.header)}

            db_assay = Assay(**values)
            db_assay.save()
            logger.debug('Added assay "{}" in study "{}"'.format(
                db_assay.file_name, db_study.title))

            # Create assay materials (excluding sources and samples)
            assay_materials = {
                k: a.materials[k] for k in a.materials if
                MATERIAL_TYPE_MAP[a.materials[k].type] not in [
                    'SOURCE', 'SAMPLE']}
            import_materials(assay_materials, db_assay, obj_lookup)

            # Create assay processes
            import_processes(a.processes, db_assay, obj_lookup)

            # Create assay arcs
            import_arcs(a.arcs, db_assay, obj_lookup)
            assay_count += 1

        study_count += 1

    logger.info('Import of investigation "{}" OK ({:.1f}s)'.format(
        db_investigation.title, time.time() - t_start))

    # Update investigation status
    db_investigation.status = 'RENDERING'
    db_investigation.save()

    # Render tables
    render_investigation(db_investigation)

    # Update investigation status
    db_investigation.status = 'OK'
    db_investigation.save()

    logger.info('Investigation "{}": All OK'.format(db_investigation.title))
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
