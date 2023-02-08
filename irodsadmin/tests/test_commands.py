"""Management command tests for the irodsadmin app"""

import io
import os
import uuid

from django.core.management import call_command

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.constants import SODAR_CONSTANTS
from projectroles.models import Role
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

# Landingzones dependency
from landingzones.tests.test_models import LandingZoneMixin

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

from irodsadmin.management.commands import irodsorphans


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_TITLE = '20180503_172456_test_zone'
ZONE_DESC = 'description'


class TestIrodsOrphans(
    ProjectMixin,
    SampleSheetIOMixin,
    RoleAssignmentMixin,
    LandingZoneMixin,
    TestCase,
):
    """Tests for the irodsorphans management command"""

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
        self.project = self.make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None
        )
        self.owner_as = self.make_assignment(
            self.project, self.user, self.role_owner
        )

        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.investigation.irods_status = True
        self.investigation.save()
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.assay.measurement_type = 'genome sequencing'
        self.assay.technology_type = 'nucleotide sequencing'
        self.assay.save()

        # Create LandingZone
        self.landing_zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        self.irods_backend = get_backend_api('omics_irods')
        self.irods = self.irods_backend.get_session_obj()

        # Create the actual assay, study and landing zone in the irods session
        self.irods.collections.create(self.irods_backend.get_path(self.assay))
        self.irods.collections.create(
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
        self.irods.collections.get(
            self.irods_backend.get_projects_path()
        ).remove(force=True)
        self.irods.cleanup()
        super().tearDown()

    def test_get_assay_collections(self):
        """Test get_assay_collections()"""
        self.assertListEqual(
            irodsorphans.get_assay_collections(
                [self.assay], self.irods_backend
            ),
            [self.irods_backend.get_path(self.assay)],
        )

    def test_get_study_collections(self):
        """Test get_study_collections()"""
        self.assertListEqual(
            irodsorphans.get_study_collections(
                [self.study], self.irods_backend
            ),
            [self.irods_backend.get_path(self.study)],
        )

    def test_get_zone_collections(self):
        """Test get_zone_collections()"""
        self.assertListEqual(
            irodsorphans.get_zone_collections(self.irods_backend),
            [self.irods_backend.get_path(self.landing_zone)],
        )

    def test_get_project_collections(self):
        """Test get_project_collections()"""
        self.assertListEqual(
            irodsorphans.get_project_collections(self.irods_backend),
            [self.irods_backend.get_path(self.project)],
        )

    def test_get_assay_subcollections(self):
        """Test get_assay_subcollections()"""
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

    def test_is_zone(self):
        """Test is_zone()"""
        collection = self.irods.collections.get(
            self.irods_backend.get_path(self.landing_zone)
        )
        self.assertTrue(irodsorphans.is_zone(collection))

    def test_is_assay_or_study_with_assay(self):
        """Test is_assay_or_study() with assay"""
        collection = self.irods.collections.get(
            self.irods_backend.get_path(self.assay)
        )
        self.assertTrue(irodsorphans.is_assay_or_study(collection))

    def test_is_assay_or_study_with_study(self):
        """Test is_assay_or_study() with study"""
        collection = self.irods.collections.get(
            self.irods_backend.get_path(self.study)
        )
        self.assertTrue(irodsorphans.is_assay_or_study(collection))

    def test_is_project(self):
        """Test is_project()"""
        collection = self.irods.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertTrue(irodsorphans.is_project(collection))

    def test_is_zone_invalid(self):
        """Test is_zone() with a non-landingzone collection"""
        collection = self.irods.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertFalse(irodsorphans.is_zone(collection))

    def test_is_assay_or_study_invalid(self):
        """Test is_assay_or_study() with non-assay/study collection"""
        collection = self.irods.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertFalse(irodsorphans.is_assay_or_study(collection))

    def test_get_orphans_none(self):
        """Test get_orphans() with no orphans available"""
        self.assertListEqual(
            irodsorphans.get_orphans(
                self.irods,
                self.irods_backend,
                self.expected_collections,
                [self.assay],
            ),
            [],
        )

    def test_get_orphans_assay(self):
        """Test get_orphans() with orphan assay"""
        orphan_path = '{}/assay_{}'.format(
            self.irods_backend.get_path(self.study), str(uuid.uuid4())
        )
        self.irods.collections.create(orphan_path)
        self.assertListEqual(
            irodsorphans.get_orphans(
                self.irods,
                self.irods_backend,
                self.expected_collections,
                [self.assay],
            ),
            [orphan_path],
        )

    def test_get_orphans_study(self):
        """Test get_orphans() with orphan study"""
        orphan_path = '{}/sample_data/study_{}'.format(
            self.irods_backend.get_path(self.project), str(uuid.uuid4())
        )
        self.irods.collections.create(orphan_path)
        self.assertListEqual(
            irodsorphans.get_orphans(
                self.irods,
                self.irods_backend,
                self.expected_collections,
                [self.assay],
            ),
            [orphan_path],
        )

    def test_get_orphans_zone(self):
        """Test get_orphans() with orphan landing zone"""
        collection = '20201031_123456'
        orphan_path = '{}/landing_zones/{}/{}/{}'.format(
            self.irods_backend.get_path(self.project),
            self.user.username,
            self.study.get_display_name().replace(' ', '_').lower(),
            collection,
        )
        self.irods.collections.create(orphan_path)
        self.assertListEqual(
            irodsorphans.get_orphans(
                self.irods,
                self.irods_backend,
                self.expected_collections,
                [self.assay],
            ),
            [orphan_path],
        )

    def test_get_orphans_project(self):
        """Test get_orphans() with orphan project"""
        collection = 'aa/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        orphan_path = '{}/{}'.format(
            os.path.dirname(
                os.path.dirname(self.irods_backend.get_path(self.project))
            ),
            collection,
        )
        self.irods.collections.create(orphan_path)
        self.assertListEqual(
            irodsorphans.get_orphans(
                self.irods,
                self.irods_backend,
                self.expected_collections,
                [self.assay],
            ),
            [orphan_path],
        )

    def test_get_orphans_assay_subs(self):
        """Test get_orphans() with orphan assay subcollections"""
        collection = 'UnexpectedCollection'
        orphan_path = '{}/{}'.format(
            self.irods_backend.get_path(self.assay), collection
        )
        self.irods.collections.create(orphan_path)
        self.assertListEqual(
            irodsorphans.get_orphans(
                self.irods,
                self.irods_backend,
                self.expected_collections,
                [self.assay],
            ),
            [orphan_path],
        )

    def test_get_output(self):
        """Test get_output()"""
        orphan_path = '{}/assay_{}'.format(
            self.irods_backend.get_path(self.study), str(uuid.uuid4())
        )
        self.irods.collections.create(orphan_path)
        orphans = irodsorphans.get_orphans(
            self.irods,
            self.irods_backend,
            self.expected_collections,
            [self.assay],
        )
        self.assertListEqual(
            irodsorphans.get_output(orphans, self.irods_backend, self.irods),
            [
                '{};{};{};0;0 bytes'.format(
                    str(self.project.sodar_uuid),
                    self.project.full_title,
                    orphan_path,
                )
            ],
        )

    def test_get_output_deleted_project(self):
        """Test get_output() with a deleted project"""
        project_uuid = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        collection = 'aa/' + project_uuid
        orphan_path = '{}/{}'.format(
            os.path.dirname(
                os.path.dirname(self.irods_backend.get_path(self.project))
            ),
            collection,
        )
        self.irods.collections.create(orphan_path)

        orphans = irodsorphans.get_orphans(
            self.irods,
            self.irods_backend,
            self.expected_collections,
            [self.assay],
        )
        self.assertListEqual(
            irodsorphans.get_output(orphans, self.irods_backend, self.irods),
            [
                '{};<DELETED>;{};0;0 bytes'.format(
                    project_uuid,
                    orphan_path,
                )
            ],
        )

    def test_command_no_orphans(self):
        """Test command with no orphans"""
        out = io.StringIO()
        call_command('irodsorphans', stdout=out)
        self.assertEqual('', out.getvalue())

    def test_command_orphan_assay(self):
        """Test command with orphan assay"""
        orphan_path = '{}/assay_{}'.format(
            self.irods_backend.get_path(self.study), str(uuid.uuid4())
        )
        self.irods.collections.create(orphan_path)
        out = io.StringIO()
        call_command('irodsorphans', stdout=out)
        expected = '{};{};{};0;0 bytes\n'.format(
            str(self.project.sodar_uuid),
            self.project.full_title,
            orphan_path,
        )
        self.assertEqual(expected, out.getvalue())

    def test_command_orphan_study(self):
        """Test command with orphan study"""
        orphan_path = '{}/sample_data/study_{}'.format(
            self.irods_backend.get_path(self.project), str(uuid.uuid4())
        )
        self.irods.collections.create(orphan_path)
        out = io.StringIO()
        call_command('irodsorphans', stdout=out)
        expected = '{};{};{};0;0 bytes\n'.format(
            str(self.project.sodar_uuid),
            self.project.full_title,
            orphan_path,
        )
        self.assertEqual(expected, out.getvalue())

    def test_command_orphan_zone(self):
        """Test command with orphan landing zone"""
        collection = '20201031_123456'
        orphan_path = '{}/landing_zones/{}/{}/{}'.format(
            self.irods_backend.get_path(self.project),
            self.user.username,
            self.study.get_display_name().replace(' ', '_').lower(),
            collection,
        )
        self.irods.collections.create(orphan_path)
        out = io.StringIO()
        call_command('irodsorphans', stdout=out)
        expected = '{};{};{};0;0 bytes\n'.format(
            str(self.project.sodar_uuid),
            self.project.full_title,
            orphan_path,
        )
        self.assertEqual(expected, out.getvalue())

    def test_command_orphan_project(self):
        """Test command with orphan project"""
        project_uuid = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        collection = 'aa/' + project_uuid
        orphan_path = '{}/{}'.format(
            os.path.dirname(
                os.path.dirname(self.irods_backend.get_path(self.project))
            ),
            collection,
        )
        self.irods.collections.create(orphan_path)
        out = io.StringIO()
        call_command('irodsorphans', stdout=out)
        expected = '{};<DELETED>;{};0;0 bytes\n'.format(
            project_uuid, orphan_path
        )
        self.assertEqual(expected, out.getvalue())

    def test_command_orphan_assay_sub(self):
        """Test command with orphan assay subcollection"""
        collection = 'UnexpectedCollection'
        orphan_path = '{}/{}'.format(
            self.irods_backend.get_path(self.assay), collection
        )
        self.irods.collections.create(orphan_path)
        out = io.StringIO()
        call_command('irodsorphans', stdout=out)
        expected = '{};{};{};0;0 bytes\n'.format(
            str(self.project.sodar_uuid),
            self.project.full_title,
            orphan_path,
        )
        self.assertEqual(expected, out.getvalue())

    def test_command_multiple(self):
        """Test command with multiple orphans"""
        orphan_path = '{}/sample_data/study_{}'.format(
            self.irods_backend.get_path(self.project), str(uuid.uuid4())
        )
        self.irods.collections.create(orphan_path)
        collection = '20201031_123456'
        orphan_path2 = '{}/landing_zones/{}/{}/{}'.format(
            self.irods_backend.get_path(self.project),
            self.user.username,
            self.study.get_display_name().replace(' ', '_').lower(),
            collection,
        )
        self.irods.collections.create(orphan_path2)
        out = io.StringIO()
        call_command('irodsorphans', stdout=out)
        expected = '{};{};{};0;0 bytes\n'.format(
            str(self.project.sodar_uuid),
            self.project.full_title,
            orphan_path2,
        )
        expected += '{};{};{};0;0 bytes\n'.format(
            str(self.project.sodar_uuid),
            self.project.full_title,
            orphan_path,
        )
        self.assertEqual(expected, out.getvalue())
