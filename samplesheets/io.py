"""Import and export utilities for the samplesheets app"""

# TODO: Refactor into class

import altamisa
from altamisa.isatab import (
    InvestigationReader,
    StudyReader,
    AssayReader,
    InvestigationValidator,
    StudyValidator,
    AssayValidator,
)
from fnmatch import fnmatch
import io
import logging
import time
import warnings

from .models import (
    Investigation,
    Study,
    Assay,
    GenericMaterial,
    Protocol,
    Process,
)
from .rendering import SampleSheetTableBuilder
from .utils import get_alt_names


# Local constants
ALTAMISA_MATERIAL_TYPE_SAMPLE = 'Sample Name'

MATERIAL_TYPE_MAP = {
    'Source Name': 'SOURCE',
    'Sample Name': 'SAMPLE',
    'Extract Name': 'MATERIAL',
    'Library Name': 'MATERIAL',
    'Labeled Extract Name': 'MATERIAL',
    'Raw Data File': 'DATA',  # HACK: File subtypes should be in their own
    'Derived Data File': 'DATA',  # field instead of material.type
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
    'Array Data Matrix File': 'DATA',
}

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
    logger.info('Using CUBI altamISA parser v{}'.format(altamisa.__version__))
    parser_warnings = {
        'investigation': [],
        'studies': {},
        'assays': {},
        'all_ok': True,
    }

    ###################
    # Helper functions
    ###################

    def _get_file(zip_file, file_name):
        file = zip_file.open(str(file_name), 'r')
        return io.TextIOWrapper(file)

    def _get_zip_path(inv_path, file_path):
        return '{}{}{}'.format(
            inv_path, '/' if inv_path else '', str(file_path)
        )

    def _handle_warning(warning, db_obj):
        """
        Store and log altamISA warning.

        :param warning: Warning object
        :param obj_cls: SODAR database object which was parsed (Investigation,
                        Study, Assay)
        """
        parser_warnings['all_ok'] = False
        warn_data = {
            'message': str(warning.message),
            'category': warning.category.__name__,
        }
        obj_uuid = str(db_obj.sodar_uuid)

        if isinstance(db_obj, Investigation):
            parser_warnings['investigation'].append(warn_data)

        elif isinstance(db_obj, Study):
            if obj_uuid not in parser_warnings['studies']:
                parser_warnings['studies'][obj_uuid] = []

            parser_warnings['studies'][obj_uuid].append(warn_data)

        elif isinstance(db_obj, Assay):
            if obj_uuid not in parser_warnings['assays']:
                parser_warnings['assays'][obj_uuid] = []

            parser_warnings['assays'][obj_uuid].append(warn_data)

        logger.warning(
            'Parser warning: "{}" '
            '(Category: {})'.format(warning.message, warning.category.__name__)
        )

    def _get_study(o):
        """Return study for a potentially unknown type of object"""
        if type(o) == Study:
            return o

        elif hasattr(o, 'study'):
            return o.study

    def _get_multitype_val(o):
        """Get value where the member type can vary"""
        if isinstance(o, list) and len(o) == 1:
            o = o[0]  # Store lists of 1 item (99% of cases) as single objects

        return o._asdict() if isinstance(o, tuple) else o

    def _get_ontology_vals(vals):
        """Get value data from potential ontology references"""
        ret = {}

        for v in vals:
            ret[v.name] = {
                'unit': _get_multitype_val(v.unit)
                if hasattr(v, 'unit')
                else None,
                'value': _get_multitype_val(v.value),
            }

        return ret

    def _get_tuple_list(tuples):
        """Get list of dicts from tuples for JSONField"""
        if type(tuples) == dict:
            return [_get_multitype_val(v) for v in tuples.values()]

        elif type(tuples) in [tuple, list]:
            return [_get_multitype_val(v) for v in tuples]

    def _import_materials(materials, db_parent, obj_lookup):
        """
        Create material objects in Django database.
        :param materials: altamISA materials dict
        :param db_parent: Parent Django db object (Assay or Study)
        :param obj_lookup: Dictionary for in-memory lookup
        """
        material_vals = []
        study = _get_study(db_parent)

        for m in materials.values():
            item_type = MATERIAL_TYPE_MAP[m.type]

            # Common values
            values = {
                'item_type': item_type,
                'name': m.name,
                'unique_name': m.unique_name,
                'alt_names': get_alt_names(m.name),
                'study': study,
                'headers': m.headers,
            }

            if type(db_parent) == Assay:
                values['assay'] = db_parent

            # Type
            # HACK since file/extract subtype is in .type
            if item_type in ['DATA', 'MATERIAL'] or m.material_type:
                values['material_type'] = m.type

            # NOTE: Extract label stored as JSON since altamISA 0.1 update
            if m.extract_label:
                values['extract_label'] = {'value': m.extract_label}

            if m.characteristics:
                values['characteristics'] = _get_ontology_vals(
                    m.characteristics
                )
            if m.factor_values:
                values['factor_values'] = _get_ontology_vals(m.factor_values)
            values['comments'] = _get_ontology_vals(m.comments)

            material_vals.append(values)

        materials = GenericMaterial.objects.bulk_create(
            [GenericMaterial(**v) for v in material_vals]
        )
        obj_lookup.update({m.unique_name: m for m in materials})

        logger.debug(
            'Added {} materials to "{}"'.format(
                len(materials), db_parent.get_name()
            )
        )

    def _import_processes(processes, db_parent, obj_lookup, protocol_lookup):
        """
        Create processes of a process sequence in the database.
        :param processes: Process sequence of a study or an assay in altamISA
        :param db_parent: Parent study or assay
        :param obj_lookup: Dictionary for in-memory material/process lookup
        :param protocol_lookup: Dictionary for in-memory protocol lookup
        """
        study = _get_study(db_parent)
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
                        'with ref "{}"'.format(p.unique_name, p.protocol_ref)
                    )

            values = {
                'name': p.name,
                'unique_name': p.unique_name,
                'name_type': p.name_type,
                'protocol': protocol,
                'assay': db_parent if type(db_parent) == Assay else None,
                'study': study,
                'performer': p.performer,
                'perform_date': p.date,
                'array_design_ref': p.array_design_ref,
                'first_dimension': _get_ontology_vals(p.first_dimension)
                if p.first_dimension
                else {},
                'second_dimension': _get_ontology_vals(p.second_dimension)
                if p.second_dimension
                else {},
                'headers': p.headers,
                'comments': _get_ontology_vals(p.comments),
            }

            # Parameter values
            if p.parameter_values:
                values['parameter_values'] = _get_ontology_vals(
                    p.parameter_values
                )

            process_vals.append(values)

        processes = Process.objects.bulk_create(
            [Process(**v) for v in process_vals]
        )
        obj_lookup.update({p.unique_name: p for p in processes})

        logger.debug(
            'Added {} processes to "{}"'.format(
                len(processes), db_parent.get_name()
            )
        )

    def _import_arcs(arcs, db_parent):
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

        logger.debug(
            'Added {} arcs to "{}"'.format(len(arc_vals), db_parent.get_name())
        )

    #########
    # Import
    #########

    # Read zip file
    logger.info(
        'Importing investigation from archive "{}"..'.format(isa_zip.filename)
    )
    inv_file_path = get_inv_paths(isa_zip)[0]
    inv_dir = '/'.join(inv_file_path.split('/')[:-1])
    input_file = _get_file(isa_zip, inv_file_path)

    # Parse and validate investigation
    with warnings.catch_warnings(record=True) as ws:
        isa_inv = InvestigationReader.from_stream(input_file=input_file).read()
        InvestigationValidator(isa_inv).validate()

    # Create investigation
    values = {
        'project': project,
        'identifier': isa_inv.info.identifier,
        'title': (isa_inv.info.title or project.title),
        'description': (isa_inv.info.description or project.description),
        'file_name': inv_file_path,
        'ontology_source_refs': _get_tuple_list(isa_inv.ontology_source_refs),
        'comments': _get_ontology_vals(isa_inv.info.comments),
        'parser_version': altamisa.__version__,
    }

    db_investigation = Investigation(**values)
    db_investigation.save()

    # Handle parser warnings for investigation
    for w in ws:
        _handle_warning(w, db_investigation)

    logger.debug('Created investigation "{}"'.format(db_investigation.title))
    study_count = 0
    db_studies = []

    # Make sure identifiers are unique (avoid issue #483 repeating)
    # TODO: TBD: Do we still need this with altamISA v0.1?
    study_ids = [s_i.info.identifier for s_i in isa_inv.studies]

    if len(study_ids) != len(set(study_ids)):
        error_msg = 'Study identifiers are not unique'
        logger.error(error_msg)
        raise ValueError(error_msg)

    if '' in study_ids or None in study_ids:
        error_msg = 'Empty study identifier not allowed'
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Create studies
    for s_i in isa_inv.studies:
        logger.debug('Parsing study "{}"..'.format(s_i.info.title))
        obj_lookup = {}  # Lookup dict for study materials and processes
        study_id = 'p{}-s{}'.format(project.pk, study_count)

        # Parse and validate study file
        with warnings.catch_warnings(record=True) as ws:
            s = StudyReader.from_stream(
                input_file=_get_file(
                    isa_zip, _get_zip_path(inv_dir, s_i.info.path)
                ),
                study_id=study_id,
            ).read()
            StudyValidator(isa_inv, s_i, s).validate()

        values = {
            'identifier': s_i.info.identifier,
            'file_name': s_i.info.path,
            'investigation': db_investigation,
            'title': s_i.info.title,
            'description': s_i.info.description,
            'study_design': s_i.designs,
            'factors': s_i.factors,
            'comments': _get_ontology_vals(s_i.info.comments),
            'headers': s_i.info.headers,
        }

        db_study = Study(**values)
        db_study.save()
        db_studies.append(db_study)

        # Handle parser warnings for study
        for w in ws:
            _handle_warning(w, db_study)

        logger.debug('Added study "{}"'.format(db_study.title))

        # Create protocols
        protocol_vals = []

        for p_i in s_i.protocols.values():
            protocol_vals.append(
                {
                    'name': p_i.name,
                    'study': db_study,
                    'protocol_type': _get_multitype_val(p_i.type),
                    'description': p_i.description,
                    'uri': p_i.uri,
                    'version': p_i.version,
                    'parameters': _get_tuple_list(p_i.parameters),
                    'components': _get_tuple_list(p_i.components),
                    'comments': _get_ontology_vals(p_i.comments),
                    'headers': p_i.headers,
                }
            )

        protocols = Protocol.objects.bulk_create(
            [Protocol(**v) for v in protocol_vals]
        )
        protocol_lookup = {p.name: p for p in protocols}  # Per study, no update

        logger.debug(
            'Added {} protocols in study "{}"'.format(
                len(protocols), db_study.title
            )
        )

        # Create study materials
        _import_materials(s.materials, db_study, obj_lookup)

        # Create study processes
        _import_processes(s.processes, db_study, obj_lookup, protocol_lookup)

        # Create study arcs
        _import_arcs(s.arcs, db_study)

        assay_count = 0
        assay_paths = sorted([a_i.path for a_i in s_i.assays])

        for assay_path in assay_paths:
            a_i = next(
                (a_i for a_i in s_i.assays if a_i.path == assay_path), None
            )
            logger.debug('Parsing assay "{}"..'.format(a_i.path))
            assay_id = 'a{}'.format(assay_count)

            # Parse and validate assay file
            with warnings.catch_warnings(record=True) as ws:
                a = AssayReader.from_stream(
                    study_id=study_id,
                    assay_id=assay_id,
                    input_file=_get_file(
                        isa_zip, _get_zip_path(inv_dir, a_i.path)
                    ),
                ).read()
                AssayValidator(isa_inv, s_i, a_i, a).validate()

            values = {
                'file_name': a_i.path,
                'study': db_study,
                'measurement_type': _get_multitype_val(a_i.measurement_type),
                'technology_type': _get_multitype_val(a_i.technology_type),
                'technology_platform': a_i.platform,
                'comments': _get_ontology_vals(a_i.comments),
                'headers': a_i.headers,
            }

            db_assay = Assay(**values)
            db_assay.save()

            # Handle parser warnings for assay
            for w in ws:
                _handle_warning(w, db_assay)

            logger.debug(
                'Added assay "{}" in study "{}"'.format(
                    db_assay.file_name, db_study.title
                )
            )

            # Create assay materials (excluding sources and samples)
            assay_materials = {
                k: a.materials[k]
                for k in a.materials
                if MATERIAL_TYPE_MAP[a.materials[k].type]
                not in ['SOURCE', 'SAMPLE']
            }
            _import_materials(assay_materials, db_assay, obj_lookup)

            # Create assay processes
            _import_processes(
                a.processes, db_assay, obj_lookup, protocol_lookup
            )

            # Create assay arcs
            _import_arcs(a.arcs, db_assay)
            assay_count += 1

        study_count += 1

    # Ensure we can build the table reference, if not then fail
    logger.debug('Ensuring studies can be rendered..')

    for study in db_studies:
        # Throws an exception if we are unable to build this
        SampleSheetTableBuilder.build_study_reference(study)

    logger.debug('Rendering OK')

    # Store parser warnings (only if warnings were raised)
    if not parser_warnings['all_ok']:
        logger.debug(
            'Warnings raised, storing in investigation.parser_warnings'
        )
        db_investigation.parser_warnings = parser_warnings
        db_investigation.save()

    logger.info(
        'Import of investigation "{}" OK ({:.1f}s)'.format(
            db_investigation.title, time.time() - t_start
        )
    )
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
