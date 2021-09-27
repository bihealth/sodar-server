"""Import and export utilities for the samplesheets app"""

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
from altamisa.exceptions import CriticalIsaValidationWarning
import attr
from fnmatch import fnmatch
import io
import logging
import time
import warnings
from zipfile import ZipFile

from django.db import transaction

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI

from samplesheets.models import (
    Investigation,
    Study,
    Assay,
    GenericMaterial,
    Protocol,
    Process,
    ISATab,
)
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.utils import get_alt_names


app_settings = AppSettingAPI()
logger = logging.getLogger(__name__)


# Local constants
APP_NAME = 'samplesheets'
ARCHIVE_TYPES = ['application/zip', 'application/x-zip-compressed']
ISATAB_TYPES = ['text/plain', 'text/tab-separated-values']

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

# For old ISA-Tabs where this field was not always filled out
MATERIAL_TYPE_EXPORT_MAP = {'SOURCE': 'Source Name', 'SAMPLE': 'Sample Name'}

SAMPLE_SEARCH_SUBSTR = '-sample-'
PROTOCOL_UNKNOWN_NAME = 'Unknown'


class SampleSheetIO:
    def __init__(self, warn=True, allow_critical=False):
        """
        Initializate SampleSheetIO.

        :param warn: Handle warnings in import/export (bool)
        :param allow_critical: Allow critical warnings in import (bool)
        """
        self._warn = warn
        self._allow_critical = allow_critical
        self._warnings = self._init_warnings()

    # General internal functions -----------------------------------------------

    @classmethod
    def _init_warnings(cls):
        """Initialize warnings"""
        return {
            'investigation': [],
            'studies': {},
            'assays': {},
            'all_ok': True,
            'critical_count': 0,
            'use_file_names': True,  # HACK for issue #644
        }

    def _handle_warnings(self, warnings, db_obj):
        """
        Store and log warnings resulting from an altamISA operation.

        :param warnings: Warning objects
        :param db_obj: SODAR database object which was imported (Investigation,
                       Study, Assay)
        """
        if not warnings or not self._warn:
            return

        if self._warnings['all_ok']:
            self._init_warnings()
        self._warnings['all_ok'] = False

        for warning in warnings:
            if warning.category == CriticalIsaValidationWarning:
                self._warnings['critical_count'] += 1
            warn_data = {
                'message': str(warning.message),
                'category': warning.category.__name__,
            }
            file_name = str(db_obj.file_name).split('/')[-1]  # Strip path

            if isinstance(db_obj, Investigation):
                self._warnings['investigation'].append(warn_data)
            elif isinstance(db_obj, Study):
                if file_name not in self._warnings['studies']:
                    self._warnings['studies'][file_name] = []
                self._warnings['studies'][file_name].append(warn_data)
            elif isinstance(db_obj, Assay):
                if file_name not in self._warnings['assays']:
                    self._warnings['assays'][file_name] = []
                self._warnings['assays'][file_name].append(warn_data)

            logger.warning(
                'altamISA warning: "{}" '
                '(Category: {})'.format(
                    warning.message, warning.category.__name__
                )
            )

    # Helpers ------------------------------------------------------------------

    @classmethod
    def get_inv_paths(cls, zip_file):
        """
        Return investigation file paths from a zip file.

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

    @classmethod
    def get_zip_file(cls, file):
        """
        Return uploaded file as ZipFile. Raises an exception if the file is
        corrupt or not a zip file.

        :param file: UploadedFile or one of its subclasses
        :return: ZipFile
        :raise: OSError if the file is not a valid zip file
        """
        # Ensure file type
        if file.content_type not in ARCHIVE_TYPES:
            raise OSError('The file is not a zip archive')
        try:
            zip_file = ZipFile(file)
        except Exception as ex:
            raise OSError('Unable to open zip archive: {}'.format(ex))
        # Get investigation file path(s)
        inv_paths = cls.get_inv_paths(zip_file)
        if len(inv_paths) == 0:
            raise OSError('Investigation file not found in archive')
        elif len(inv_paths) > 1:
            raise OSError('Multiple investigation files found in archive')
        return zip_file

    @classmethod
    def get_import_file(cls, zip_file, file_name):
        file = zip_file.open(str(file_name), 'r')
        return io.TextIOWrapper(file)

    @classmethod
    def get_isa_from_zip(cls, zip_file):
        """
        Read ISA-Tab files from a Zip archive into a dictionary.

        :param zip_file: ZipFile object
        :return: Dict
        """
        ret = {'investigation': {}, 'studies': {}, 'assays': {}}

        for isa_path in [n for n in zip_file.namelist() if not n.endswith('/')]:
            isa_name = isa_path.split('/')[-1]
            if isa_name.startswith('i_'):
                ret['investigation'] = {
                    'path': isa_path,
                    'tsv': zip_file.open(str(isa_path), 'r')
                    .read()
                    .decode('utf-8'),
                }
            elif isa_name.startswith('s_'):
                ret['studies'][isa_name] = {
                    'tsv': zip_file.open(str(isa_path), 'r')
                    .read()
                    .decode('utf-8')
                }
            elif isa_name.startswith('a_'):
                ret['assays'][isa_name] = {
                    'tsv': zip_file.open(str(isa_path), 'r')
                    .read()
                    .decode('utf-8')
                }

        return ret

    @classmethod
    def get_isa_from_files(cls, files):
        """
        Get ISA-Tab data from a list of text files.

        :param files: List of UploadedFile objects
        :return: Dict
        :raise: ValueError if file content types are incorrect
        """
        isa_data = {'investigation': {}, 'studies': {}, 'assays': {}}

        for file in files:
            if file.content_type not in ISATAB_TYPES:
                raise ValueError(
                    'Invalid content type for file "{}": {}'.format(
                        file.name, file.content_type
                    )
                )
            if file.name.startswith('i_'):
                isa_data['investigation']['path'] = file.name
                isa_data['investigation']['tsv'] = file.read().decode('utf-8')
            elif file.name.startswith('s_'):
                isa_data['studies'][file.name] = {
                    'tsv': file.read().decode('utf-8')
                }
            elif file.name.startswith('a_'):
                isa_data['assays'][file.name] = {
                    'tsv': file.read().decode('utf-8')
                }

        return isa_data

    def get_warnings(self):
        """Return warnings from previous operation"""
        return self._warnings

    # Import -------------------------------------------------------------------

    @classmethod
    def _get_zip_path(cls, inv_path, file_path):
        return '{}{}{}'.format(
            inv_path, '/' if inv_path else '', str(file_path)
        )

    @classmethod
    def _get_study(cls, o):
        """Return study for a potentially unknown type of object"""
        if type(o) == Study:
            return o
        elif hasattr(o, 'study'):
            return o.study

    @classmethod
    def _import_ref_val(cls, o):
        """Get altamISA string/ref value"""
        if isinstance(o, (isa_models.OntologyRef, isa_models.OntologyTermRef)):
            o = attr.asdict(o)
            if o and 'value' in o and isinstance(o['value'], str):
                o['value'] = o['value'].strip()
            return o
        elif isinstance(o, str):
            return o.strip()

    @classmethod
    def _import_multi_val(cls, o):
        """Get value where the member type can vary"""
        if isinstance(o, list) and len(o) > 1:
            return [cls._import_ref_val(x) for x in o]
        elif isinstance(o, list) and len(o) == 1:
            o = o[0]  # Store lists of 1 item as single objects
        return cls._import_ref_val(o)

    @classmethod
    def _import_ontology_vals(cls, vals):
        """Get value data from potential ontology references"""
        ret = {}
        for v in vals:
            ret[v.name] = {
                'unit': cls._import_multi_val(v.unit)
                if hasattr(v, 'unit')
                else None,
                'value': cls._import_multi_val(v.value),
            }
        return ret

    @classmethod
    def _import_comments(cls, comments):
        """Get comments field as dict"""
        return {v.name: v.value for v in comments}

    @classmethod
    def _import_tuple_list(cls, tuples):
        """Get list of dicts from tuples for JSONField"""
        if type(tuples) == dict:
            return [cls._import_multi_val(v) for v in tuples.values()]
        elif type(tuples) in [tuple, list]:
            return [cls._import_multi_val(v) for v in tuples]

    @classmethod
    def _import_publications(cls, publications):
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
                'status': cls._import_ref_val(v.status),
                'comments': cls._import_comments(v.comments),
                'headers': v.headers,
            }
            for v in publications
        ]

    @classmethod
    def _import_contacts(cls, contacts):
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
                'role': cls._import_ref_val(v.role),
                'comments': cls._import_comments(v.comments),
                'headers': v.headers,
            }
            for v in contacts
        ]

    @classmethod
    def _import_materials(cls, materials, db_parent, obj_lookup):
        """
        Create material objects in Django database.

        :param materials: altamISA materials dict
        :param db_parent: Parent Django db object (Assay or Study)
        :param obj_lookup: Dictionary for in-memory lookup
        """
        material_vals = []
        study = cls._get_study(db_parent)

        # Fail if attempting to import an empty table
        if len(materials.values()) == 0:
            raise SampleSheetImportException(
                'No materials in {} "{}": Importing sheets with tables '
                'containing zero lines is currently not supported.'.format(
                    db_parent.__class__.__name__.lower(), db_parent.file_name
                )
            )

        for m in materials.values():
            item_type = MATERIAL_TYPE_MAP[m.type]
            # Common values
            values = {
                'item_type': item_type,
                'material_type': m.type,
                'extra_material_type': cls._import_multi_val(m.material_type),
                'name': m.name.strip(),
                'unique_name': m.unique_name,
                'alt_names': get_alt_names(m.name),
                'study': study,
                'headers': m.headers,
            }
            if type(db_parent) == Assay:
                values['assay'] = db_parent
            # NOTE: Extract label stored as JSON since altamISA 0.1 update
            if m.extract_label:
                values['extract_label'] = cls._import_multi_val(m.extract_label)
            if m.characteristics:
                values['characteristics'] = cls._import_ontology_vals(
                    m.characteristics
                )
            if m.factor_values:
                values['factor_values'] = cls._import_ontology_vals(
                    m.factor_values
                )
            values['comments'] = cls._import_comments(m.comments)
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

    @classmethod
    def _import_processes(
        cls, processes, db_parent, obj_lookup, protocol_lookup
    ):
        """
        Create processes of a process sequence in the database.

        :param processes: Process sequence of a study or an assay in altamISA
        :param db_parent: Parent study or assay
        :param obj_lookup: Dictionary for in-memory material/process lookup
        :param protocol_lookup: Dictionary for in-memory protocol lookup
        """
        study = cls._get_study(db_parent)
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
                'name': p.name.strip() if p.name else None,
                'unique_name': p.unique_name,
                'name_type': p.name_type,
                'protocol': protocol,
                'assay': db_parent if type(db_parent) == Assay else None,
                'study': study,
                'performer': p.performer,
                'perform_date': p.date if p.date else None,
                'array_design_ref': p.array_design_ref,
                'first_dimension': cls._import_multi_val(p.first_dimension)
                if p.first_dimension
                else {},
                'second_dimension': cls._import_multi_val(p.second_dimension)
                if p.second_dimension
                else {},
                'headers': p.headers,
                'comments': cls._import_comments(p.comments),
            }
            # Parameter values
            if p.parameter_values:
                values['parameter_values'] = cls._import_ontology_vals(
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

    @classmethod
    def _import_arcs(cls, arcs, db_parent):
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

    @transaction.atomic
    def import_isa(
        self,
        isa_data,
        project,
        archive_name=None,
        user=None,
        replace=False,
        replace_uuid=None,
        save_isa=True,
    ):
        """
        Import ISA investigation and its studies/assays from a dictionary of
        ISA-Tab files into the SODAR database using the altamISA parser.

        :param isa_data: Dictionary of files for a single ISA-Tab investigation
        :param project: Project object
        :param archive_name: Name of the original archive (string, optional)
        :param user: User initiating the operation (User or None)
        :param replace: Whether replacing an existing sheet (bool)
        :param replace_uuid: Investigation UUID if replacing (UUID or string)
        :param save_isa: Save ISA-Tab as backup after importing (bool)
        :return: Investigation
        :raise: SampleSheetExportException if critical warnings are raised
        """
        t_start = time.time()
        logger.info('altamISA version: {}'.format(altamisa.__version__))
        logger.info(
            'Importing investigation{}..'.format(
                ' from archive "{}"'.format(archive_name)
                if archive_name
                else ''
            )
        )

        input_name = isa_data['investigation']['path'].split('/')[-1]
        input_file = io.StringIO(isa_data['investigation']['tsv'])

        # Parse and validate investigation
        with warnings.catch_warnings(record=True) as ws:
            isa_inv = InvestigationReader.from_stream(
                input_file=input_file, filename=input_name
            ).read()
            InvestigationValidator(isa_inv).validate()

        # Create investigation
        values = {
            'project': project,
            'identifier': isa_inv.info.identifier,
            'title': isa_inv.info.title,
            'description': isa_inv.info.description,
            'file_name': isa_data['investigation']['path'],
            'ontology_source_refs': self._import_tuple_list(
                isa_inv.ontology_source_refs
            ),
            'publications': self._import_publications(isa_inv.publications),
            'contacts': self._import_contacts(isa_inv.contacts),
            'headers': isa_inv.info.headers,
            'comments': self._import_comments(isa_inv.info.comments),
            'submission_date': isa_inv.info.submission_date,
            'public_release_date': isa_inv.info.public_release_date,
            'parser_version': altamisa.__version__,
            'archive_name': archive_name,
        }
        db_investigation = Investigation.objects.create(**values)
        # Handle parser warnings for investigation
        self._handle_warnings(ws, db_investigation)
        logger.info(
            'Imported investigation "{}"'.format(db_investigation.title)
        )
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
            logger.info('Importing study "{}"..'.format(isa_study.info.title))
            obj_lookup = {}  # Lookup dict for study materials and processes
            study_id = 'p{}-s{}'.format(project.pk, study_count)
            input_name = str(isa_study.info.path)
            if input_name not in isa_data['studies']:
                raise SampleSheetImportException(
                    'Study not found in import data: "{}"'.format(input_name)
                )
            input_file = io.StringIO(isa_data['studies'][input_name]['tsv'])

            # Parse and validate study file
            with warnings.catch_warnings(record=True) as ws:
                try:
                    s = StudyReader.from_stream(
                        study_id=study_id,
                        input_file=input_file,
                        filename=input_name,
                    ).read()
                    StudyValidator(isa_inv, isa_study, s).validate()
                except Exception as ex:
                    ex_msg = 'altamISA exception in study "{}": {}'.format(
                        isa_study.info.title, ex
                    )
                    logger.error(ex_msg)
                    raise Exception(ex_msg)

            values = {
                'identifier': isa_study.info.identifier,
                'file_name': isa_study.info.path,
                'investigation': db_investigation,
                'title': isa_study.info.title,
                'description': isa_study.info.description,
                'study_design': [attr.asdict(x) for x in isa_study.designs],
                'publications': self._import_publications(
                    isa_study.publications
                ),
                'contacts': self._import_contacts(isa_study.contacts),
                'factors': {
                    k: attr.asdict(v) for k, v in isa_study.factors.items()
                },
                'comments': self._import_comments(isa_study.info.comments),
                'submission_date': isa_study.info.submission_date,
                'public_release_date': isa_study.info.public_release_date,
                'headers': isa_study.info.headers,
            }
            db_study = Study.objects.create(**values)
            db_studies.append(db_study)
            # Handle parser warnings for study
            self._handle_warnings(ws, db_study)
            logger.info('Imported study "{}"'.format(db_study.title))

            # Create protocols
            protocol_vals = []

            for isa_prot in isa_study.protocols.values():
                protocol_vals.append(
                    {
                        'name': isa_prot.name.strip(),
                        'study': db_study,
                        'protocol_type': self._import_multi_val(isa_prot.type),
                        'description': isa_prot.description,
                        'uri': isa_prot.uri,
                        'version': isa_prot.version,
                        'parameters': self._import_tuple_list(
                            isa_prot.parameters
                        ),
                        'components': self._import_tuple_list(
                            isa_prot.components
                        ),
                        'comments': self._import_comments(isa_prot.comments),
                        'headers': isa_prot.headers,
                    }
                )

            protocols = Protocol.objects.bulk_create(
                [Protocol(**v) for v in protocol_vals]
            )
            protocol_lookup = {
                p.name: p for p in protocols
            }  # Per study, no update
            logger.debug(
                'Added {} protocols in study "{}"'.format(
                    len(protocols), db_study.title
                )
            )

            # Create study materials
            self._import_materials(s.materials, db_study, obj_lookup)

            # Create study processes
            self._import_processes(
                s.processes, db_study, obj_lookup, protocol_lookup
            )

            # Create study arcs
            self._import_arcs(s.arcs, db_study)

            assay_count = 0
            assay_paths = sorted([a.path for a in isa_study.assays])

            for assay_path in assay_paths:
                isa_assay = next(
                    (a_i for a_i in isa_study.assays if a_i.path == assay_path),
                    None,
                )
                logger.info('Importing assay "{}"..'.format(isa_assay.path))
                assay_id = 'a{}'.format(assay_count)
                # HACK to fake a file for altamISA
                input_name = str(isa_assay.path)
                if input_name not in isa_data['assays']:
                    raise SampleSheetImportException(
                        'Assay not found in import data: "{}"'.format(
                            input_name
                        )
                    )
                input_file = io.StringIO(isa_data['assays'][input_name]['tsv'])

                # Parse and validate assay file
                with warnings.catch_warnings(record=True) as ws:
                    try:
                        a = AssayReader.from_stream(
                            study_id=study_id,
                            assay_id=assay_id,
                            input_file=input_file,
                            filename=input_name,
                        ).read()
                        AssayValidator(
                            isa_inv, isa_study, isa_assay, a
                        ).validate()
                    except Exception as ex:
                        ex_msg = 'altamISA exception in assay "{}": {}'.format(
                            isa_assay.path, ex
                        )
                        logger.error(ex_msg)
                        raise Exception(ex_msg)

                logger.debug('altamISA assay import OK')

                values = {
                    'file_name': isa_assay.path,
                    'study': db_study,
                    'measurement_type': self._import_multi_val(
                        isa_assay.measurement_type
                    ),
                    'technology_type': self._import_multi_val(
                        isa_assay.technology_type
                    ),
                    'technology_platform': isa_assay.platform,
                    'comments': self._import_comments(isa_assay.comments),
                    'headers': isa_assay.headers,
                }
                db_assay = Assay.objects.create(**values)
                # Handle parser warnings for assay
                self._handle_warnings(ws, db_assay)
                logger.info(
                    'Imported assay "{}" in study "{}"'.format(
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
                self._import_materials(assay_materials, db_assay, obj_lookup)

                # Create assay processes
                self._import_processes(
                    a.processes, db_assay, obj_lookup, protocol_lookup
                )

                # Create assay arcs
                self._import_arcs(a.arcs, db_assay)
                assay_count += 1

            study_count += 1

        # Raise exception if we got criticals and don't accept them
        cc = self._warnings['critical_count']
        if not self._allow_critical and cc > 0:
            ex_msg = (
                '{} critical warning{} raised by altamISA, '
                'import failed'.format(cc, 's' if cc != 1 else '')
            )
            raise SampleSheetImportException(ex_msg, self._warnings)

        # Ensure we can build the table reference, if not then fail
        logger.debug('Ensuring studies can be rendered..')
        for study in db_studies:
            # Throws an exception if we are unable to build this
            SampleSheetTableBuilder.build_study_reference(study)
        logger.debug('Rendering OK')

        # Store parser warnings (only if warnings were raised)
        if not self._warnings['all_ok']:
            logger.debug(
                'Warnings raised, storing in investigation.parser_warnings'
            )
            db_investigation.parser_warnings = self._warnings
            db_investigation.save()

        logger.info(
            'Import of investigation "{}" OK ({:.1f}s)'.format(
                db_investigation.title, time.time() - t_start
            )
        )

        # Save original ISA-Tab data
        # TODO: TBD: Prevent saving if previous data matches current one?
        if save_isa:
            tags = ['IMPORT']
            if replace:
                tags.append('REPLACE')
            self.save_isa(
                project=project,
                inv_uuid=replace_uuid
                if replace and replace_uuid
                else db_investigation.sodar_uuid,
                isa_data=isa_data,
                tags=tags,
                user=user,
                archive_name=archive_name,
            )

        return db_investigation

    # Export -------------------------------------------------------------------

    @classmethod
    def _get_arc_nodes(cls, nodes, arcs):
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

    @classmethod
    def _export_value(cls, value):
        """
        Build a "FreeTextOrTermRef" value out of a string/dict value in a
        JSONField. Can also be used for units.

        :param value: String or dict
        :return: String or OntologyTermRef
        """
        if isinstance(value, str):
            return value
        elif isinstance(value, list):
            return [cls._export_value(x) for x in value]
        elif isinstance(value, dict):
            if not value:  # Empty dict
                return None  # {} is not cool to altamISA
            return isa_models.OntologyTermRef(
                name=value['name'],
                accession=value['accession'],
                ontology_name=value['ontology_name'],
            )

    @classmethod
    def _export_comments(cls, comments):
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

    @classmethod
    def _export_publications(cls, publications):
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
                status=cls._export_value(v['status']),
                comments=cls._export_comments(v['comments']),
                headers=v['headers'],
            )
            for v in publications
        )

    @classmethod
    def _export_contacts(cls, contacts):
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
                role=cls._export_value(v['role']),
                comments=cls._export_comments(v['comments']),
                headers=v['headers'],
            )
            for v in contacts
        )

    @classmethod
    def _export_source_refs(cls, source_refs):
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
                comments=cls._export_comments(v['comments']),
                description=v['description'],
                headers=v['headers'],
            )
            for v in source_refs
        }

    @classmethod
    def _export_study_design(cls, study_design):
        """
        Build study design descriptors from a JSONField in a Study object.

        :param study_design: List from a study_design JSONField object
        :return: Tuple[DesignDescriptorsInfo]
        """
        return tuple(
            isa_models.DesignDescriptorsInfo(
                type=cls._export_value(v['type']),
                comments=cls._export_comments(v['comments']),
                headers=v['headers'],
            )
            for v in study_design
        )

    @classmethod
    def _export_components(cls, components):
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

    @classmethod
    def _export_characteristics(cls, characteristics):
        """
        Build characteristics from JSON stored in a SODAR model object.

        :param characteristics: Dict from a characteristics JSONField
        :return: Tuple[Characteristics]
        """
        return tuple(
            isa_models.Characteristics(
                name=k,
                value=[cls._export_value(v['value'])]
                if not isinstance(v['value'], list)
                else cls._export_value(v['value']),
                unit=cls._export_value(v['unit']),
            )
            for k, v in characteristics.items()
        )

    @classmethod
    def _export_factors(cls, factors):
        """
        Build factor references from JSON stored in a Study object.

        :param factors: Dict from a factors JSONField
        :return: Dict[str, FactorInfo]
        """
        return {
            k: isa_models.FactorInfo(
                name=k,
                type=cls._export_value(v['type']),
                comments=cls._export_comments(v['comments']),
                headers=v['headers'],
            )
            for k, v in factors.items()
        }

    @classmethod
    def _export_factor_values(cls, factor_values):
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
                value=cls._export_value(v['value']),
                unit=cls._export_value(v['unit']),
            )
            for k, v in factor_values.items()
        )

    @classmethod
    def _export_parameters(cls, parameters):
        """
        Build parameters for a protocol from JSON stored in a Protocol
        object.

        :param parameters: List from a parameters JSONField
        :return: Dict
        """
        return {p['name']: cls._export_value(p) for p in parameters}

    @classmethod
    def _export_param_values(cls, param_values):
        """
        Build parameter values from JSON stored in a Process object.

        :param param_values: Dict from a parameter_values JSONField
        :return: Tuple[ParameterValue]
        """
        return tuple(
            isa_models.ParameterValue(
                name=k,
                value=[cls._export_value(v['value'])]
                if not isinstance(v['value'], list)
                else cls._export_value(v['value']),
                unit=cls._export_value(v['unit']),
            )
            for k, v in param_values.items()
        )

    @classmethod
    def _export_arcs(cls, arcs):
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

    @classmethod
    def _export_materials(cls, materials, study_data=True):
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
                extract_label = cls._export_value(m.extract_label)
            ret[m.unique_name] = isa_models.Material(
                type=m.material_type
                if m.material_type
                else MATERIAL_TYPE_EXPORT_MAP[m.item_type],
                unique_name=m.unique_name,
                name=m.name,
                extract_label=extract_label,
                characteristics=cls._export_characteristics(m.characteristics)
                if not sample_in_assay
                else (),
                comments=cls._export_comments(m.comments)
                if not sample_in_assay
                else (),
                factor_values=cls._export_factor_values(m.factor_values)
                if study_data
                else tuple(),
                material_type=cls._export_value(m.extra_material_type),
                headers=headers,
            )
        return ret

    @classmethod
    def _export_processes(cls, processes):
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
                parameter_values=cls._export_param_values(p.parameter_values),
                comments=cls._export_comments(p.comments),
                array_design_ref=p.array_design_ref,
                first_dimension=cls._export_value(p.first_dimension),
                second_dimension=cls._export_value(p.second_dimension),
                headers=p.headers,
            )
        return ret

    def export_isa(self, investigation):
        """
        Import ISA investigation and its studies/assays from the SODAR database
        model into an ISA-Tab archive.

        :param investigation: Investigation object
        :return: Dict
        """
        # Create StudyInfo objects for studies
        isa_study_infos = []
        isa_studies = []
        isa_assays = {}
        study_idx = 0
        logger.info('Converting database objects into altamISA models..')

        for study in investigation.studies.all().order_by('file_name'):
            # Get all materials and nodes in study and its assays
            all_materials = {
                m.unique_name: m for m in study.materials.all().order_by('pk')
            }
            all_processes = {
                p.unique_name: p for p in study.processes.all().order_by('pk')
            }
            # Get study materials
            study_materials = self._export_materials(
                self._get_arc_nodes(all_materials, study.arcs)
            )
            study_processes = self._export_processes(
                self._get_arc_nodes(all_processes, study.arcs)
            )

            # Create study
            isa_study = isa_models.Study(
                file=study.file_name,
                header=study.headers,
                materials=study_materials,
                processes=study_processes,
                arcs=self._export_arcs(study.arcs),
            )
            isa_studies.append(isa_study)
            isa_assay_infos = []
            isa_assays[study_idx] = {}
            assay_idx = 0

            # Create AssayInfo objects for assays
            for assay in study.assays.all().order_by('file_name'):
                assay_info = isa_models.AssayInfo(
                    measurement_type=self._export_value(assay.measurement_type),
                    technology_type=self._export_value(assay.technology_type),
                    platform=assay.technology_platform,
                    path=assay.file_name,
                    comments=self._export_comments(assay.comments),
                    headers=assay.headers,
                )
                isa_assay_infos.append(assay_info)

                # Get assay materials and processes
                assay_materials = self._export_materials(
                    self._get_arc_nodes(all_materials, assay.arcs),
                    study_data=False,
                )
                assay_processes = self._export_processes(
                    self._get_arc_nodes(all_processes, assay.arcs)
                )

                # Create actual assay and parse its members
                isa_assay = isa_models.Assay(
                    file=assay.file_name,
                    header=tuple(assay.headers),
                    materials=assay_materials,
                    processes=assay_processes,
                    arcs=self._export_arcs(assay.arcs),
                )
                isa_assays[study_idx][assay_idx] = isa_assay
                assay_idx += 1

            # Create protocols for study
            isa_protocols = {}

            for protocol in study.protocols.all():
                isa_protocols[protocol.name] = isa_models.ProtocolInfo(
                    name=protocol.name,
                    type=self._export_value(protocol.protocol_type),
                    description=protocol.description,
                    uri=protocol.uri,
                    version=protocol.version,
                    parameters=self._export_parameters(protocol.parameters),
                    components=self._export_components(protocol.components),
                    comments=self._export_comments(protocol.comments),
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
                comments=self._export_comments(study.comments),
                headers=study.headers,
            )

            # Create StudyInfo object
            isa_study_info = isa_models.StudyInfo(
                info=isa_study_basic,
                designs=self._export_study_design(study.study_design),
                publications=self._export_publications(study.publications),
                factors=self._export_factors(study.factors),
                assays=tuple(isa_assay_infos),
                protocols=isa_protocols,
                contacts=self._export_contacts(study.contacts),
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
            comments=self._export_comments(investigation.comments),
            headers=investigation.headers,
        )

        # Create InvestigationInfo
        inv_info = isa_models.InvestigationInfo(
            ontology_source_refs=self._export_source_refs(
                investigation.ontology_source_refs
            ),
            info=inv_basic,
            publications=self._export_publications(investigation.publications),
            contacts=self._export_contacts(investigation.contacts),
            studies=tuple(isa_study_infos),
        )

        logger.info('Models converted')

        # Prepare return data
        # (the ZIP file preparing and serving should happen in the view)
        ret = {'investigation': {}, 'studies': {}, 'assays': {}}
        inv_out = io.StringIO()

        logger.info('Validating and exporting investigation..')

        # Write investigation
        with warnings.catch_warnings(record=True) as ws:
            InvestigationValidator(inv_info).validate()

        # Handle parser warnings for investigation
        self._handle_warnings(ws, investigation)

        with warnings.catch_warnings(record=True) as ws:
            InvestigationWriter.from_stream(
                inv_info, output_file=inv_out
            ).write()

        # Handle parser warnings for investigation
        self._handle_warnings(ws, investigation)

        ret['investigation']['path'] = inv_info.info.path
        ret['investigation']['tsv'] = inv_out.getvalue()
        inv_out.close()
        logger.info('Exported investigation')

        # Write studies
        for study_idx, study_info in enumerate(inv_info.studies):
            db_study = Study.objects.get(
                investigation=investigation,
                identifier=study_info.info.identifier,
            )
            logger.info(
                'Validating and exporting study "{}"..'.format(
                    db_study.file_name
                )
            )
            with warnings.catch_warnings(record=True) as ws:
                StudyValidator(
                    inv_info, study_info, isa_studies[study_idx]
                ).validate()

            # Handle parser warnings for study
            self._handle_warnings(ws, db_study)

            study_out = io.StringIO()
            with warnings.catch_warnings(record=True) as ws:
                StudyWriter.from_stream(
                    isa_studies[study_idx], study_out
                ).write()

            # Handle parser warnings for study
            self._handle_warnings(ws, db_study)

            ret['studies'][study_info.info.path] = {'tsv': study_out.getvalue()}
            study_out.close()
            logger.info('Exported study "{}"'.format(db_study.file_name))

            # Write assays
            for assay_idx, assay_info in enumerate(study_info.assays):
                db_assay = Assay.objects.get(
                    study=db_study, file_name=assay_info.path
                )

                logger.info(
                    'Validating and exporting assay "{}"..'.format(
                        db_assay.file_name
                    )
                )

                with warnings.catch_warnings(record=True) as ws:
                    AssayValidator(
                        inv_info,
                        study_info,
                        assay_info,
                        isa_assays[study_idx][assay_idx],
                    ).validate()

                # Handle parser warnings for assay
                self._handle_warnings(ws, db_assay)

                assay_out = io.StringIO()
                with warnings.catch_warnings(record=True) as ws:
                    AssayWriter.from_stream(
                        isa_assays[study_idx][assay_idx], assay_out
                    ).write()

                # Handle parser warnings for assay
                self._handle_warnings(ws, db_assay)

                ret['assays'][assay_info.path] = {'tsv': assay_out.getvalue()}
                assay_out.close()
                logger.info('Exported assay "{}"'.format(db_assay.file_name))

        return ret

    @classmethod
    def save_isa(
        cls,
        project,
        inv_uuid,
        isa_data,
        tags=None,
        user=None,
        archive_name=None,
        description=None,
    ):
        """
        Save a copy of an ISA-Tab investigation into the SODAR database.

        :param project: Project object
        :param inv_uuid: Investigation UUID (UUID or string)
        :param isa_data: ISAtab file contents (dict)
        :param tags: Tags for the ISA-Tab (optional)
        :param user: User saving the ISA-Tab (optional)
        :param archive_name: File name of ISA-Tab archive (optional)
        :param description: ISATab description (string, optional)
        :return: ISATab object
        """
        db_isatab = ISATab.objects.create(
            project=project,
            investigation_uuid=inv_uuid,
            data=isa_data,
            tags=tags or [],
            user=user,
            archive_name=archive_name,
            description=description,
            parser_version=altamisa.__version__,
        )
        logger.info('ISA-Tab saved (UUID={})'.format(db_isatab.sodar_uuid))
        return db_isatab


# Exceptions -------------------------------------------------------------------


class SampleSheetImportException(Exception):
    """Sample sheet importing exception"""

    pass


class SampleSheetExportException(Exception):
    """Sample sheet exporting exception"""

    pass
