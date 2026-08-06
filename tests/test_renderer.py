import tempfile

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.test import TransactionTestCase
from django.utils.translation import activate as activate_lang

from django_distill.errors import DistillError
from django_distill.renderer import DistillRenderer, render_uri, write_single_pattern
from django_distill.request import generate_uri, get_uri_values
from django_distill.urls import get_distilled_url_by_name, get_distilled_urls
from django_distill.utils import Path

test_urls = get_distilled_urls()
# A list of all the test urls that are not broken views. This is used for "loop all URLs" tests where
# having a view that on purpose throws an exception or raises a 404 is not useful.
test_urls_not_broken = [
    p for p in test_urls if not getattr(p.callback, "skip_render_all_tests", False)
]


class StaticSiteRendererTestSuite(TransactionTestCase):
    def setUp(self):
        # Create a few test flatpages
        site = django_apps.get_model("sites.Site")
        current_site = site.objects.get_current()
        page1 = FlatPage()
        page1.url = "/flat/page1.html"
        page1.title = "flatpage1"
        page1.content = "flatpage1"
        page1.template_name = "flatpage.html"
        page1.save()
        page1.sites.add(current_site)
        page2 = FlatPage()
        page2.url = "/flat/page2.html"
        page2.title = "flatpage2"
        page2.content = "flatpage2"
        page2.template_name = "flatpage.html"
        page2.save()
        page2.sites.add(current_site)

    def test_get_uri_values(self):
        test = ()
        check = get_uri_values(lambda: test, None)
        self.assertEqual(check, (None,))
        test = ("a",)
        check = get_uri_values(lambda: test, None)
        test = (("a",),)
        check = get_uri_values(lambda: test, None)
        self.assertEqual(check, test)
        test = []
        check = get_uri_values(lambda: test, None)
        self.assertEqual(check, (None,))
        test = ["a"]
        check = get_uri_values(lambda: test, None)
        self.assertEqual(check, test)
        test = [["a"]]
        check = get_uri_values(lambda: test, None)
        self.assertEqual(check, test)
        for invalid in ("a", 1, b"a", {"s"}, {"a": "a"}, object()):
            with self.assertRaises(DistillError):
                get_uri_values(lambda invalid: invalid, None)

    def test_re_path_no_param(self):
        u = get_distilled_url_by_name("re_path-no-param")
        self.assertEqual(u.name, "re_path-no-param")
        param_set = get_uri_values(u.distill_func, u.name)[0]
        uri = generate_uri(u.distill_namespace, u.name, param_set)
        self.assertEqual(uri, "/re_path/no-param")
        status, _headers, body = render_uri(uri, u.distill_status_codes)
        self.assertEqual(status, 200)
        self.assertEqual(body, b"test")

    def test_re_path_positional_param(self):
        u = get_distilled_url_by_name("re_path-positional-param")
        self.assertEqual(u.name, "re_path-positional-param")
        param_sets = get_uri_values(u.distill_func, u.name)
        for param_set in param_sets:
            param_set = (param_set,)
            first_value = param_set[0]
            uri = generate_uri(u.distill_namespace, u.name, param_set)
            self.assertEqual(uri, f"/re_path/positional-param/{first_value}")
            status, _headers, body = render_uri(uri, u.distill_status_codes)
            self.assertEqual(status, 200)
            self.assertEqual(body, b"test" + first_value.encode())

    def test_re_path_named_param(self):
        u = get_distilled_url_by_name("re_path-named-param")
        self.assertEqual(u.name, "re_path-named-param")
        param_set = get_uri_values(u.distill_func, u.name)[0]
        uri = generate_uri(u.distill_namespace, u.name, param_set)
        self.assertEqual(uri, "/re_path/named-override-filename/test")
        status, _headers, body = render_uri(uri, u.distill_status_codes)
        self.assertEqual(status, 200)
        self.assertEqual(body, b"testtest")

    def test_re_broken(self):
        u = get_distilled_url_by_name("re_path-broken")
        self.assertEqual(u.name, "re_path-broken")
        param_set = get_uri_values(u.distill_func, u.name)[0]
        uri = generate_uri(u.distill_namespace, u.name, param_set)
        self.assertEqual(uri, "/re_path/broken")
        with self.assertRaises(DistillError):
            status, _headers, _body = render_uri(uri, u.distill_status_codes)
            self.assertEqual(status, 500)

    def test_path_no_param(self):
        u = get_distilled_url_by_name("path-no-param")
        self.assertEqual(u.name, "path-no-param")
        param_set = get_uri_values(u.distill_func, u.name)[0]
        uri = generate_uri(u.distill_namespace, u.name, param_set)
        self.assertEqual(uri, "/path/no-param")
        status, _headers, body = render_uri(uri, u.distill_status_codes)
        self.assertEqual(status, 200)
        self.assertEqual(body, b"test")

    def test_path_positional_param(self):
        u = get_distilled_url_by_name("path-positional-param")
        self.assertEqual(u.name, "path-positional-param")
        param_sets = get_uri_values(u.distill_func, u.name)
        for param_set in param_sets:
            param_set = (param_set,)
            first_value = param_set[0]
            uri = generate_uri(u.distill_namespace, u.name, param_set)
            self.assertEqual(uri, f"/path/positional-param/{first_value}")
            status, _headers, body = render_uri(uri, u.distill_status_codes)
            self.assertEqual(status, 200)
            self.assertEqual(body, b"test" + first_value.encode())

    def test_path_named_param(self):
        u = get_distilled_url_by_name("path-named-param")
        self.assertEqual(u.name, "path-named-param")
        param_set = get_uri_values(u.distill_func, u.name)[0]
        uri = generate_uri(u.distill_namespace, u.name, param_set)
        self.assertEqual(uri, "/path/named-param/test")
        status, _headers, body = render_uri(uri, u.distill_status_codes)
        self.assertEqual(status, 200)
        self.assertEqual(body, b"testtest")

    def test_path_broken(self):
        u = get_distilled_url_by_name("path-broken")
        self.assertEqual(u.name, "path-broken")
        param_set = get_uri_values(u.distill_func, u.name)[0]
        uri = generate_uri(u.distill_namespace, u.name, param_set)
        self.assertEqual(uri, "/path/broken")
        with self.assertRaises(DistillError):
            status, _headers, _body = render_uri(uri, u.distill_status_codes)
            self.assertEqual(status, 500)

    def test_render_paths(self):
        expected_files = (
            ("path", "namespace1", "path", "sub-namespace", "sub-url-in-sub-namespace"),
            ("path", "namespace1", "sub-url-in-namespace"),
            ("path", "no-namespace", "sub-url-in-no-namespace"),
            ("en", "path", "i18n", "sub-url-with-i18n-prefix"),
            ("re_path", "no-param"),
            ("re_path", "no-func"),
            ("re_path", "positional-param", "12345"),
            ("re_path", "positional-param", "67890"),
            ("re_path", "x", "12345.html"),
            ("re_path", "x", "67890.html"),
            ("re_path", "named-override-filename", "test"),
            ("re_path", "x", "test.html"),
            ("re_path", "ignore-sessions"),
            ("re_path", "flatpage", "flat", "page1.html"),
            ("re_path", "flatpage", "flat", "page2.html"),
            ("path", "no-param"),
            ("path", "no-func"),
            ("path", "positional-param", "12345"),
            ("path", "positional-param", "67890"),
            ("path", "x", "12345.html"),
            ("path", "x", "67890.html"),
            ("path", "named-param", "test"),
            ("path", "x", "test.html"),
            ("path", "ignore-sessions"),
            ("path", "flatpage", "flat", "page1.html"),
            ("path", "flatpage", "flat", "page2.html"),
            ("path", "sitemap"),
            ("path", "kwargs"),
            ("path", "humanize"),
            ("path", "has-resolver-match"),
        )
        with tempfile.TemporaryDirectory() as tmpdirname:
            with DistillRenderer(test_urls_not_broken) as renderer:
                renderer.render_to_directory(tmpdirname)
            written_files = []
            tmpdirpath = Path(tmpdirname)
            for root, dirs, files in tmpdirpath.walk():
                for f in files:
                    written_files.append(root / f)
            for expected_file in expected_files:
                filepath = tmpdirpath / Path(*expected_file)
                self.assertIn(filepath, written_files)

    def test_sessions_are_ignored(self):
        u = get_distilled_url_by_name("path-ignore-sessions")
        self.assertEqual(u.name, "path-ignore-sessions")
        param_set = get_uri_values(u.distill_func, u.name)[0]
        uri = generate_uri(u.distill_namespace, u.name, param_set)
        self.assertEqual(uri, "/path/ignore-sessions")
        status, _headers, body = render_uri(uri, u.distill_status_codes)
        self.assertEqual(status, 200)
        self.assertEqual(body, b"test")

    def test_custom_status_codes(self):
        u = get_distilled_url_by_name("path-404")
        self.assertEqual(u.name, "path-404")
        param_set = get_uri_values(u.distill_func, u.name)[0]
        uri = generate_uri(u.distill_namespace, u.name, param_set)
        self.assertEqual(uri, "/path/404")
        status, _headers, body = render_uri(uri, u.distill_status_codes)
        self.assertEqual(status, 404)
        self.assertEqual(body, b"404")

    def test_contrib_flatpages(self):
        u = get_distilled_url_by_name("path-flatpage")
        self.assertEqual(u.name, "path-flatpage")
        param_set = get_uri_values(u.distill_func, u.name)
        for param in param_set:
            page_url = param["url"]
            uri = generate_uri(u.distill_namespace, u.name, param)
            self.assertEqual(uri, f"/path/flatpage{page_url}")
            status, _headers, body = render_uri(uri, u.distill_status_codes)
            flatpage = FlatPage.objects.get(url=page_url)
            expected = (
                f"<title>{flatpage.title}</title><body>{flatpage.content}</body>\n"
            )
            self.assertEqual(body, expected.encode())
            self.assertEqual(status, 200)

    def test_contrib_sitemaps(self):
        u = get_distilled_url_by_name("path-sitemap")
        self.assertEqual(u.name, "path-sitemap")
        param_set = get_uri_values(u.distill_func, u.name)[0]
        uri = generate_uri(u.distill_namespace, u.name, param_set)
        self.assertEqual(uri, "/path/sitemap")
        status, _headers, body = render_uri(uri, u.distill_status_codes)
        expected = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            b'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            b"<url><loc>https://example.com/path/sitemap</loc>"
            b"<changefreq>daily</changefreq>"
            b"<priority>0.5</priority></url>\n</urlset>\n"
        )
        self.assertEqual(body, expected)
        self.assertEqual(status, 200)

    def test_render_single_file(self):
        expected_files = (
            ("path", "positional-param", "12345"),
            ("path", "named-param", "test"),
        )
        with tempfile.TemporaryDirectory() as tmpdirname:
            write_single_pattern(tmpdirname, "path-positional-param", 12345)
            write_single_pattern(tmpdirname, "path-named-param", param="test")
            written_files = []
            tmpdirpath = Path(tmpdirname)
            for root, dirs, files in Path(tmpdirpath).walk():
                for f in files:
                    written_files.append(root / f)
            for expected_file in expected_files:
                filepath = tmpdirpath / Path(*expected_file)
                self.assertIn(filepath, written_files)

    def test_i18n(self):
        settings.STATICSITE_LANGUAGES = [
            "en",
            "fr",
            "de",
        ]
        expected = {}
        for lang_code in settings.STATICSITE_LANGUAGES:
            expected[lang_code] = f"/{lang_code}/path/i18n/sub-url-with-i18n-prefix"
        u = get_distilled_url_by_name("test-url-i18n", namespace="test_i18n")
        self.assertEqual(u.name, "test-url-i18n")
        for lang_code, path in expected.items():
            activate_lang(lang_code)
            param_set = get_uri_values(u.distill_func, u.name)[0]
            uri = generate_uri(u.distill_namespace, u.name, param_set)
            self.assertEqual(uri, path)
            _status, _headers, body = render_uri(uri, u.distill_status_codes)
            self.assertEqual(body, b"test")
        # Render the test URLs and confirm the expected language URI prefixes are present
        expected_files = (
            ("en", "path", "i18n", "sub-url-with-i18n-prefix"),
            ("fr", "path", "i18n", "sub-url-with-i18n-prefix"),
            ("de", "path", "i18n", "sub-url-with-i18n-prefix"),
        )
        with tempfile.TemporaryDirectory() as tmpdirname:
            for lang_code in settings.STATICSITE_LANGUAGES:
                write_single_pattern(
                    tmpdirname, "test_i18n:test-url-i18n", language_code=lang_code
                )
            written_files = []
            tmpdirpath = Path(tmpdirname)
            for root, dirs, files in tmpdirpath.walk():
                for f in files:
                    written_files.append(root / f)
            for expected_file in expected_files:
                filepath = tmpdirname / Path(*expected_file)
                self.assertIn(filepath, written_files)
        settings.STATICSITE_LANGUAGES = []

    def test_kwargs(self):
        u = get_distilled_url_by_name("test-kwargs")
        self.assertEqual(u.name, "test-kwargs")
        param_set = get_uri_values(u.distill_func, u.name)[0]
        uri = generate_uri(u.distill_namespace, u.name, param_set)
        self.assertEqual(uri, "/path/kwargs")
        status, _headers, body = render_uri(uri, u.distill_status_codes)
        self.assertEqual(status, 200)
        self.assertEqual(body, b"test")

    def test_humanize(self):
        u = get_distilled_url_by_name("test-humanize")
        self.assertEqual(u.name, "test-humanize")
        param_set = get_uri_values(u.distill_func, u.name)[0]
        uri = generate_uri(u.distill_namespace, u.name, param_set)
        self.assertEqual(uri, "/path/humanize")
        _status, _headers, body = render_uri(uri, u.distill_status_codes)
        expected = b"\n".join(
            [
                b"",
                b"<ul>",
                b"<li>test</li>",
                b"<li>one hour ago naturaltime: an hour ago</li>",
                b"<li>nineteen hours ago naturaltime: 19\xc2\xa0hours ago</li>",
                b"</ul>",
                b"",
            ]
        )
        self.assertEqual(body, expected)

    def test_request_has_resolver_match(self):
        u = get_distilled_url_by_name("test-has-resolver-match")
        self.assertEqual(u.name, "test-has-resolver-match")
        param_set = get_uri_values(u.distill_func, u.name)[0]
        uri = generate_uri(u.distill_namespace, u.name, param_set)
        self.assertEqual(uri, "/path/has-resolver-match")
        _status, _headers, body = render_uri(uri, u.distill_status_codes)
        self.assertEqual(body, b"test_request_has_resolver_match_view")

    def test_parallel_rendering(self):
        expected_files = (
            ("path", "namespace1", "path", "sub-namespace", "sub-url-in-sub-namespace"),
            ("path", "namespace1", "sub-url-in-namespace"),
            ("path", "no-namespace", "sub-url-in-no-namespace"),
            ("en", "path", "i18n", "sub-url-with-i18n-prefix"),
            ("re_path", "no-param"),
            ("re_path", "no-func"),
            ("re_path", "positional-param", "12345"),
            ("re_path", "positional-param", "67890"),
            ("re_path", "x", "12345.html"),
            ("re_path", "x", "67890.html"),
            ("re_path", "named-override-filename", "test"),
            ("re_path", "x", "test.html"),
            ("re_path", "ignore-sessions"),
            ("re_path", "flatpage", "flat", "page1.html"),
            ("re_path", "flatpage", "flat", "page2.html"),
            ("path", "no-param"),
            ("path", "no-func"),
            ("path", "positional-param", "12345"),
            ("path", "positional-param", "67890"),
            ("path", "x", "12345.html"),
            ("path", "x", "67890.html"),
            ("path", "named-param", "test"),
            ("path", "x", "test.html"),
            ("path", "ignore-sessions"),
            ("path", "flatpage", "flat", "page1.html"),
            ("path", "flatpage", "flat", "page2.html"),
            ("path", "sitemap"),
            ("path", "kwargs"),
            ("path", "humanize"),
            ("path", "has-resolver-match"),
        )
        with tempfile.TemporaryDirectory() as tmpdirname:
            with DistillRenderer(test_urls_not_broken, concurrency=8) as renderer:
                renderer.render_to_directory(tmpdirname)
            written_files = []
            tmpdirpath = Path(tmpdirname)
            for root, dirs, files in tmpdirpath.walk():
                for f in files:
                    written_files.append(root / f)
            for expected_file in expected_files:
                filepath = tmpdirpath / Path(*expected_file)
                self.assertIn(filepath, written_files)

    def test_generate_urls(self):
        expected_urls = (
            "/en/path/i18n/sub-url-with-i18n-prefix",
            "/path/flatpage/flat/page1.html",
            "/path/flatpage/flat/page2.html",
            "/path/has-resolver-match",
            "/path/humanize",
            "/path/ignore-sessions",
            "/path/kwargs",
            "/path/named-override-filename/test",
            "/path/named-param/test",
            "/path/namespace1/path/sub-namespace/sub-url-in-sub-namespace",
            "/path/namespace1/sub-url-in-namespace",
            "/path/no-func",
            "/path/no-namespace/sub-url-in-no-namespace",
            "/path/no-param",
            "/path/positional-override-filename/12345",
            "/path/positional-override-filename/67890",
            "/path/positional-param/12345",
            "/path/positional-param/67890",
            "/path/sitemap",
            "/re_path/flatpage/flat/page1.html",
            "/re_path/flatpage/flat/page2.html",
            "/re_path/ignore-sessions",
            "/re_path/named-override-filename/test",
            "/re_path/named-param/test",
            "/re_path/no-func",
            "/re_path/no-param",
            "/re_path/positional-override-filename/12345",
            "/re_path/positional-override-filename/67890",
            "/re_path/positional-param/12345",
            "/re_path/positional-param/67890",
        )
        generated_urls = []
        with DistillRenderer(test_urls_not_broken) as renderer:
            for generated_url in renderer.urls():
                generated_urls.append(str(generated_url))
        self.assertEqual(sorted(generated_urls), sorted(expected_urls))
