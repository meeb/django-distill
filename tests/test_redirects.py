import os
from tempfile import TemporaryDirectory

from django.apps import apps as django_apps
from django.contrib.redirects.models import Redirect
from django.test import TestCase

from django_distill.renderer import render_redirects, render_static_redirect
from django_distill.utils import Path


class StaticSiteRedirectsTestSuite(TestCase):
    def setUp(self):
        # Create some test redirects
        site = django_apps.get_model("sites.Site")
        current_site = site.objects.get_current()
        site_id = current_site.id
        Redirect.objects.create(
            site_id=site_id, old_path="/redirect-from1/", new_path="/redirect-to1/"
        )
        Redirect.objects.create(
            site_id=site_id, old_path="/redirect-from2/", new_path="/redirect-to2/"
        )
        Redirect.objects.create(
            site_id=site_id, old_path="/redirect-from3/", new_path="/redirect-to3/"
        )
        Redirect.objects.create(
            site_id=site_id,
            old_path="/redirect-from4/test.html",
            new_path="/redirect-to4/test.html",
        )
        Redirect.objects.create(
            site_id=site_id,
            old_path="/redirect-from5/noslash",
            new_path="/redirect-to5/noslash",
        )
        Redirect.objects.create(
            site_id=site_id,
            old_path="/redirect-from6/deep/redirect/path/",
            new_path="/redirect-to6/",
        )

    def test_template(self):
        test_url = "https://example.com/"
        test_template = render_static_redirect(test_url)
        expected_template = (
            "<!DOCTYPE html>\n"
            "<html>\n"
            "<head>\n"
            '<meta charset="UTF-8">\n'
            '<meta http-equiv="refresh" content="0;URL=https://example.com/" />\n'
            "<title>Redirecting to https://example.com/</title>\n"
            '<meta name="robots" content="noindex" />\n'
            "</head>\n"
            "<body>\n"
            '<h1>Redirecting to <a href="https://example.com/">https://example.com/</a></h1>\n'
            '<p>If you are not automatically redirected please click <a href="https://example.com/">this link</a></p>\n'
            "</html>"
        )
        self.assertEqual(test_template, expected_template.encode())

    def test_redirects(self):
        with TemporaryDirectory() as tempdir:
            render_redirects(tempdir)
            # Test the redirect templates exist
            for redirect in Redirect.objects.all():
                redirect_path = redirect.old_path.lstrip("/")
                if redirect_path.lower().endswith(".html"):
                    test_file_path = str(Path(tempdir) / redirect_path)
                else:
                    test_file_path = str(Path(tempdir) / redirect_path / "index.html")
                self.assertTrue(os.path.exists(test_file_path))
                with open(test_file_path, "rb") as f:
                    test_file_contents = f.read()
                    expected_file_contents = render_static_redirect(redirect.new_path)
                    self.assertEqual(test_file_contents, expected_file_contents)
