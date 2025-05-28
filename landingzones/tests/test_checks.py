"""Tests for Django checks in the landingzones app"""

from django.conf import settings
from django.test import override_settings

from test_plus.test import TestCase

import landingzones.checks as checks
from landingzones.apps import LandingzonesConfig


# Local constants
AC = [LandingzonesConfig]


class TestLandingzonesChecks(TestCase):
    """Tests for landingzones checks"""

    def test_check_validate_limit(self):
        """Test check_validate_limit() with default settings"""
        self.assertEqual(settings.LANDINGZONES_ZONE_VALIDATE_LIMIT, 4)
        self.assertEqual(checks.check_validate_limit(AC), [])

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=0)
    def test_check_validate_limit_zero_value(self):
        """Test check_validate_limit() with value set to 0"""
        self.assertEqual(checks.check_validate_limit(AC), [checks.W001])
