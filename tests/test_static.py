import os
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import TestCase
from django.conf import settings
from django_distill.renderer import copy_static_and_media_files


def null(*args, **kwargs):
    pass


class DjangoDistillStaticFilesTestSuite(TestCase):

    def test_copying_static_files(self):
        # Test default behavior
        with TemporaryDirectory() as tempdir:
            copy_static_and_media_files(tempdir, null)
            test_media_file_path = str(Path(tempdir) / 'media' / 'media-test.txt')
            self.assertTrue(os.path.exists(test_media_file_path))
            test_static_file_path = str(Path(tempdir) / 'static' / 'static-test.txt')
            self.assertTrue(os.path.exists(test_static_file_path))
        # Test admin dir is copied with SKIP_ADMIN_DIRS set to False
        settings.DISTILL_SKIP_ADMIN_DIRS = False
        with TemporaryDirectory() as tempdir:
            copy_static_and_media_files(tempdir, null)
            test_media_file_path = str(Path(tempdir) / 'media' / 'media-test.txt')
            self.assertTrue(os.path.exists(test_media_file_path))
            test_static_file_path = str(Path(tempdir) / 'static' / 'static-test.txt')
            self.assertTrue(os.path.exists(test_static_file_path))
            test_admin_file_path = str(Path(tempdir) / 'static' / 'admin' / 'admin-test.txt')
            self.assertTrue(os.path.exists(test_admin_file_path))
            test_appdir_file_path = str(Path(tempdir) / 'static' / 'appdir' / 'appdir-test.txt')
            self.assertTrue(os.path.exists(test_appdir_file_path))
        # Test static app dirs are skipped with DISTILL_SKIP_STATICFILES_DIRS populated
        settings.DISTILL_SKIP_STATICFILES_DIRS = ['appdir']
        with TemporaryDirectory() as tempdir:
            copy_static_and_media_files(tempdir, null)
            test_appdir_file_path = str(Path(tempdir) / 'static' / 'appdir' / 'appdir-test.txt')
            self.assertFalse(os.path.exists(test_appdir_file_path))
