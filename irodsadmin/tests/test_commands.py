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
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

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
            *irodsorphans.get_assay_collections(),
            *irodsorphans.get_study_collections(),
            *irodsorphans.get_zone_collections(),
        )

    def tearDown(self):
        self.irods_session.collections.get('/omicsZone/projects').remove(
            force=True
        )

    def test_get_assay_collections(self):
        self.assertListEqual(
            irodsorphans.get_assay_collections(),
            ['assay_{}'.format(self.assay.sodar_uuid)],
        )

    def test_get_study_collections(self):
        self.assertListEqual(
            irodsorphans.get_study_collections(),
            ['study_{}'.format(self.study.sodar_uuid)],
        )

    def test_get_landingzone_collections(self):
        self.assertListEqual(
            irodsorphans.get_zone_collections(), [self.landing_zone.title],
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
                self.irods_session, self.expected_collections
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
                self.irods_session, self.expected_collections
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
                self.irods_session, self.expected_collections
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
                self.irods_session, self.expected_collections
            ),
            [orphan_path],
        )

    def test_command_irodsorphans_no_orphans(self):
        out = StringIO()
        call_command('irodsorphans', stdout=out)
        self.assertEqual('\n', out.getvalue())

    def test_command_irodsorphans_orphanated_assay(self):
        orphan_path = '{}/assay_{}'.format(
            self.irods_backend.get_path(self.study), str(uuid.uuid4())
        )
        self.irods_session.collections.create(orphan_path)
        out = StringIO()
        call_command('irodsorphans', stdout=out)
        self.assertEqual(orphan_path + '\n', out.getvalue())

    def test_command_irodsorphans_orphanated_study(self):
        orphan_path = '{}/sample_data/study_{}'.format(
            self.irods_backend.get_path(self.project), str(uuid.uuid4())
        )
        self.irods_session.collections.create(orphan_path)
        out = StringIO()
        call_command('irodsorphans', stdout=out)
        self.assertEqual(orphan_path + '\n', out.getvalue())

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
        self.assertEqual(orphan_path + '\n', out.getvalue())

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
        self.assertEqual(
            '{}\n{}\n'.format(orphan_path2, orphan_path), out.getvalue()
        )