import os
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import TestCase
from django.conf import settings
import django_distill
from django_distill.renderer import copy_static_and_media_files


def null(*args, **kwargs):
    pass


class DjangoDistillStaticFilesTestSuite(TestCase):

    def test_copying_static_files(self):
        with TemporaryDirectory() as tempdir:
            copy_static_and_media_files(tempdir, null)
            test_media_file_path = str(Path(tempdir) / 'media' / 'media-test.txt')
            self.assertTrue(os.path.exists(test_media_file_path))
            test_static_file_path = str(Path(tempdir) / 'static' / 'static-test.txt')
            self.assertTrue(os.path.exists(test_static_file_path))
