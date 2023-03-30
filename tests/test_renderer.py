import os
import sys
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.apps import apps as django_apps
from django.utils import timezone
from django.utils.translation import activate as activate_lang
from django_distill.distill import urls_to_distill
from django_distill.renderer import DistillRender, render_to_dir, render_single_file, get_renderer
from django_distill.errors import DistillError

class CustomRender(DistillRender):
    pass


class DjangoDistillRendererTestSuite(TestCase):

    def setUp(self):
        self.renderer = DistillRender(urls_to_distill)
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
        param_sets = self.renderer.get_uri_values(view_func, view_name)
        for param_set in param_sets:
            param_set = (param_set,)
            first_value = param_set[0]
            uri = self.renderer.generate_uri(view_url, view_name, param_set)
            self.assertEqual(uri, f'/re_path/{first_value}')
            render = self.renderer.render_view(uri, status_codes, param_set, args)
            self.assertEqual(render.content, b'test' + first_value.encode())

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
        param_sets = self.renderer.get_uri_values(view_func, view_name)
        for param_set in param_sets:
            param_set = (param_set,)
            first_value = param_set[0]
            uri = self.renderer.generate_uri(view_url, view_name, param_set)
            self.assertEqual(uri, f'/path/{first_value}')
            render = self.renderer.render_view(uri, status_codes, param_set, args)
            self.assertEqual(render.content, b'test' + first_value.encode())

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
            ('re_path', '12345'),
            ('re_path', 'test'),
            ('re_path', 'x', '12345.html'),
            ('re_path', 'x', 'test.html'),
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

    @patch.object(CustomRender, "render_view", side_effect=CustomRender.render_view, autospec=True)
    @override_settings(DISTILL_RENDERER="tests.test_renderer.CustomRender")
    def test_render_paths_custom_renderer(self, render_view_spy):
        def _blackhole(_):
            pass
        expected_files = (
            ('test',),
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
        self.assertEqual(render_view_spy.call_count, 13)

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
            render = self.renderer.render_view(uri, status_codes, param_set, args)
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
            render = self.renderer.render_view(uri, status_codes, param_set, args)
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

    def test_contrib_flatpages(self):
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

    def test_contrib_sitemaps(self):
        view = self._get_view('path-sitemap')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = ()
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/path/test-sitemap')
        render = self.renderer.render_view(uri, status_codes, param_set, args)
        expected_content = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            b'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            b'<url><loc>http://example.com/path/test-sitemap</loc>'
            b'<changefreq>daily</changefreq>'
            b'<priority>0.5</priority></url>\n</urlset>\n'
        )
        self.assertEqual(render.content, expected_content)
        self.assertEqual(render.status_code, 200)

    def test_render_single_file(self):
        expected_files = (
            ('path', '12345'),
            ('path', 'test'),
        )
        with tempfile.TemporaryDirectory() as tmpdirname:
            render_single_file(tmpdirname, 'path-positional-param', 12345)
            render_single_file(tmpdirname, 'path-named-param', param='test')
            written_files = []
            for (root, dirs, files) in os.walk(tmpdirname):
                for f in files:
                    filepath = os.path.join(root, f)
                    written_files.append(filepath)
            for expected_file in expected_files:
                filepath = os.path.join(tmpdirname, *expected_file)
                self.assertIn(filepath, written_files)

    def test_i18n(self):
        if not settings.USE_I18N:
            self._skip('settings.USE_I18N')
            return
        expected = {}
        for lang_code, lang_name in settings.LANGUAGES:
            expected[lang_code] = f'/{lang_code}/path/i18n/sub-url-with-i18n-prefix'
        view = self._get_view('test-url-i18n')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        if not param_set:
            param_set = ()
        for lang_code, path in expected.items():
            activate_lang(lang_code)
            uri = self.renderer.generate_uri(view_url, view_name, param_set)
            self.assertEqual(uri, path)
            render = self.renderer.render_view(uri, status_codes, param_set, args)
            self.assertEqual(render.content, b'test')

    def test_kwargs(self):
        if not settings.HAS_PATH:
            self._skip('django.urls.path')
            return
        view = self._get_view('test-kwargs')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        if not param_set:
            param_set = ()
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/path/kwargs')
        render = self.renderer.render_view(uri, status_codes, param_set, args, kwargs)
        self.assertEqual(render.content, b'test')

    def test_humanize(self):
        if not settings.HAS_PATH:
            self._skip('django.urls.path')
            return
        view = self._get_view('test-humanize')
        assert view
        view_url, view_func, file_name, status_codes, view_name, args, kwargs = view
        param_set = self.renderer.get_uri_values(view_func, view_name)[0]
        if not param_set:
            param_set = ()
        uri = self.renderer.generate_uri(view_url, view_name, param_set)
        self.assertEqual(uri, '/path/humanize')
        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)
        nineteen_hours_ago = now - timedelta(hours=19)
        render = self.renderer.render_view(uri, status_codes, param_set, args, kwargs)
        content = render.content
        expected = b'\n'.join([
            b'',
            b'<ul>',
            b'<li>test</li>',
            b'<li>one hour ago naturaltime: an hour ago</li>',
            b'<li>nineteen hours ago naturaltime: 19\xc2\xa0hours ago</li>',
            b'</ul>',
            b'',
        ])
        self.assertEqual(render.content, expected)
