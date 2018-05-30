"""Import and export utilities for the samplesheets app"""

from altamisa.isatab import InvestigationReader, StudyReader, AssayReader
from fnmatch import fnmatch
import io
import logging
import time

from .models import Investigation, Study, Assay, GenericMaterial, Protocol, \
    Process
from .rendering import SampleSheetTableBuilder


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


def import_isa(isa_zip, project):
    """
    Import ISA investigation and its studies/assays from an ISAtab Zip archive
    into the Django database, utilizing the altamISA parser
    :param isa_zip: ZipFile (archive containing a single ISAtab investigation)
    :param project: Project object
    :return: Django Investigation object
    """
    t_start = time.time()
    logger.info('Importing investigation from a Zip archive..')

    ######################
    # Parse Zip archive
    ######################

    def get_file(zip_file, file_name):
        file = zip_file.open(str(file_name), 'r')
        return io.TextIOWrapper(file)

    def get_zip_path(inv_path, file_path):
        return '{}{}{}'.format(
            inv_path, '/' if inv_path else '', str(file_path))

    # Parse investigation
    inv_file_path = get_inv_paths(isa_zip)[0]
    inv_dir = '/'.join(inv_file_path.split('/')[:-1])

    input_file = get_file(isa_zip, inv_file_path)
    isa_inv = InvestigationReader.from_stream(
        input_file=input_file).read()

    ###################
    # Helper functions
    ###################

    def get_study(o):
        """Return study for a potentially unknown type of object"""
        if type(o) == Study:
            return o

        elif hasattr(o, 'study'):
            return o.study

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
        material_vals = []
        study = get_study(db_parent)

        for m in materials.values():
            item_type = MATERIAL_TYPE_MAP[m.type]

            # Common values
            values = {
                'item_type': item_type,
                'name': m.name,
                'unique_name': m.unique_name,
                'study': study}

            if type(db_parent) == Assay:
                values['assay'] = db_parent

            # Type
            # HACK since file/extract subtype is in .type
            if item_type in ['DATA', 'MATERIAL'] or m.material_type:
                values['material_type'] = m.type
            if m.extract_label:
                values['extract_label'] = m.extract_label

            if m.characteristics:
                values['characteristics'] = get_ontology_vals(m.characteristics)
            if m.factor_values:
                values['factor_values'] = get_ontology_vals(m.factor_values)
            values['comments'] = get_ontology_vals(m.comments)

            material_vals.append(values)

        materials = GenericMaterial.objects.bulk_create([
            GenericMaterial(**v) for v in material_vals])
        obj_lookup.update({m.unique_name: m for m in materials})

        logger.debug('Added {} materials to "{}"'.format(
            len(materials), db_parent.get_name()))

    def import_processes(processes, db_parent, obj_lookup, protocol_lookup):
        """
        Create processes of a process sequence in the database.
        :param processes: Process sequence of a study or an assay in altamISA
        :param db_parent: Parent study or assay
        :param obj_lookup: Dictionary for in-memory material/process lookup
        :param protocol_lookup: Dictionary for in-memory protocol lookup
        """
        study = get_study(db_parent)
        process_vals = []

        for p in processes.values():
            # Link protocol
            protocol = None

            if p.protocol_ref != 'UNKNOWN':
                try:
                    protocol = protocol_lookup[p.protocol_ref]

                except KeyError:
                    logger.warning(
                        'No protocol found for process "{}" '
                        'with ref "{}"'.format(
                            p.unique_name, p.protocol_ref))

            values = {
                'name': p.name,
                'unique_name': p.unique_name,
                'protocol': protocol,
                'assay': db_parent if type(db_parent) == Assay else None,
                'study': study,
                'performer': p.performer,
                'perform_date': p.date,
                'array_design_ref': p.array_design_ref,
                'scan_name': p.scan_name,
                'comments': get_ontology_vals(p.comments)}

            # Parameter values
            if p.parameter_values:
                values['parameter_values'] = get_ontology_vals(
                    p.parameter_values)

            process_vals.append(values)

        processes = Process.objects.bulk_create([
            Process(**v) for v in process_vals])
        obj_lookup.update({p.unique_name: p for p in processes})

        logger.debug('Added {} processes to "{}"'.format(
            len(processes), db_parent.get_name()))

    def import_arcs(arcs, db_parent):
        """
        Create process/material arcs according to the altamISA structure
        :param arcs: Tuple
        :param db_parent: Study or Assay object
        """
        arc_vals = []

        for a in arcs:
            arc_vals.append([a.tail, a.head])

        db_parent.arcs = arc_vals
        db_parent.save()

        logger.debug('Added {} arcs to "{}"'.format(
            len(arc_vals), db_parent.get_name()))

    #########
    # Import
    #########

    # Create investigation
    values = {
        'project': project,
        'identifier': isa_inv.info.identifier,
        'title': (isa_inv.info.title or project.title),
        'description': (isa_inv.info.description or project.description),
        'file_name': inv_file_path,
        'ontology_source_refs': get_tuple_list(isa_inv.ontology_source_refs),
        'comments': get_ontology_vals(isa_inv.info.comments)}

    db_investigation = Investigation(**values)
    db_investigation.save()
    logger.debug('Created investigation "{}"'.format(db_investigation.title))
    study_count = 0
    db_studies = []

    # Create studies
    for s_i in isa_inv.studies:
        obj_lookup = {}  # Lookup dict for study materials and processes
        study_id = 'p{}-s{}'.format(project.pk, study_count)

        # Parse study file
        s = StudyReader.from_stream(
            isa_inv,
            s_i,
            input_file=get_file(isa_zip, get_zip_path(inv_dir, s_i.info.path)),
            study_id=study_id).read()

        values = {
            'identifier': s_i.info.identifier,
            'file_name': s_i.info.path,
            'investigation': db_investigation,
            'title': s_i.info.title,
            'study_design': s_i.designs,        # TODO
            'factors': s_i.factors,             # TODO
            'characteristic_cat': [],           # TODO: TBD: Implement or omit?
            'unit_cat': [],                     # TODO: TBD: Implement or omit?
            'comments': get_ontology_vals(s_i.info.comments),
            'header': get_header(s.header)}

        db_study = Study(**values)
        db_study.save()
        db_studies.append(db_study)
        logger.debug('Added study "{}"'.format(db_study.title))

        # Create protocols
        protocol_vals = []

        for p_i in s_i.protocols.values():
            protocol_vals.append({
                'name': p_i.name,
                'study': db_study,
                'protocol_type': get_multitype_val(p_i.type),
                'description': p_i.description,
                'uri': p_i.uri,
                'version': p_i.version,
                'parameters': get_tuple_list(p_i.parameters),
                'components': get_tuple_list(p_i.components),
                'comments': get_ontology_vals(p_i.comments)})

        protocols = Protocol.objects.bulk_create([
            Protocol(**v) for v in protocol_vals])
        protocol_lookup = {p.name: p for p in protocols}  # Per study, no update

        logger.debug('Added {} protocols in study "{}"'.format(
            len(protocols), db_study.title))

        # Create study materials
        import_materials(s.materials, db_study, obj_lookup)

        # Create study processes
        import_processes(s.processes, db_study, obj_lookup, protocol_lookup)

        # Create study arcs
        import_arcs(s.arcs, db_study)

        assay_count = 0
        assay_paths = sorted([a_i.path for a_i in s_i.assays.values()])

        for assay_path in assay_paths:
            a_i = next((
                a_i for a_i in s_i.assays.values() if a_i.path == assay_path),
                None)
            assay_id = 'a{}'.format(assay_count)

            a = AssayReader.from_stream(
                isa_inv,
                s_i,
                study_id=study_id,
                assay_id=assay_id,
                input_file=get_file(
                    isa_zip, get_zip_path(inv_dir, a_i.path))).read()

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
            import_processes(a.processes, db_assay, obj_lookup, protocol_lookup)

            # Create assay arcs
            import_arcs(a.arcs, db_assay)
            assay_count += 1

        study_count += 1

    # Ensure we can build the table reference, if not then fail
    logger.debug('Ensuring studies can be rendered..')

    for study in db_studies:
        # Throws an exception if we are unable to build this
        SampleSheetTableBuilder.build_study_reference(study)

    logger.info('Import of investigation "{}" OK ({:.1f}s)'.format(
        db_investigation.title, time.time() - t_start))
    return db_investigation


def get_inv_paths(zip_file):
    """
    Return investigation file paths from a zip file
    :param zip_file: ZipFile
    :return: List
    :raise: ValueError if file_type is not valid
    """
    # NOTE: There should not be multiple inv.:s in one file, but must check
    ret = []

    for f in zip_file.infolist():
        if fnmatch(f.filename.split('/')[-1], 'i_*.txt'):
            ret.append(f.filename)

    return ret


# Exporting --------------------------------------------------------------------


# TODO: Export to ISAtab


# iRODS Utils ------------------------------------------------------------------


def get_assay_dirs(assay):
    """
    Return iRODS directory structure under an assay
    :param assay: Assay object
    :return: List
    """
    # TODO: Currently just an empty dir, this needs to be implemented for real
    return []
