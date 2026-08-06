import os
from tempfile import TemporaryDirectory

from django.conf import settings
from django.test import TestCase

from django_distill.static import copy_static_and_media_files
from django_distill.utils import Path


class StaticSiteStaticTestSuite(TestCase):
    def test_copying_static_and_media_files(self):
        # Test default behavior
        with TemporaryDirectory() as tempdir:
            tempdir = Path(tempdir)
            copy_static_and_media_files(tempdir)
            test_media_file_path = tempdir / "media" / "media-test.txt"
            self.assertTrue(test_media_file_path.is_file())
            test_static_file_path = tempdir / "static" / "static-test.txt"
            self.assertTrue(test_static_file_path.is_file())

    def test_skipping_admin_dirs(self):
        settings.DISTILL_SKIP_ADMIN_DIRS = False
        with TemporaryDirectory() as tempdir:
            tempdir = Path(tempdir)
            copy_static_and_media_files(tempdir)
            test_media_file_path = tempdir / "media" / "media-test.txt"
            self.assertTrue(test_media_file_path.is_file())
            test_static_file_path = tempdir / "static" / "static-test.txt"
            self.assertTrue(test_static_file_path.is_file())
            test_admin_file_path = tempdir / "static" / "admin" / "admin-test.txt"
            self.assertTrue(test_admin_file_path.is_file())
            test_appdir_file_path = tempdir / "static" / "appdir" / "appdir-test.txt"
            self.assertTrue(test_appdir_file_path.is_file())

    def test_skipping_staticfiles_dirs(self):
        settings.DISTILL_SKIP_STATICFILES_DIRS = ["appdir"]
        with TemporaryDirectory() as tempdir:
            copy_static_and_media_files(tempdir)
            test_appdir_file_path = str(
                Path(tempdir) / "static" / "appdir" / "appdir-test.txt"
            )
            self.assertFalse(os.path.exists(test_appdir_file_path))
