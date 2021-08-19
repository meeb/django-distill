import os
import sys
import tempfile
import warnings
from django.test import TestCase
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.apps import apps as django_apps
from django_distill.distill import urls_to_distill
from django_distill.renderer import DistillRender, render_to_dir
from django_distill.errors import DistillError


class DjangoDistillRendererTestSuite(TestCase):

    def setUp(self):
        output_dir = None
        self.renderer = DistillRender(output_dir, urls_to_distill)
        # Create a few test flatpages
        Site = django_apps.get_model('sites.Site')
        current_site = Site.objects.get_current()
        page1 = FlatPage()
        page1.url = '/flat/page1.html'
        page1.title = 'flatpage1'
        page1.content = 'flatpage1'
        page1.template_name = 'flatpage.html'
        page1.save()
        page1.sites.add(current_site)
        page2 = FlatPage()
        page2.url = '/flat/page2.html'
        page2.title = 'flatpage2'
        page2.content = 'flatpage2'
        page2.template_name = 'flatpage.html'
        page2.save()
        page2.sites.add(current_site)

    def _get_view(self, name):
        for u in urls_to_distill:
            if u[4] == name:
                return u
        return False

    def _skip(self, what):
        sys.stdout.write('Missing {}, skipping test... '.format(what))
        sys.stdout.flush()

    def test_is_str(self):
        self.assertTrue(self.renderer._is_str('a'))
        self.assertFalse(self.renderer._is_str(None))
        self.assertFalse(self.renderer._is_str(1))
        self.assertFalse(self.renderer._is_str([]))
        self.assertFalse(self.renderer._is_str(()))
        self.assertFalse(self.renderer._is_str({}))
        self.assertFalse(self.renderer._is_str({'a':'a'}))
        self.assertFalse(self.renderer._is_str(object()))

    def test_get_uri_values(self):
        test = ()
        check = self.renderer.get_uri_values(lambda: test, None)
        self.assertEqual(check, (None,))
        test = ('a',)
        check = self.renderer.get_uri_values(lambda: test, None)
        self.assertEqual(check, test)
        test = (('a',),)
        check = self.renderer.get_uri_values(lambda: test, None)
        self.assertEqual(check, test)
        test = []
        check = self.renderer.get_uri_values(lambda: test, None)
        self.assertEqual(check, (None,))
        test = ['a']
        check = self.renderer.get_uri_values(lambda: test, None)
        self.assertEqual(check, test)
        test = [['a']]
        check = self.renderer.get_uri_values(lambda: test, None)
        self.assertEqual(check, test)
        for invalid in ('a', 1, b'a', {'s'}, {'a':'a'}, object()):
            with self.assertRaises(DistillError):
                self.renderer.get_uri_values(lambda: invalid, None)

    def test_url_no_param(self):
        view = self._get_view('url-no-param')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        if not param_set:
            param_set = ()
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/url/')
        render = self.renderer.render_view(uri, status_codes, param_set, args)
        self.assertEqual(render.content, b'test')

    def test_url_positional_param(self):
        view = self._get_view('url-positional-param')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/url/12345')
        render = self.renderer.render_view(uri, status_codes, param_set, args)
        self.assertEqual(render.content, b'test12345')

    def test_url_named_param(self):
        view = self._get_view('url-named-param')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/url/test')
        render = self.renderer.render_view(uri, status_codes, param_set, args)
        self.assertEqual(render.content, b'testtest')

    def test_re_path_no_param(self):
        if not settings.HAS_RE_PATH:
            self._skip('django.urls.re_path')
            return
        view = self._get_view('re_path-no-param')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        if not param_set:
            param_set = ()
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/re_path/')
        render = self.renderer.render_view(uri, status_codes, param_set, args)
        self.assertEqual(render.content, b'test')

    def test_re_path_positional_param(self):
        if not settings.HAS_RE_PATH:
            self._skip('django.urls.re_path')
            return
        view = self._get_view('re_path-positional-param')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/re_path/12345')
        render = self.renderer.render_view(uri, status_codes, param_set, args)
        self.assertEqual(render.content, b'test12345')

    def test_re_path_named_param(self):
        if not settings.HAS_RE_PATH:
            self._skip('django.urls.re_path')
            return
        view = self._get_view('re_path-named-param')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/re_path/test')
        render = self.renderer.render_view(uri, status_codes, param_set, args)
        self.assertEqual(render.content, b'testtest')

    def test_re_broken(self):
        if not settings.HAS_RE_PATH:
            self._skip('django.urls.re_path')
            return
        view = self._get_view('re_path-broken')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        if not param_set:
            param_set = ()
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/re_path/broken')
        with self.assertRaises(DistillError):
            self.renderer.render_view(uri, status_codes, param_set, args)

    def test_path_no_param(self):
        if not settings.HAS_PATH:
            self._skip('django.urls.path')
            return
        view = self._get_view('path-no-param')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        if not param_set:
            param_set = ()
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/path/')
        render = self.renderer.render_view(uri, status_codes, param_set, args)
        self.assertEqual(render.content, b'test')

    def test_path_positional_param(self):
        if not settings.HAS_PATH:
            self._skip('django.urls.path')
            return
        view = self._get_view('path-positional-param')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/path/12345')
        render = self.renderer.render_view(uri, status_codes, param_set, args)
        self.assertEqual(render.content, b'test12345')

    def test_path_named_param(self):
        if not settings.HAS_PATH:
            self._skip('django.urls.path')
            return
        view = self._get_view('path-named-param')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/path/test')
        render = self.renderer.render_view(uri, status_codes, param_set, args)
        self.assertEqual(render.content, b'testtest')

    def test_path_broken(self):
        if not settings.HAS_PATH:
            self._skip('django.urls.path')
            return
        view = self._get_view('path-broken')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        if not param_set:
            param_set = ()
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/path/broken')
        with self.assertRaises(DistillError):
            self.renderer.render_view(uri, status_codes, param_set, args)

    def test_render_paths(self):
        def _blackhole(_):
            pass
        expected_files = (
            ('test',),
            ('url', '12345'),
            ('url', 'test'),
            ('re_path', '12345'),
            ('re_path', 'test'),
        )
        with tempfile.TemporaryDirectory() as tmpdirname:
            with self.assertRaises(DistillError):
                render_to_dir(tmpdirname, urls_to_distill, _blackhole)
            written_files = []
            for (root, dirs, files) in os.walk(tmpdirname):
                for f in files:
                    filepath = os.path.join(root, f)
                    written_files.append(filepath)
            for expected_file in expected_files:
                filepath = os.path.join(tmpdirname, *expected_file)
                self.assertIn(filepath, written_files)

    def test_sessions_are_ignored(self):
        if settings.HAS_PATH:
            view = self._get_view('path-ignore-sessions')
            assert view
            view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
            param_set = self.renderer.get_uri_values(view_func, view_name)[0]
            if not param_set:
                param_set = ()
            uri = self.renderer.generate_uri(view_url, view_name, param_set)
            self.assertEqual(uri, '/path/ignore-sessions')
            with warnings.catch_warnings(record=True) as w:
                render = self.renderer.render_view(uri, status_codes, param_set, args)
                self.assertEqual(len(w), 1)
                caught_warning = w[0]
                self.assertEqual(caught_warning.category, RuntimeWarning)
            self.assertEqual(render.content, b'test')
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        if settings.HAS_RE_PATH:
            view = self._get_view('re_path-ignore-sessions')
            assert view
            view_url, iew_func, file_name, status_codes, view_name, args, kwargs = view
            param_set = self.renderer.get_uri_values(view_func, view_name)[0]
            if not param_set:
                param_set = ()
            uri = self.renderer.generate_uri(view_url, view_name, param_set)
            self.assertEqual(uri, '/re_path/ignore-sessions')
            with warnings.catch_warnings(record=True) as w:
                render = self.renderer.render_view(uri, status_codes, param_set, args)
                self.assertEqual(len(w), 1)
                caught_warning = w[0]
                self.assertEqual(caught_warning.category, RuntimeWarning)
            self.assertEqual(render.content, b'test')

    def test_custom_status_codes(self):
        if settings.HAS_PATH:
            view = self._get_view('path-404')
            assert view
            view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
            param_set = self.renderer.get_uri_values(view_func, view_name)[0]
            if not param_set:
                param_set = ()
            uri = self.renderer.generate_uri(view_url, view_name, param_set)
            self.assertEqual(uri, '/path/404')
            render = self.renderer.render_view(uri, status_codes, param_set, args)
            self.assertEqual(render.content, b'404')
            self.assertEqual(render.status_code, 404)
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        if settings.HAS_RE_PATH:
            view = self._get_view('re_path-404')
            assert view
            view_url, iew_func, file_name, status_codes, view_name, args, kwargs = view
            param_set = self.renderer.get_uri_values(view_func, view_name)[0]
            if not param_set:
                param_set = ()
            uri = self.renderer.generate_uri(view_url, view_name, param_set)
            self.assertEqual(uri, '/re_path/404')
            render = self.renderer.render_view(uri, status_codes, param_set, args)
            self.assertEqual(render.content, b'404')
            self.assertEqual(render.status_code, 404)

    def test_flatpages(self):
        if settings.HAS_PATH:
            view = self._get_view('path-flatpage')
            assert view
            view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
            param_set = self.renderer.get_uri_values(view_func, view_name)
            for param in param_set:
                page_url = param['url']
                uri = self.renderer.generate_uri(view_url, view_name, param)
                self.assertEqual(uri, f'/path/flatpage{page_url}')
                render = self.renderer.render_view(uri, status_codes, param, args)
                flatpage = FlatPage.objects.get(url=page_url)
                expected = f'<title>{flatpage.title}</title><body>{flatpage.content}</body>\n'
                self.assertEqual(render.content, expected.encode())
                self.assertEqual(render.status_code, 200)
        if settings.HAS_RE_PATH:
            view = self._get_view('re_path-flatpage')
            assert view
            view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
            param_set = self.renderer.get_uri_values(view_func, view_name)
            for param in param_set:
                page_url = param['url']
                uri = self.renderer.generate_uri(view_url, view_name, param)
                self.assertEqual(uri, f'/re_path/flatpage{page_url}')
                render = self.renderer.render_view(uri, status_codes, param, args)
                flatpage = FlatPage.objects.get(url=page_url)
                expected = f'<title>{flatpage.title}</title><body>{flatpage.content}</body>\n'
                self.assertEqual(render.content, expected.encode())
                self.assertEqual(render.status_code, 200)
