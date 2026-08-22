# noqa: N999

import warnings

from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Depreciated command that generates a static local site using distill"

    def add_arguments(self, parser):
        parser.add_argument("output_dir", nargs="?", type=str)
        parser.add_argument(
            "--collectstatic", dest="collectstatic", action="store_true"
        )
        parser.add_argument("--quiet", dest="quiet", action="store_true")
        parser.add_argument("--force", dest="force", action="store_true")
        parser.add_argument("--debug", dest="debug", type=str, default="false")
        parser.add_argument(
            "--exclude-staticfiles", dest="exclude_staticfiles", action="store_true"
        )
        parser.add_argument(
            "--generate-redirects", dest="generate_redirects", action="store_true"
        )
        parser.add_argument(
            "--parallel-render", dest="parallel_render", type=int, default=1
        )

    def handle(self, *args, **options):
        wrapped_args = ["--output-directory", options.get("output_dir")]
        if options.get("collectstatic"):
            wrapped_args.append("--collectstatic")
        if options.get("quiet"):
            wrapped_args.append("--quiet")
        if options.get("force"):
            wrapped_args.append("--force")
        if options.get("exclude_staticfiles"):
            wrapped_args.append("--exclude-staticfiles")
        if options.get("generate_redirects"):
            wrapped_args.append("--generate-redirects")
        wrapped_args.append("--parallel-render")
        wrapped_args.append(options.get("parallel_render"))
        wrapped_args.append("--debug")
        wrapped_args.append(options.get("debug"))
        warnings.warn(
            '"./manage.py distill-local" is depreciated, use "./manage.py distill generate" instead'
        )
        call_command("distill", "generate", *wrapped_args)
