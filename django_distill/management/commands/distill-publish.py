# noqa: N999

import warnings

from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Depreciated command that distills a site into a temporary local directory then publishes it"

    def add_arguments(self, parser):
        parser.add_argument("publish_target_name", nargs="?", type=str)
        parser.add_argument(
            "--collectstatic", dest="collectstatic", action="store_true"
        )
        parser.add_argument("--quiet", dest="quiet", action="store_true")
        parser.add_argument("--force", dest="force", action="store_true")
        parser.add_argument(
            "--exclude-staticfiles", dest="exclude_staticfiles", action="store_true"
        )
        parser.add_argument("--skip-verify", dest="skip_verify", action="store_true")
        parser.add_argument(
            "--ignore-remote-content", dest="ignore_remote_content", action="store_true"
        )
        parser.add_argument(
            "--parallel-publish", dest="parallel_publish", type=int, default=1
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
        if options.get("skip_verify"):
            wrapped_args.append("--skip-verify")
        if options.get("ignore_remote_content"):
            wrapped_args.append("--ignore-remote-content")
        wrapped_args.append("--parallel-render")
        wrapped_args.append(options.get("parallel_render"))
        wrapped_args.append("--parallel-publish")
        wrapped_args.append(options.get("parallel_publish"))
        wrapped_args.append("--debug")
        wrapped_args.append(options.get("debug"))
        warnings.warn(
            '"./manage.py distill-publish" is depreciated, use "./manage.py distill publish" instead'
        )
        call_command("distill", "generate", *wrapped_args)
