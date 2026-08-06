#!/usr/bin/env python


import os
import sys

if __name__ == "__main__":
    try:
        command = sys.argv[1]
    except IndexError:
        command = None
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    if command == "testsuite":
        import django
        from django.conf import settings
        from django.test.utils import get_runner

        django.setup()
        TestRunner = get_runner(settings)
        test_runner = TestRunner(verbosity=2)
        failures = test_runner.run_tests(["tests"])
        sys.exit(bool(failures))
    else:
        try:
            from django.core.management import execute_from_command_line
        except ImportError as exc:
            raise ImportError("Error importing django, is it installed?") from exc
        execute_from_command_line(sys.argv)
