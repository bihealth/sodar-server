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
    InvestigationWriter,
    StudyWriter,
    AssayWriter,
    models as isa_models,
)
import attr
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

# For old ISAtabs where this field was not always filled out
MATERIAL_TYPE_EXPORT_MAP = {'SOURCE': 'Source Name', 'SAMPLE': 'Sample Name'}

SAMPLE_SEARCH_SUBSTR = '-sample-'
PROTOCOL_UNKNOWN_NAME = 'Unknown'


logger = logging.getLogger(__name__)


# Importing --------------------------------------------------------------------


def import_isa(isa_zip, project):
    """
    Import ISA investigation and its studies/assays from an ISAtab Zip archive
    into the SODAR database using the altamISA parser.

    :param isa_zip: ZipFile (archive containing a single ISAtab investigation)
    :param project: Project object
    :return: Investigation object
    """
    t_start = time.time()
    logger.info('CUBI altamISA parser version: {}'.format(altamisa.__version__))
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

    def _get_ref_val(o):
        """Get altamISA string/ref value"""
        if isinstance(o, (isa_models.OntologyRef, isa_models.OntologyTermRef)):
            o = attr.asdict(o)

            if o and 'value' in o and isinstance(o['value'], str):
                o['value'] = o['value'].strip()

            return o

        elif isinstance(o, str):
            return o.strip()

    def _get_multitype_val(o):
        """Get value where the member type can vary"""
        if isinstance(o, list) and len(o) > 1:
            return [_get_ref_val(x) for x in o]

        elif isinstance(o, list) and len(o) == 1:
            o = o[0]  # Store lists of 1 item as single objects

        return _get_ref_val(o)

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

    def _get_comments(comments):
        """Get comments field as dict"""
        return {v.name: v.value for v in comments}

    def _get_tuple_list(tuples):
        """Get list of dicts from tuples for JSONField"""
        if type(tuples) == dict:
            return [_get_multitype_val(v) for v in tuples.values()]

        elif type(tuples) in [tuple, list]:
            return [_get_multitype_val(v) for v in tuples]

    def _import_publications(publications):
        """
        Convert altamISA publications tuple into a list to be stored into a
        JSONField.

        :param publications: Tuple[PublicationInfo]
        :return: List of dicts
        """
        return [
            {
                'pubmed_id': v.pubmed_id,
                'doi': v.doi,
                'authors': v.authors,
                'title': v.title,
                'status': _get_ref_val(v.status),
                'comments': _get_comments(v.comments),
                'headers': v.headers,
            }
            for v in publications
        ]

    def _import_contacts(contacts):
        """
        Convert altamISA converts tuple into a list to be stored into a
        JSONField.

        :param contacts: Tuple[ContactInfo]
        :return: List of dicts
        """
        return [
            {
                'last_name': v.last_name,
                'first_name': v.first_name,
                'mid_initial': v.mid_initial,
                'email': v.email,
                'phone': v.phone,
                'fax': v.fax,
                'address': v.address,
                'affiliation': v.affiliation,
                'role': _get_ref_val(v.role),
                'comments': _get_comments(v.comments),
                'headers': v.headers,
            }
            for v in contacts
        ]

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
                'material_type': m.type,
                'extra_material_type': _get_multitype_val(m.material_type),
                'name': m.name,
                'unique_name': m.unique_name,
                'alt_names': get_alt_names(m.name),
                'study': study,
                'headers': m.headers,
            }

            if type(db_parent) == Assay:
                values['assay'] = db_parent

            # NOTE: Extract label stored as JSON since altamISA 0.1 update
            if m.extract_label:
                values['extract_label'] = _get_multitype_val(m.extract_label)

            if m.characteristics:
                values['characteristics'] = _get_ontology_vals(
                    m.characteristics
                )
            if m.factor_values:
                values['factor_values'] = _get_ontology_vals(m.factor_values)
            values['comments'] = _get_comments(m.comments)

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
                    pass  # Warning for no found protocol reported by altamISA

            values = {
                'name': p.name,
                'unique_name': p.unique_name,
                'name_type': p.name_type,
                'protocol': protocol,
                'assay': db_parent if type(db_parent) == Assay else None,
                'study': study,
                'performer': p.performer,
                'perform_date': p.date if p.date else None,
                'array_design_ref': p.array_design_ref,
                'first_dimension': _get_ontology_vals(p.first_dimension)
                if p.first_dimension
                else {},
                'second_dimension': _get_ontology_vals(p.second_dimension)
                if p.second_dimension
                else {},
                'headers': p.headers,
                'comments': _get_comments(p.comments),
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
        'title': isa_inv.info.title,
        'description': isa_inv.info.description,
        'file_name': inv_file_path,
        'ontology_source_refs': _get_tuple_list(isa_inv.ontology_source_refs),
        'publications': _import_publications(isa_inv.publications),
        'contacts': _import_contacts(isa_inv.contacts),
        'headers': isa_inv.info.headers,
        'comments': _get_comments(isa_inv.info.comments),
        'submission_date': isa_inv.info.submission_date,
        'public_release_date': isa_inv.info.public_release_date,
        'parser_version': altamisa.__version__,
        'archive_name': isa_zip.filename,
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
    for isa_study in isa_inv.studies:
        logger.debug('Parsing study "{}"..'.format(isa_study.info.title))
        obj_lookup = {}  # Lookup dict for study materials and processes
        study_id = 'p{}-s{}'.format(project.pk, study_count)

        # Parse and validate study file
        with warnings.catch_warnings(record=True) as ws:
            s = StudyReader.from_stream(
                input_file=_get_file(
                    isa_zip, _get_zip_path(inv_dir, isa_study.info.path)
                ),
                study_id=study_id,
            ).read()
            StudyValidator(isa_inv, isa_study, s).validate()

        values = {
            'identifier': isa_study.info.identifier,
            'file_name': isa_study.info.path,
            'investigation': db_investigation,
            'title': isa_study.info.title,
            'description': isa_study.info.description,
            'study_design': [attr.asdict(x) for x in isa_study.designs],
            'publications': _import_publications(isa_study.publications),
            'contacts': _import_contacts(isa_study.contacts),
            'factors': {
                k: attr.asdict(v) for k, v in isa_study.factors.items()
            },
            'comments': _get_comments(isa_study.info.comments),
            'submission_date': isa_study.info.submission_date,
            'public_release_date': isa_study.info.public_release_date,
            'headers': isa_study.info.headers,
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

        for isa_prot in isa_study.protocols.values():
            protocol_vals.append(
                {
                    'name': isa_prot.name,
                    'study': db_study,
                    'protocol_type': _get_multitype_val(isa_prot.type),
                    'description': isa_prot.description,
                    'uri': isa_prot.uri,
                    'version': isa_prot.version,
                    'parameters': _get_tuple_list(isa_prot.parameters),
                    'components': _get_tuple_list(isa_prot.components),
                    'comments': _get_comments(isa_prot.comments),
                    'headers': isa_prot.headers,
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
        assay_paths = sorted([a.path for a in isa_study.assays])

        for assay_path in assay_paths:
            isa_assay = next(
                (a_i for a_i in isa_study.assays if a_i.path == assay_path),
                None,
            )
            logger.debug('Parsing assay "{}"..'.format(isa_assay.path))
            assay_id = 'a{}'.format(assay_count)

            # Parse and validate assay file
            with warnings.catch_warnings(record=True) as ws:
                a = AssayReader.from_stream(
                    study_id=study_id,
                    assay_id=assay_id,
                    input_file=_get_file(
                        isa_zip, _get_zip_path(inv_dir, isa_assay.path)
                    ),
                ).read()
                AssayValidator(isa_inv, isa_study, isa_assay, a).validate()

            values = {
                'file_name': isa_assay.path,
                'study': db_study,
                'measurement_type': _get_multitype_val(
                    isa_assay.measurement_type
                ),
                'technology_type': _get_multitype_val(
                    isa_assay.technology_type
                ),
                'technology_platform': isa_assay.platform,
                'comments': _get_comments(isa_assay.comments),
                'headers': isa_assay.headers,
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


def export_isa(investigation):
    """
    Import ISA investigation and its studies/assays from the SODAR database
    model into an ISAtab archive.

    :param investigation: Investigation object
    :return: ZipFile (archive containing ISAtab files for the investigation)
    """

    ################
    # Export helpers
    ################

    def _get_nodes(nodes, arcs):
        """
        Return nodes referred to in arcs.

        :param nodes: Dict of GenericMaterial or Process, key=unique_name
        :param arcs: List of lists
        :return: List
        """
        ret = {}

        def _get_node(vertice):
            if vertice in nodes and vertice not in ret:
                ret[vertice] = nodes[vertice]

        for a in arcs:
            _get_node(a[0])
            _get_node(a[1])

        return ret.values()

    def _build_value(value):
        """
        Build a "FreeTextOrTermRef" value out of a string/dict value in a
        JSONField. Can also be used for units.

        :param value: String or dict
        :return: String or OntologyTermRef
        """
        if isinstance(value, str):
            return value

        elif isinstance(value, list):
            return [_build_value(x) for x in value]

        elif isinstance(value, dict):
            if not value:  # Empty dict
                return None  # {} is not cool to altamISA

            return isa_models.OntologyTermRef(
                name=value['name'],
                accession=value['accession'],
                ontology_name=value['ontology_name'],
            )

    def _build_comments(comments):
        """
        Build comments from JSON stored in a SODAR model object.

        :param comments: Dict from a comments JSONField
        :return: Tuple of Comment NamedTuples
        """

        # TODO: Remove once reimporting sample sheets (#629, #631)
        def _get_comment_value(v):
            if isinstance(v, dict):
                return v['value']
            return v

        return tuple(
            (
                isa_models.Comment(name=k, value=_get_comment_value(v))
                for k, v in comments.items()
            )
            if comments
            else ()
        )

    def _build_publications(publications):
        """
        Build publications from a JSONField stored in an Investigation or Study
        object.

        :param publications: List of dicts from a publications JSONField
        :return: Tuple[PublicationInfo]
        """
        return tuple(
            isa_models.PublicationInfo(
                pubmed_id=v['pubmed_id'],
                doi=v['doi'],
                authors=v['authors'],
                title=v['title'],
                status=_build_value(v['status']),
                comments=_build_comments(v['comments']),
                headers=v['headers'],
            )
            for v in publications
        )

    def _build_contacts(contacts):
        """
        Build contacts from a JSONField stored in an Investigation or Study
        object.

        :param contacts: List of dicts from a contacts JSONField
        :return: Tuple[ContactInfo]
        """
        return tuple(
            isa_models.ContactInfo(
                last_name=v['last_name'],
                first_name=v['first_name'],
                mid_initial=v['mid_initial'],
                email=v['email'],
                phone=v['phone'],
                fax=v['fax'],
                address=v['address'],
                affiliation=v['affiliation'],
                role=_build_value(v['role']),
                comments=_build_comments(v['comments']),
                headers=v['headers'],
            )
            for v in contacts
        )

    def _build_source_refs(source_refs):
        """
        Build ontology source references from a JSONField stored in an
        Investigation object.

        :param source_refs: Dict from a ontology_source_refs JSONField
        :return: Dict
        """
        return {
            v['name']: isa_models.OntologyRef(
                name=v['name'],
                file=v['file'],
                version=v['version'],
                comments=_build_comments(v['comments']),
                description=v['description'],
                headers=v['headers'],
            )
            for v in source_refs
        }

    def _build_study_design(study_design):
        """
        Build study design descriptors from a JSONField in a Study object.

        :param study_design: List from a study_design JSONField object
        :return: Tuple[DesignDescriptorsInfo]
        """
        return tuple(
            isa_models.DesignDescriptorsInfo(
                type=_build_value(v['type']),
                comments=_build_comments(v['comments']),
                headers=v['headers'],
            )
            for v in study_design
        )

    def _build_components(components):
        """
        Build protocol components from JSON stored in a Protocol object.

        :param components: Dict from a comments JSONField
        :return: Tuple[ProtocolComponentInfo]
        """
        # TODO: Ensure this works with filled out data
        return (
            {
                k: isa_models.ProtocolComponentInfo(name=k, type=v)
                for k, v in components.items()
            }
            if components
            else {}
        )

    def _build_characteristics(characteristics):
        """
        Build characteristics from JSON stored in a SODAR model object.

        :param characteristics: Dict from a characteristics JSONField
        :return: Tuple[Characteristics]
        """
        return tuple(
            isa_models.Characteristics(
                name=k,
                value=[_build_value(v['value'])]
                if not isinstance(v['value'], list)
                else _build_value(v['value']),
                unit=_build_value(v['unit']),
            )
            for k, v in characteristics.items()
        )

    def _build_factors(factors):
        """
        Build factor references from JSON stored in a Study object.

        :param factors: Dict from a factors JSONField
        :return: Dict[str, FactorInfo]
        """
        return {
            k: isa_models.FactorInfo(
                name=k,
                type=_build_value(v['type']),
                comments=_build_comments(v['comments']),
                headers=v['headers'],
            )
            for k, v in factors.items()
        }

    def _build_factor_values(factor_values):
        """
        Build factor values from JSON stored in a GenericMaterial object.

        :param factor_values: Dict from a factor_values JSONField
        :return: Tuple[FactorValue]
        """
        if not factor_values:
            return tuple()  # None is not accepted here

        return tuple(
            isa_models.FactorValue(
                name=k,
                value=_build_value(v['value']),
                unit=_build_value(v['unit']),
            )
            for k, v in factor_values.items()
        )

    def _build_parameters(parameters):
        """
        Build parameters for a protocol from JSON stored in a Protocol
        object.

        :param parameters: List from a parameters JSONField
        :return: Dict
        """
        ret = {}

        for p in parameters:
            ret[p['name']] = _build_value(p)

        return ret

    def _build_param_values(param_values):
        """
        Build parameter values from JSON stored in a Process object.

        :param param_values: Dict from a parameter_values JSONField
        :return: Tuple[ParameterValue]
        """
        return tuple(
            isa_models.ParameterValue(
                name=k,
                value=[_build_value(v['value'])]
                if not isinstance(v['value'], list)
                else _build_value(v['value']),
                unit=_build_value(v['unit']),
            )
            for k, v in param_values.items()
        )

    def _build_arcs(arcs):
        """
        Build arcs from ArrayField stored in a Study or Assay object.

        :param arcs: List of lists from an arcs ArrayField
        :return: Tuple[Arc]
        """
        return (
            tuple(isa_models.Arc(tail=a[0], head=a[1]) for a in arcs)
            if arcs
            else ()
        )

    ################
    # Export helpers
    ################

    def _export_materials(materials, study_data=True):
        """
        Export materials from SODAR model objects.

        :param materials: QuerySet or array of GenericMaterial objects
        :param study_data: If False, strip data not expected in an assay
        :return: Dict
        """
        ret = {}

        for m in materials:
            sample_in_assay = m.item_type == 'SAMPLE' and not study_data
            headers = m.headers if not sample_in_assay else [m.headers[0]]

            # HACK for extract label parsing crash (#635)
            if (
                m.material_type == 'Labeled Extract Name'
                and 'Label' in headers
                and not m.extract_label
            ):
                extract_label = ''

            else:
                extract_label = _build_value(m.extract_label)

            ret[m.unique_name] = isa_models.Material(
                type=m.material_type
                if m.material_type
                else MATERIAL_TYPE_EXPORT_MAP[m.item_type],
                unique_name=m.unique_name,
                name=m.name,
                extract_label=extract_label,
                characteristics=_build_characteristics(m.characteristics)
                if not sample_in_assay
                else (),
                comments=_build_comments(m.comments)
                if not sample_in_assay
                else (),
                factor_values=_build_factor_values(m.factor_values)
                if study_data
                else tuple(),
                material_type=_build_value(m.extra_material_type),
                headers=headers,
            )

        return ret

    def _export_processes(processes):
        """
        Export processes from SODAR model objects.

        :param processes: QuerySet or array of Process objects
        :return: Dict
        """
        ret = {}

        for p in processes:
            # Set up perform date
            if not p.perform_date and 'Date' in p.headers:
                perform_date = ''  # Empty string denotes an empty column

            else:
                perform_date = p.perform_date

            ret[p.unique_name] = isa_models.Process(
                protocol_ref=p.protocol.name
                if p.protocol
                else PROTOCOL_UNKNOWN_NAME,
                unique_name=p.unique_name,
                name=p.name,
                name_type=p.name_type,
                date=perform_date,
                performer=p.performer,
                parameter_values=_build_param_values(p.parameter_values),
                comments=_build_comments(p.comments),
                array_design_ref=p.array_design_ref,
                first_dimension=_build_value(p.first_dimension),
                second_dimension=_build_value(p.second_dimension),
                headers=p.headers,
            )

        return ret

    ###########
    # Exporting
    ###########

    # Create StudyInfo objects for studies
    isa_study_infos = []
    isa_studies = []
    isa_assays = {}
    study_idx = 0

    for study in investigation.studies.all().order_by('file_name'):
        # Get all materials and nodes in study and its assays
        all_materials = {m.unique_name: m for m in study.materials.all()}
        all_processes = {p.unique_name: p for p in study.processes.all()}

        # Get study materials
        study_materials = _export_materials(
            _get_nodes(all_materials, study.arcs)
        )
        study_processes = _export_processes(
            _get_nodes(all_processes, study.arcs)
        )

        # Create study
        isa_study = isa_models.Study(
            file=study.file_name,
            header=study.headers,
            materials=study_materials,
            processes=study_processes,
            arcs=_build_arcs(study.arcs),
        )
        isa_studies.append(isa_study)

        isa_assay_infos = []
        isa_assays[study_idx] = {}
        assay_idx = 0

        # Create AssayInfo objects for assays
        for assay in study.assays.all().order_by('file_name'):
            assay_info = isa_models.AssayInfo(
                measurement_type=_build_value(assay.measurement_type),
                technology_type=_build_value(assay.technology_type),
                platform=assay.technology_platform,
                path=assay.file_name,
                comments=_build_comments(assay.comments),
                headers=assay.headers,
            )
            isa_assay_infos.append(assay_info)

            # Get assay materials and processes
            assay_materials = _export_materials(
                _get_nodes(all_materials, assay.arcs), study_data=False
            )
            assay_processes = _export_processes(
                _get_nodes(all_processes, assay.arcs)
            )

            # Create actual assay and parse its members
            isa_assay = isa_models.Assay(
                file=assay.file_name,
                header=tuple(assay.headers),
                materials=assay_materials,
                processes=assay_processes,
                arcs=_build_arcs(assay.arcs),
            )
            isa_assays[study_idx][assay_idx] = isa_assay
            assay_idx += 1

        # Create protocols for study
        isa_protocols = {}

        for protocol in study.protocols.all():
            isa_protocols[protocol.name] = isa_models.ProtocolInfo(
                name=protocol.name,
                type=_build_value(protocol.protocol_type),
                description=protocol.description,
                uri=protocol.uri,
                version=protocol.version,
                parameters=_build_parameters(protocol.parameters),
                components=_build_components(protocol.components),
                comments=_build_comments(protocol.comments),
                headers=protocol.headers,
            )

        # Create BasicInfo for study
        isa_study_basic = isa_models.BasicInfo(
            path=study.file_name,
            identifier=study.identifier,
            title=study.title,
            description=study.description,
            submission_date=study.submission_date,
            public_release_date=study.public_release_date,
            comments=_build_comments(study.comments),
            headers=study.headers,
        )

        # Create StudyInfo object
        isa_study_info = isa_models.StudyInfo(
            info=isa_study_basic,
            designs=_build_study_design(study.study_design),
            publications=_build_publications(study.publications),
            factors=_build_factors(study.factors),
            assays=tuple(isa_assay_infos),
            protocols=isa_protocols,
            contacts=_build_contacts(study.contacts),
        )
        isa_study_infos.append(isa_study_info)
        study_idx += 1

    # Create BasicInfo for investigation
    inv_basic = isa_models.BasicInfo(
        path=investigation.file_name,
        identifier=investigation.identifier,
        title=investigation.title,
        description=investigation.description,
        submission_date=investigation.submission_date,
        public_release_date=investigation.public_release_date,
        comments=_build_comments(investigation.comments),
        headers=investigation.headers,
    )

    # Create InvestigationInfo
    inv_info = isa_models.InvestigationInfo(
        ontology_source_refs=_build_source_refs(
            investigation.ontology_source_refs
        ),
        info=inv_basic,
        publications=_build_publications(investigation.publications),
        contacts=_build_contacts(investigation.contacts),
        studies=tuple(isa_study_infos),
    )

    # Prepare return data
    # (the ZIP file preparing and serving should happen in the view)
    ret = {'investigation': {}, 'studies': {}, 'assays': {}}
    inv_out = io.StringIO()

    # Write investigation
    InvestigationValidator(inv_info).validate()
    InvestigationWriter.from_stream(inv_info, output_file=inv_out).write()
    ret['investigation']['path'] = inv_info.info.path
    ret['investigation']['data'] = inv_out.getvalue()
    inv_out.close()

    # Write studies
    for study_idx, study_info in enumerate(inv_info.studies):
        StudyValidator(inv_info, study_info, isa_studies[study_idx]).validate()
        study_out = io.StringIO()
        StudyWriter.from_stream(isa_studies[study_idx], study_out).write()
        ret['studies'][study_info.info.path] = {'data': study_out.getvalue()}
        study_out.close()

        # Write assays
        for assay_idx, assay_info in enumerate(study_info.assays):
            AssayValidator(
                inv_info,
                study_info,
                assay_info,
                isa_assays[study_idx][assay_idx],
            ).validate()
            assay_out = io.StringIO()
            AssayWriter.from_stream(
                isa_assays[study_idx][assay_idx], assay_out
            ).write()
            ret['assays'][assay_info.path] = {'data': assay_out.getvalue()}
            assay_out.close()

    return ret


# iRODS Utils ------------------------------------------------------------------


def get_assay_dirs(assay):
    """
    Return iRODS directory structure under an assay

    :param assay: Assay object
    :return: List
    """
    # TODO: Currently just an empty dir, this needs to be implemented for real
    return []
