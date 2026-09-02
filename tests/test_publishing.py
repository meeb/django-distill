import tempfile
from hashlib import sha256

from django.test import TestCase

from django_distill.errors import DistillPublishError
from django_distill.publisher import (
    PublisherBackendBase,
    get_publisher,
    get_publisher_from_options,
)
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

    def test_remote_path_has_no_leading_slash(self):
        # Remote paths are used directly as object storage keys, where a
        # leading slash is a different (and wrong) key. 3.x produced bare
        # keys; publishing prefixed keys over a site published by 3.x would
        # upload a parallel copy and delete every existing object.
        with tempfile.TemporaryDirectory() as tmpdirname:
            nested = Path(tmpdirname) / "gigs"
            nested.mkdir()
            nested_file = nested / "index.html"
            nested_file.write_text("<html>test</html>")
            test_backend = TestBackend(tmpdirname, options=self.test_options)
            self.assertEqual(test_backend.remote_path(nested_file), "gigs/index.html")

    def test_generate_remote_url_with_path_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            nested = Path(tmpdirname) / "gigs"
            nested.mkdir()
            nested_file = nested / "index.html"
            nested_file.write_text("<html>test</html>")
            for public_url, expected in (
                (
                    "https://test.cdn.example",
                    "https://test.cdn.example/gigs/index.html",
                ),
                (
                    "https://test.cdn.example/",
                    "https://test.cdn.example/gigs/index.html",
                ),
                (
                    "https://test.cdn.example/site",
                    "https://test.cdn.example/site/gigs/index.html",
                ),
                (
                    "https://test.cdn.example/site/",
                    "https://test.cdn.example/site/gigs/index.html",
                ),
            ):
                options = dict(self.test_options, PUBLIC_URL=public_url)
                test_backend = TestBackend(tmpdirname, options=options)
                self.assertEqual(
                    test_backend.generate_remote_url(nested_file), expected
                )


class InMemoryBackend(PublisherBackendBase):
    """A publisher backend that keeps its "remote" files in a dict."""

    REQUIRED_OPTIONS = ("PUBLIC_URL",)

    def __init__(self, source_dir, options):
        super().__init__(source_dir, options)
        self.remote_store = {}
        self.uploaded = []
        self.deleted = []
        self.final_checks_called = False
        self.upload_error = None

    def account_username(self):
        return "test-user"

    def account_container(self):
        return "test-container"

    def authenticate(self):
        self._authenticated = True
        return True

    def get_remote_files(self):
        return set(self.remote_store)

    def delete_remote_file(self, remote_name):
        self.deleted.append(remote_name)
        self.remote_store.pop(remote_name, None)
        return True

    def compare_file(self, local_name, remote_name):
        return self.get_local_file_hash(local_name) == self.remote_store[remote_name]

    def upload_file(self, local_name, remote_name, verify=True):
        if self.upload_error:
            raise self.upload_error
        self.uploaded.append(remote_name)
        self.remote_store[remote_name] = self.get_local_file_hash(local_name)
        return True

    def create_remote_dir(self, remote_dir_name):
        return True

    def final_checks(self):
        self.final_checks_called = True


backend_class = InMemoryBackend


class StaticSitePublisherLoadingTestSuite(TestCase):
    def test_get_publisher_returns_the_backend_class(self):
        # get_publisher() must return the class named by the module's
        # backend_class attribute, not the module itself - the command calls
        # the result to construct a publisher.
        publisher = get_publisher("tests.test_publishing")
        self.assertIs(publisher, InMemoryBackend)
        self.assertTrue(callable(publisher))

    def test_get_publisher_without_backend_class(self):
        with self.assertRaises(DistillPublishError):
            get_publisher("django_distill.errors")

    def test_get_publisher_from_options(self):
        options = {"ENGINE": "tests.test_publishing"}
        self.assertIs(get_publisher_from_options(options), InMemoryBackend)

    def test_get_publisher_from_options_without_engine(self):
        with self.assertRaises(DistillPublishError):
            get_publisher_from_options({})


class StaticSitePublishTestSuite(TestCase):
    def setUp(self):
        self.options = {"PUBLIC_URL": "https://test.cdn.example/"}

    def _make_site(self, tmpdirname):
        (Path(tmpdirname) / "index.html").write_text("<html>index</html>")
        nested = Path(tmpdirname) / "gigs"
        nested.mkdir()
        (nested / "index.html").write_text("<html>gigs</html>")

    def test_publish_uploads_with_unprefixed_keys(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            self._make_site(tmpdirname)
            backend = InMemoryBackend(tmpdirname, self.options)
            backend.authenticate()
            backend.publish(verify=False)
            self.assertEqual(
                sorted(backend.uploaded), ["gigs/index.html", "index.html"]
            )
            self.assertFalse([k for k in backend.remote_store if k.startswith("/")])

    def test_publish_deletes_orphaned_remote_files(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            self._make_site(tmpdirname)
            backend = InMemoryBackend(tmpdirname, self.options)
            backend.authenticate()
            backend.remote_store["stale/removed.html"] = "whatever"
            backend.publish(verify=False)
            self.assertEqual(backend.deleted, ["stale/removed.html"])
            self.assertNotIn("stale/removed.html", backend.remote_store)

    def test_publish_leaves_unchanged_files_alone(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            self._make_site(tmpdirname)
            backend = InMemoryBackend(tmpdirname, self.options)
            backend.authenticate()
            backend.publish(verify=False)
            backend.uploaded.clear()
            backend.publish(verify=False)
            self.assertEqual(backend.uploaded, [])
            self.assertEqual(backend.deleted, [])

    def test_publish_ignoring_remote_content_skips_deletes(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            self._make_site(tmpdirname)
            backend = InMemoryBackend(tmpdirname, self.options)
            backend.authenticate()
            backend.remote_store["stale/removed.html"] = "whatever"
            backend.publish(verify=False, ignore_remote_content=True)
            self.assertEqual(backend.deleted, [])

    def test_publish_requires_authentication(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            self._make_site(tmpdirname)
            backend = InMemoryBackend(tmpdirname, self.options)
            with self.assertRaises(DistillPublishError):
                backend.publish(verify=False)

    def test_publish_propagates_upload_errors(self):
        # Errors raised in the upload workers must not be silently swallowed,
        # otherwise a completely failed publish reports success.
        with tempfile.TemporaryDirectory() as tmpdirname:
            self._make_site(tmpdirname)
            backend = InMemoryBackend(tmpdirname, self.options)
            backend.authenticate()
            backend.upload_error = DistillPublishError("upload failed")
            with self.assertRaises(DistillPublishError):
                backend.publish(verify=False)

    def test_publish_runs_final_checks(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            self._make_site(tmpdirname)
            backend = InMemoryBackend(tmpdirname, self.options)
            backend.authenticate()
            backend.publish(verify=False)
            self.assertTrue(backend.final_checks_called)
