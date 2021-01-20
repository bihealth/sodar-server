import os
import uuid
from unittest import skipIf

from django.conf import settings
from django.core.management import call_command
from django.utils.six import StringIO
from projectroles.constants import SODAR_CONSTANTS
from projectroles.models import Role
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin
from test_plus.test import TestCase


from irodsadmin.management.commands import irodsorphans
from landingzones.tests.test_models import LandingZoneMixin
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

SHEET_PATH = SHEET_DIR + 'i_small.zip'

ZONE_TITLE = '20180503_172456_test_zone'
ZONE_DESC = 'description'

IRODS_BACKEND_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_BACKEND_SKIP_MSG = 'iRODS backend not enabled in settings'


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestIrodsOrphans(
    ProjectMixin,
    SampleSheetIOMixin,
    RoleAssignmentMixin,
    LandingZoneMixin,
    TestCase,
):
    """Test functions from irodsorphans command."""

    def setUp(self):
        super().setUp()

        self.maxDiff = None

        # Init super user
        self.user = self.make_user('user')
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()

        # Init roles
        self.role_owner = Role.objects.get_or_create(name=PROJECT_ROLE_OWNER)[0]

        # Init project with owner
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None
        )
        self.as_owner = self._make_assignment(
            self.project, self.user, self.role_owner
        )

        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.investigation.irods_status = True
        self.investigation.save()
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.assay.measurement_type = 'genome sequencing'
        self.assay.technology_type = 'nucleotide sequencing'
        self.assay.save()

        # Create LandingZone
        self.landing_zone = self._make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.as_owner.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        self.irods_backend = get_backend_api('omics_irods')
        self.irods_session = self.irods_backend.get_session()

        # Create the actual assay, study and landing zone in the irods session
        self.irods_session.collections.create(
            self.irods_backend.get_path(self.assay)
        )
        self.irods_session.collections.create(
            self.irods_backend.get_path(self.landing_zone)
        )

        self.expected_collections = (
            *irodsorphans.get_assay_collections(
                [self.assay], self.irods_backend
            ),
            *irodsorphans.get_study_collections(
                [self.study], self.irods_backend
            ),
            *irodsorphans.get_zone_collections(self.irods_backend),
            *irodsorphans.get_project_collections(self.irods_backend),
            *irodsorphans.get_assay_subcollections(
                [self.study], self.irods_backend
            ),
        )

    def tearDown(self):
        self.irods_session.collections.get('/omicsZone/projects').remove(
            force=True
        )

    def test_get_assay_collections(self):
        self.assertListEqual(
            irodsorphans.get_assay_collections(
                [self.assay], self.irods_backend
            ),
            [self.irods_backend.get_path(self.assay)],
        )

    def test_get_study_collections(self):
        self.assertListEqual(
            irodsorphans.get_study_collections(
                [self.study], self.irods_backend
            ),
            [self.irods_backend.get_path(self.study)],
        )

    def test_get_landingzone_collections(self):
        self.assertListEqual(
            irodsorphans.get_zone_collections(self.irods_backend),
            [self.irods_backend.get_path(self.landing_zone)],
        )

    def test_get_project_collections(self):
        self.assertListEqual(
            irodsorphans.get_project_collections(self.irods_backend),
            [self.irods_backend.get_path(self.project)],
        )

    def test_get_assay_subcollections(self):
        assay_path = self.irods_backend.get_path(self.assay)
        self.assertListEqual(
            irodsorphans.get_assay_subcollections(
                [self.study], self.irods_backend
            ),
            [
                assay_path + '/0815-N1-DNA1',
                assay_path + '/0815-T1-DNA1',
                assay_path + '/TrackHubs',
                assay_path + '/ResultsReports',
                assay_path + '/MiscFiles',
            ],
        )

    def test_is_landingzone(self):
        collection = self.irods_session.collections.get(
            self.irods_backend.get_path(self.landing_zone)
        )
        self.assertTrue(irodsorphans.is_zone(collection))

    def test_is_assay_or_study_assay(self):
        collection = self.irods_session.collections.get(
            self.irods_backend.get_path(self.assay)
        )
        self.assertTrue(irodsorphans.is_assay_or_study(collection))

    def test_is_assay_or_study_study(self):
        collection = self.irods_session.collections.get(
            self.irods_backend.get_path(self.study)
        )
        self.assertTrue(irodsorphans.is_assay_or_study(collection))

    def test_is_project(self):
        collection = self.irods_session.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertTrue(irodsorphans.is_project(collection))

    def test_is_no_landingzone(self):
        collection = self.irods_session.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertFalse(irodsorphans.is_zone(collection))

    def test_is_no_assay_assay_or_study(self):
        collection = self.irods_session.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertFalse(irodsorphans.is_assay_or_study(collection))

    def test_no_orphans(self):
        self.assertListEqual(
            irodsorphans.get_orphans(
                self.irods_session,
                self.irods_backend,
                self.expected_collections,
                [self.assay],
            ),
            [],
        )

    def test_orphanated_assay(self):
        orphan_path = '{}/assay_{}'.format(
            self.irods_backend.get_path(self.study), str(uuid.uuid4())
        )
        self.irods_session.collections.create(orphan_path)
        self.assertListEqual(
            irodsorphans.get_orphans(
                self.irods_session,
                self.irods_backend,
                self.expected_collections,
                [self.assay],
            ),
            [orphan_path],
        )

    def test_orphanated_study(self):
        orphan_path = '{}/sample_data/study_{}'.format(
            self.irods_backend.get_path(self.project), str(uuid.uuid4())
        )
        self.irods_session.collections.create(orphan_path)
        self.assertListEqual(
            irodsorphans.get_orphans(
                self.irods_session,
                self.irods_backend,
                self.expected_collections,
                [self.assay],
            ),
            [orphan_path],
        )

    def test_orphanated_landingzone(self):
        collection = '20201031_123456'
        orphan_path = '{}/landing_zones/{}/{}/{}'.format(
            self.irods_backend.get_path(self.project),
            self.user.username,
            self.study.get_display_name().replace(' ', '_').lower(),
            collection,
        )
        self.irods_session.collections.create(orphan_path)
        self.assertListEqual(
            irodsorphans.get_orphans(
                self.irods_session,
                self.irods_backend,
                self.expected_collections,
                [self.assay],
            ),
            [orphan_path],
        )

    def test_orphanated_project(self):
        collection = 'aa/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        orphan_path = '{}/{}'.format(
            os.path.dirname(
                os.path.dirname(self.irods_backend.get_path(self.project))
            ),
            collection,
        )
        self.irods_session.collections.create(orphan_path)
        self.assertListEqual(
            irodsorphans.get_orphans(
                self.irods_session,
                self.irods_backend,
                self.expected_collections,
                [self.assay],
            ),
            [orphan_path],
        )

    def test_orphanated_assay_subs(self):
        collection = 'UnexpectedCollection'
        orphan_path = '{}/{}'.format(
            self.irods_backend.get_path(self.assay), collection
        )
        self.irods_session.collections.create(orphan_path)
        self.assertListEqual(
            irodsorphans.get_orphans(
                self.irods_session,
                self.irods_backend,
                self.expected_collections,
                [self.assay],
            ),
            [orphan_path],
        )

    def test_get_output(self):
        orphan_path = '{}/assay_{}'.format(
            self.irods_backend.get_path(self.study), str(uuid.uuid4())
        )
        self.irods_session.collections.create(orphan_path)
        orphans = irodsorphans.get_orphans(
            self.irods_session,
            self.irods_backend,
            self.expected_collections,
            [self.assay],
        )
        self.assertListEqual(
            irodsorphans.get_output(orphans, self.irods_backend),
            [
                '{};{};{};0;0 bytes'.format(
                    str(self.project.sodar_uuid),
                    self.project.get_full_title(),
                    orphan_path,
                )
            ],
        )

    def test_command_irodsorphans_no_orphans(self):
        out = StringIO()
        call_command('irodsorphans', stdout=out)
        self.assertEqual('', out.getvalue())

    def test_command_irodsorphans_orphanated_assay(self):
        orphan_path = '{}/assay_{}'.format(
            self.irods_backend.get_path(self.study), str(uuid.uuid4())
        )
        self.irods_session.collections.create(orphan_path)
        out = StringIO()
        call_command('irodsorphans', stdout=out)
        expected = '{};{};{};0;0 bytes\n'.format(
            str(self.project.sodar_uuid),
            self.project.get_full_title(),
            orphan_path,
        )
        self.assertEqual(expected, out.getvalue())

    def test_command_irodsorphans_orphanated_study(self):
        orphan_path = '{}/sample_data/study_{}'.format(
            self.irods_backend.get_path(self.project), str(uuid.uuid4())
        )
        self.irods_session.collections.create(orphan_path)
        out = StringIO()
        call_command('irodsorphans', stdout=out)
        expected = '{};{};{};0;0 bytes\n'.format(
            str(self.project.sodar_uuid),
            self.project.get_full_title(),
            orphan_path,
        )
        self.assertEqual(expected, out.getvalue())

    def test_command_irodsorphans_orphanated_landingzone(self):
        collection = '20201031_123456'
        orphan_path = '{}/landing_zones/{}/{}/{}'.format(
            self.irods_backend.get_path(self.project),
            self.user.username,
            self.study.get_display_name().replace(' ', '_').lower(),
            collection,
        )
        self.irods_session.collections.create(orphan_path)
        out = StringIO()
        call_command('irodsorphans', stdout=out)
        expected = '{};{};{};0;0 bytes\n'.format(
            str(self.project.sodar_uuid),
            self.project.get_full_title(),
            orphan_path,
        )
        self.assertEqual(expected, out.getvalue())

    def test_command_irodsorphans_orphanated_project(self):
        collection = 'aa/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        orphan_path = '{}/{}'.format(
            os.path.dirname(
                os.path.dirname(self.irods_backend.get_path(self.project))
            ),
            collection,
        )
        self.irods_session.collections.create(orphan_path)
        out = StringIO()
        call_command('irodsorphans', stdout=out)
        expected = 'N/A;N/A;{};0;0 bytes\n'.format(orphan_path)
        self.assertEqual(expected, out.getvalue())

    def test_command_irodsorphans_orphanated_assay_sub(self):
        collection = 'UnexpectedCollection'
        orphan_path = '{}/{}'.format(
            self.irods_backend.get_path(self.assay), collection
        )
        self.irods_session.collections.create(orphan_path)
        out = StringIO()
        call_command('irodsorphans', stdout=out)
        expected = '{};{};{};0;0 bytes\n'.format(
            str(self.project.sodar_uuid),
            self.project.get_full_title(),
            orphan_path,
        )
        self.assertEqual(expected, out.getvalue())

    def test_command_irodsorphans_multiple(self):
        orphan_path = '{}/sample_data/study_{}'.format(
            self.irods_backend.get_path(self.project), str(uuid.uuid4())
        )
        self.irods_session.collections.create(orphan_path)
        collection = '20201031_123456'
        orphan_path2 = '{}/landing_zones/{}/{}/{}'.format(
            self.irods_backend.get_path(self.project),
            self.user.username,
            self.study.get_display_name().replace(' ', '_').lower(),
            collection,
        )
        self.irods_session.collections.create(orphan_path2)
        out = StringIO()
        call_command('irodsorphans', stdout=out)
        expected = '{};{};{};0;0 bytes\n'.format(
            str(self.project.sodar_uuid),
            self.project.get_full_title(),
            orphan_path2,
        )
        expected += '{};{};{};0;0 bytes\n'.format(
            str(self.project.sodar_uuid),
            self.project.get_full_title(),
            orphan_path,
        )
        self.assertEqual(expected, out.getvalue())
