# -*- coding: utf-8 -*-


from django.test import TestCase


import django_distill


class DjangoDistillInterfaceTestSuite(TestCase):

    def test_import(self):
        assert hasattr(django_distill, 'distill_url')
        assert callable(django_distill.distill_url)
        assert hasattr(django_distill, 'distill_path')
        assert callable(django_distill.distill_path)
        assert hasattr(django_distill, 'distill_re_path')
        assert callable(django_distill.distill_re_path)


# eof
