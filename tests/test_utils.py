import os
from pathlib import Path

from django.test import TestCase, override_settings
from django.urls import URLPattern, include, path

from django_distill.utils import (
    NamedTestFile,
    get_header,
    get_langs,
    iter_url_patterns,
    set_func_attr,
)


class UtilsTestCase(TestCase):
    def test_set_func_attr(self):
        def my_func():
            pass

        decorated = set_func_attr("test_attr", "test_value")(my_func)
        self.assertEqual(decorated.test_attr, "test_value")
        self.assertEqual(my_func.test_attr, "test_value")

    def test_get_header(self):
        headers = [
            ("Content-Type", "text/html"),
            ("X-Test", "Value1"),
            ("x-test", "Value2"),
        ]
        self.assertEqual(get_header(headers, "Content-Type"), "text/html")
        self.assertEqual(get_header(headers, "content-type"), "text/html")
        self.assertEqual(get_header(headers, "X-Test"), "Value1")
        self.assertEqual(get_header(headers, "Non-Existent"), None)

    @override_settings(
        LANGUAGE_CODE="fr",
        LANGUAGES=[("fr", "French"), ("de", "German")],
        DISTILL_LANGUAGES=["it"],
    )
    def test_get_langs(self):
        langs = get_langs()
        # fr (LANGUAGE_CODE), de (from LANGUAGES), it (from DISTILL_LANGUAGES)
        self.assertIn("fr", langs)
        self.assertIn("de", langs)
        self.assertIn("it", langs)
        self.assertEqual(langs, sorted(["fr", "de", "it"]))

    @override_settings(LANGUAGE_CODE="en")
    def test_get_langs_default(self):
        # By default LANGUAGES is global_settings.LANGUAGES
        # get_langs should at least include LANGUAGE_CODE if it's not in DISTILL_LANGUAGES
        langs = get_langs()
        self.assertIn("en", langs)

    def test_named_test_file(self):
        with NamedTestFile() as ntf:
            self.assertTrue(os.path.exists(ntf.name))
            self.assertEqual(str(ntf), ntf.name)
            self.assertEqual(os.fspath(ntf), ntf.name)
            self.assertIsInstance(ntf.path, Path)
            self.assertEqual(ntf.path, Path(ntf.name))
            with open(ntf.name, "rb") as f:
                content = f.read()
                self.assertEqual(len(content), 32)  # hexlify(os.urandom(16))
            name = ntf.name
        self.assertFalse(os.path.exists(name))

    def test_named_test_file_manual_unlink(self):
        ntf = NamedTestFile()
        name = ntf.name
        self.assertTrue(os.path.exists(name))
        ntf.unlink()
        self.assertFalse(os.path.exists(name))

    def test_iter_url_patterns(self):
        def dummy_view(request):
            pass

        patterns = [
            path("a/", dummy_view, name="a"),
            path(
                "b/",
                include(
                    (
                        [
                            path("c/", dummy_view, name="c"),
                        ],
                        "ns1",
                    )
                ),
            ),
        ]

        # iter_url_patterns yields (URLPattern, namespace, depth)
        # Note: iter_url_patterns in utils.py treats depth 0 specially for namespace
        results = list(iter_url_patterns(patterns))

        # results[0] -> (path('a/'), None, 1)
        # results[1] -> (path('c/'), 'ns1', 1)

        self.assertEqual(len(results), 2)

        p1, ns1, d1 = results[0]
        self.assertIsInstance(p1, URLPattern)
        self.assertEqual(ns1, None)
        self.assertEqual(d1, 1)

        p2, ns2, d2 = results[1]
        self.assertIsInstance(p2, URLPattern)
        self.assertEqual(ns2, "ns1")
        self.assertEqual(d2, 1)

    def test_iter_url_patterns_nested(self):
        def dummy_view(request):
            pass

        patterns = [
            path(
                "sub/",
                include(
                    (
                        [
                            path("leaf/", dummy_view, name="leaf"),
                        ],
                        "subns",
                    ),
                    namespace="outerns",
                ),
            ),
        ]

        results = list(iter_url_patterns(patterns))
        self.assertEqual(len(results), 1)
        p, ns, d = results[0]
        # When URLResolver has namespace, it appends to parent namespace.
        # Here: depth 0 -> pattern is URLResolver. pattern.namespace is 'outerns'
        # call iter_url_patterns(pattern.url_patterns, 'outerns', 1)
        # depth 1 -> pattern is URLPattern. yields (pattern, 'outerns', 1)
        self.assertIsInstance(p, URLPattern)
        self.assertEqual(ns, "outerns")
        self.assertEqual(d, 1)
