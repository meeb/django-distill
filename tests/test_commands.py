from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class DistillCommandsTestSuite(TestCase):
    def test_command_help(self):
        with StringIO() as o:
            call_command("distill", "help", stdout=o)
            o.seek(0)
            command_output = o.read()
            command_lines = command_output.split("\n")
            self.assertEqual(command_lines[0], "Generates a local static site")

    def test_unknown_command(self):
        with self.assertRaises(CommandError):
            call_command("distill", "unknown")

    def test_quiet_flag(self):
        with StringIO() as o:
            call_command("distill", "help", "--quiet", stdout=o)
            o.seek(0)
            command_output = o.read()
            self.assertEqual(command_output, "")
