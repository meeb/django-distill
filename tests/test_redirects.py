import os
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import TestCase
from django.contrib.redirects.models import Redirect
from django_distill.renderer import render_static_redirect, render_redirects


def null(*args, **kwargs):
    pass


class DjangoDistillRedirectsTestSuite(TestCase):    

    def test_template(self):
        test_url = 'https://example.com/'
        test_template = render_static_redirect(test_url)
        expected_template = ('<!DOCTYPE html>\n'
                             '<html>\n'
                             '<head>\n'
                             '<meta charset="UTF-8">\n'
                             '<meta http-equiv="refresh" content="0;URL=https://example.com/" />\n'
                             '<title>Redirecting to https://example.com/</title>\n'
                             '<meta name="robots" content="noindex" />\n'
                             '</head>\n'
                             '<body>\n'
                             '<h1>Redirecting to <a href="https://example.com/">https://example.com/</a></h1>\n'
                             '<p>If you are not automatically redirected please click <a href="https://example.com/">this link</a></p>\n'
                             '</html>')
        self.assertEqual(test_template, expected_template.encode())

    def test_redirects(self):
        # Create some test redirects
        Redirect.objects.create(site_id=1, old_path='/redirect-from1/', new_path='/redirect-to1/')
        Redirect.objects.create(site_id=1, old_path='/redirect-from2/', new_path='/redirect-to2/')
        Redirect.objects.create(site_id=1, old_path='/redirect-from3/', new_path='/redirect-to3/')
        Redirect.objects.create(site_id=1, old_path='/redirect-from4/test.html', new_path='/redirect-to4/test.html')
        Redirect.objects.create(site_id=1, old_path='/redirect-from5/noslash', new_path='/redirect-to5/noslash')
        Redirect.objects.create(site_id=1, old_path='/redirect-from6/deep/redirect/path/', new_path='/redirect-to6/')
        # Render the redirect templates
        with TemporaryDirectory() as tempdir:
            render_redirects(tempdir, null)
            # Test the redirect templates exist
            for redirect in Redirect.objects.all():
                redirect_path = redirect.old_path.lstrip('/')
                if redirect_path.lower().endswith('.html'):
                    test_file_path = str(Path(tempdir) / redirect_path)
                else:
                    test_file_path = str(Path(tempdir) / redirect_path / 'index.html')
                self.assertTrue(os.path.exists(test_file_path))
                with open(test_file_path, 'rb') as f:
                    test_file_contents = f.read()
                    expected_file_contents = render_static_redirect(redirect.new_path)
                    self.assertEqual(test_file_contents, expected_file_contents)
