from django.test import TestCase
from django.conf import settings
import django_distill


class DjangoDistillInterfaceTestSuite(TestCase):

    def test_import(self):
        assert hasattr(django_distill, 'distill_url')
        assert callable(django_distill.distill_url)
        if settings.HAS_RE_PATH:
            assert hasattr(django_distill, 'distill_re_path')
            assert callable(django_distill.distill_re_path)
        if settings.HAS_PATH:
            assert hasattr(django_distill, 'distill_path')
            assert callable(django_distill.distill_path)
