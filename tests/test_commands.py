from importlib import import_module
from django.test import TestCase


class DjangoDistillCommandTestSuite(TestCase):

    def test_command_imports_distill_local(self):
        import_module('django_distill.management.commands.distill-local')

    def test_command_imports_distill_publish(self):
        import_module('django_distill.management.commands.distill-publish')

    def test_command_imports_distill_test_publish(self):
        import_module('django_distill.management.commands.distill-test-publish')
