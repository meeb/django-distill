import tempfile
from hashlib import sha256

from django.test import TestCase

from django_distill.errors import DistillPublishError
from django_distill.publisher import PublisherBackendBase
from django_distill.utils import Path


class TestBackend(PublisherBackendBase):
    REQUIRED_OPTIONS = ("TEST_OPTION_1", "TEST_OPTION_2", "TEST_OPTION_3")


class StaticSitePublishingTestSuite(TestCase):
    def setUp(self):
        self.test_options = {
            "PUBLIC_URL": "https://test.cdn.example/",
            "TEST_OPTION_1": "test1",
            "TEST_OPTION_2": "test2",
            "TEST_OPTION_3": "test3",
        }

    def test_backend_dir(self):
        TestBackend("/tmp", options=self.test_options)
        TestBackend(Path("/tmp"), options=self.test_options)
        with self.assertRaises(DistillPublishError):
            TestBackend(123, options=self.test_options)
        with self.assertRaises(DistillPublishError):
            TestBackend(Path("/tmp/does/not/exist"), options=self.test_options)

    def test_validate_options(self):
        TestBackend("/tmp", options=self.test_options)
        with self.assertRaises(DistillPublishError):
            # Missing a required option
            TestBackend(
                "/tmp",
                options={
                    "PUBLIC_URL": "https://test.cdn.example/",
                    "TEST_OPTION_1": "test1",
                    "TEST_OPTION_2": "test2",
                },
            )
        with self.assertRaises(DistillPublishError):
            # No options
            TestBackend("/tmp", options={})

    def test_local_file_indexing(self):
        with (
            tempfile.TemporaryDirectory() as tmpdirname,
            tempfile.TemporaryDirectory(dir=tmpdirname) as tmpsubdirname,
            tempfile.NamedTemporaryFile(dir=tmpsubdirname) as tmpfilename,
        ):
            test_backend = TestBackend(tmpdirname, options=self.test_options)
            test_backend.index_local_files()
            self.assertEqual(test_backend.get_local_dirs(), {Path(tmpsubdirname)})
            self.assertEqual(test_backend.get_local_files(), {Path(tmpfilename.name)})

    def test_get_local_file_hash(self):
        with (
            tempfile.TemporaryDirectory() as tmpdirname,
            tempfile.NamedTemporaryFile(dir=tmpdirname) as tmpfilename,
        ):
            test_backend = TestBackend(tmpdirname, options=self.test_options)
            tmpfilename.write(b"test")
            tmpfilename.seek(0)
            local_md5_hash = test_backend.get_local_file_hash(tmpfilename.name)
            self.assertEqual(local_md5_hash, "098f6bcd4621d373cade4e832627b4f6")
            local_sha256_hash = test_backend.get_local_file_hash(
                tmpfilename.name, digest_func=sha256
            )
            self.assertEqual(
                local_sha256_hash,
                "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
            )

    def test_file_exists(self):
        with (
            tempfile.TemporaryDirectory() as tmpdirname,
            tempfile.NamedTemporaryFile(dir=tmpdirname) as tmpfilename,
        ):
            test_backend = TestBackend(tmpdirname, options=self.test_options)
            self.assertTrue(test_backend.file_exists(tmpfilename.name))
            self.assertFalse(test_backend.file_exists(f"{tmpfilename.name}.test"))

    def test_detect_local_file_mimetype(self):
        with (
            tempfile.TemporaryDirectory() as tmpdirname,
            tempfile.NamedTemporaryFile(dir=tmpdirname, suffix=".txt") as tmpfilename,
        ):
            tmpfilename.write(b"test")
            tmpfilename.seek(0)
            test_backend = TestBackend(tmpdirname, options=self.test_options)
            self.assertEqual(
                test_backend.detect_local_file_mimetype(tmpfilename.name),
                "text/plain",
            )

    def test_generate_remote_url(self):
        with (
            tempfile.TemporaryDirectory() as tmpdirname,
            tempfile.NamedTemporaryFile(dir=tmpdirname, suffix=".html") as tmpfilename,
        ):
            tmpfilename.write(b"<html>test</html>")
            tmpfilename.seek(0)
            tmpfilepath = Path(tmpfilename.name)
            test_backend = TestBackend(tmpdirname, options=self.test_options)
            self.assertEqual(
                test_backend.generate_remote_url(Path(tmpfilename.name)),
                f"{self.test_options['PUBLIC_URL']}{tmpfilepath.name}",
            )
