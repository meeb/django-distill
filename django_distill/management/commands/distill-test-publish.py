# noqa: N999

import warnings

from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Depreciated command that tests a distill publishing target"

    def add_arguments(self, parser):
        parser.add_argument("publish_target_name", nargs="?", type=str)

    def handle(self, *args, **options):
        publish_target_name = options.get("publish_target_name")
        if not publish_target_name:
            publish_target_name = "default"
        wrapped_args = ["--target", publish_target_name]
        warnings.warn(
            '"./manage.py distill-test-publish" is depreciated, use "./manage.py distill test-target" instead'
        )
        call_command("distill", "test-target", *wrapped_args)
