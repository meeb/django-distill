from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from django_distill.management.commands.distill import Command as DistillCommand


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

    def test_debug_flag(self):
        with patch(
            "django_distill.management.commands.distill.DistillRenderer"
        ) as mock_renderer:
            mock_renderer.return_value.__enter__.return_value.urls.return_value = []
            with StringIO() as o:
                call_command("distill", "list-static-urls", "--debug=false", stdout=o)
            mock_renderer.assert_called_with(enable_debug=False)

            with StringIO() as o:
                call_command("distill", "list-static-urls", "--debug=true", stdout=o)
            mock_renderer.assert_called_with(enable_debug=True)

            with StringIO() as o:
                call_command("distill", "list-static-urls", stdout=o)
            mock_renderer.assert_called_with(enable_debug=True)

        cmd = DistillCommand()
        cmd.stdout = StringIO()
        cmd.handle(subcommand="help", debug="false")
        self.assertFalse(cmd.debug)
        cmd.handle(subcommand="help", debug="true")
        self.assertTrue(cmd.debug)
        cmd.handle(subcommand="help", debug="True")
        self.assertTrue(cmd.debug)
        cmd.handle(subcommand="help", debug="False")
        self.assertFalse(cmd.debug)
