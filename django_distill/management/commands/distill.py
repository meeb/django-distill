import tempfile
from logging import getLogger
from shutil import rmtree

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from django_distill.errors import DistillError
from django_distill.publisher import (
    get_publisher_from_options,
    get_publishing_target,
    get_publishing_targets,
)
from django_distill.renderer import DistillRenderer, render_redirects
from django_distill.static import copy_static_and_media_files
from django_distill.utils import NamedTestFile, Path

log = getLogger("main")


def ask_question(question="Type 'yes' to continue, or 'no' to cancel: "):
    return input(question).lower() == "yes"


def run_collectstatic():
    try:
        call_command("collectstatic", "--noinput")
    except Exception as e:
        raise CommandError(f'Error running "collectstatic": {e}') from e


def load_target(target_name):
    try:
        target_options = get_publishing_target(target_name)
    except DistillError as e:
        raise CommandError(str(e)) from e
    try:
        publisher = get_publisher_from_options(target_options)
    except Exception as e:
        raise CommandError(f"Failed to load backend '{target_name}': {e}") from e
    return target_options, publisher


class Command(BaseCommand):
    help = "Generates a local static site"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.quiet = False
        self.debug = True

    def add_arguments(self, parser):
        parser.add_argument("subcommand", nargs="?", type=str)
        parser.add_argument(
            "--output-directory", dest="output_directory", type=str, default=None
        )
        parser.add_argument("--target", dest="target", type=str, default="default")
        parser.add_argument(
            "--collectstatic", dest="collectstatic", action="store_true"
        )
        parser.add_argument("--quiet", dest="quiet", action="store_true")
        parser.add_argument("--force", dest="force", action="store_true")
        parser.add_argument("--debug", dest="debug", action="store_true")
        parser.add_argument(
            "--exclude-staticfiles", dest="exclude_staticfiles", action="store_true"
        )
        parser.add_argument(
            "--generate-redirects", dest="generate_redirects", action="store_true"
        )
        parser.add_argument(
            "--parallel-render", dest="parallel_render", type=int, default=1
        )
        parser.add_argument(
            "--parallel-publish", dest="parallel_publish", type=int, default=1
        )
        parser.add_argument("--skip-verify", dest="skip_verify", action="store_true")
        parser.add_argument(
            "--ignore-remote-content", dest="ignore_remote_content", action="store_true"
        )

    def write(self, msg, error=False):
        if not self.quiet:
            if error:
                self.stderr.write(msg)
            else:
                self.stdout.write(msg)

    def handle(self, *args, **options):
        subcommand_map = {
            "help": self.command_help,
            "generate": self.command_generate,
            "publish": self.command_publish,
            "test-target": self.command_test_target,
            "list-static-urls": self.command_list_static_urls,
            "list-publish-targets": self.command_list_publish_targets,
        }
        subcommand_name = options.get("subcommand")
        self.quiet = options.get("quiet")
        self.debug = options.get("debug")
        if subcommand_name is None:
            subcommand_func = self.command_help
        else:
            subcommand_func = subcommand_map.get(subcommand_name)
        if subcommand_func:
            subcommand_func(*args, **options)
        else:
            raise CommandError(
                f'Unknown subcommand specified: {subcommand_name} (try "help")'
            )

    def command_help(self, *args, **options):
        self.write(self.help)
        self.write("")
        self.write("This help message:")
        self.write("    ./manage.py distill help")
        self.write("")
        self.write("Generate a local static site:")
        self.write(
            "    ./manage.py distill generate --output-directory=<directory_name>"
        )
        self.write("")
        self.write(
            'Generate a static site and publish it to remote object storage backend ("target_name" defaults to "default"):'
        )
        self.write("    ./manage.py distill publish --target=<target_name>")
        self.write("")
        self.write(
            'Test a publish target is configured correctly ("target_name" defaults to "default"):'
        )
        self.write("    ./manage.py distill test-target --target=<target_name>")
        self.write("")
        self.write(
            "List all URL routes in the project that have been defined as static:"
        )
        self.write("    ./manage.py distill list-static-urls")
        self.write("")
        self.write("List all defined publish targets:")
        self.write("    ./manage.py distill list-publish-targets")
        self.write("")
        self.write("Additional options:")
        self.write("")
        self.write(
            '    --collectstatic - when generating a local static site, also run "collectstatic"'
        )
        self.write("    --quiet - no log output")
        self.write('    --force - automatically answer "yes" to all questions')
        self.write(
            "    --exclude-staticfiles - when generating a local static site, exclude static files"
        )
        self.write(
            "    --generate-redirects - create static HTML redirect pages for any 301 or 303 redirects"
        )
        self.write(
            "    --parallel-render=N - number of parallel processes to use when rendering the site, defaults to 1"
        )
        self.write("")

    def command_generate(self, *args, **options):
        output_directory = options.get("output_directory")
        if not output_directory:
            output_directory = getattr(settings, "DISTILL_DIR", None)
            if not output_directory:
                raise CommandError(
                    "No static site directory specified, one of --output-directory or "
                    "settings.DISTILL_DIR must be set."
                )
        output_directory = Path(output_directory).resolve()
        force = options.get("force")
        exclude_staticfiles = options.get("exclude_staticfiles")
        if options.get("collectstatic"):
            self.write('Running "collectstatic" ...')
            run_collectstatic()
        if not exclude_staticfiles and not Path(settings.STATIC_ROOT).is_dir():
            raise CommandError(
                f'Static source directory "{settings.STATIC_ROOT}" does not exist, run collectstatic'
            )
        self.write("")
        self.write(
            "You have requested to create a static version of his site into the output path directory:"
        )
        self.write("")
        if not exclude_staticfiles:
            self.write(f"    Source static path:      {settings.STATIC_ROOT}")
        self.write(f"    Static site output path: {output_directory}")
        self.write("")
        if output_directory.is_dir():
            self.write("Static site output directory already exists, delete it first?")
            self.write("This will delete and recreate all files in the output dir")
            self.write("")
            if force or ask_question():
                self.write("Recreating output directory ...")
                rmtree(output_directory)
                output_directory.mkdir(parents=True)
            else:
                raise CommandError("Static site generation cancelled.")
        else:
            self.write("Static site output directory does not exist, create it?")
            if force or ask_question():
                self.write("Creating output directory ...")
                output_directory.mkdir(parents=True)
            else:
                raise CommandError("Static site generation cancelled.")
        self.write("")
        self.write(f"Generating static site into directory: {output_directory}")
        try:
            with DistillRenderer(
                enable_debug=self.debug, concurrency=options.get("parallel_render")
            ) as renderer:
                renderer.render_to_directory(output_directory)
            if not exclude_staticfiles:
                copy_static_and_media_files(output_directory)
        except DistillError as e:
            raise CommandError(str(e)) from e
        self.write("")
        if options.get("generate_redirects"):
            self.write("Generating redirects ...")
            render_redirects(output_directory)
            self.write("")
        self.write("Static site generation complete.")

    def command_publish(self, *args, **options):
        target_name = options.get("target")
        target_options, publisher_class = load_target(target_name)
        collectstatic = options.get("collectstatic")
        exclude_staticfiles = options.get("exclude_staticfiles")
        generate_redirects = options.get("generate_redirects")
        parallel_render = options.get("parallel_render")
        skip_verify = options.get("skip_verify")
        parallel_publish = options.get("parallel_publish")
        ignore_remote_content = options.get("ignore_remote_content")
        if collectstatic:
            self.write('Running "collectstatic" ...')
            run_collectstatic()
        if not exclude_staticfiles and not Path(settings.STATIC_ROOT).is_dir():
            raise CommandError(
                f'Static source directory "{settings.STATIC_ROOT}" does not exist, run collectstatic'
            )
        self.write("")
        self.write(f"Publishing static site to target: {target_name}")
        self.write("")
        self.write(f"    Publisher:    {target_options.get('ENGINE')}")
        self.write(f"    Public URL:   {target_options.get('PUBLIC_URL')}")
        self.write("")
        self.write(
            "The static site will first be generated locally into a temporary directory"
        )
        self.write(
            "before being uploaded to the publishing target. Once uploaded and verified"
        )
        self.write("the temporary directory will be deleted.")
        self.write("")
        if options.get("force") or ask_question():
            self.write("Publishing static site ...")
            with tempfile.TemporaryDirectory() as tmpdirname:
                tmpdirpath = Path(tmpdirname)
                self.write(
                    f"Generating static site into temporary directory: {tmpdirpath}"
                )
                with DistillRenderer(
                    enable_debug=self.debug, concurrency=parallel_render
                ) as renderer:
                    renderer.render_to_directory(tmpdirpath)
                if not exclude_staticfiles:
                    copy_static_and_media_files(tmpdirpath)
                if generate_redirects:
                    self.write("Generating redirects ...")
                    render_redirects(tmpdirpath)
                self.write("Authenticating to publishing target ...")
                publisher = publisher_class(tmpdirpath, target_options)
                publisher.authenticate()
                self.write("Publishing static site to target ...")
                publisher.publish(
                    verify=not skip_verify,
                    concurrency=parallel_publish,
                    ignore_remote_content=ignore_remote_content,
                )
            self.write("Publishing static site complete.")
        else:
            self.write("Publishing static site cancelled.")

    def command_test_target(self, *args, **options):
        target_name = options.get("target")
        target_options, publisher_class = load_target(target_name)
        self.write("")
        self.write(f"Testing static site publishing target: {target_name}")
        self.write("")
        self.write(f"    Publisher:    {target_options.get('ENGINE')}")
        self.write(f"    Public URL:   {target_options.get('PUBLIC_URL')}")
        self.write("")
        self.write(
            "The test will create a random test file, attempt to upload it to the"
        )
        self.write(
            "target and verify it is accessible on the public URL before deleting it."
        )
        self.write("")
        if ask_question():
            self.write("Testing publishing target...")
            with NamedTestFile() as test_file:
                publisher = publisher_class(test_file.path.parent, target_options)
                self.write(f"Test file created: {test_file}")
                remote_url = publisher.remote_url(test_file)
                self.write(f"Testing URL: {remote_url}")
                self.write("Uploading test file...")
                publisher.upload_test_file(test_file)
                self.write("Verifying remote test file...")
                local_hash = publisher.get_local_file_hash(test_file)
                remote_hash = publisher.get_url_hash(remote_url)
                self.write(f"    Local file hash:  {local_hash}")
                self.write(f"    Remote file hash: {remote_hash}")
                if local_hash == remote_hash:
                    self.write("File uploaded correctly, file hash is correct.")
                else:
                    self.write(
                        "Test failed, remote file hash differs from local hash",
                        error=True,
                    )
                self.write("Deleting test files...")
                remote_path = publisher.remote_path(test_file)
                publisher.delete_remote_file(remote_path)
            self.write("Test complete.")
        else:
            self.write("Testing target cancelled.")

    def command_list_static_urls(self, *args, **options):
        self.write("")
        self.write("Defined static site URLs:")
        self.write("")
        with DistillRenderer(enable_debug=self.debug) as renderer:
            for url in renderer.urls():
                self.write(f"    {url}")
        self.write("")

    def command_list_publish_targets(self, *args, **options):
        self.write("")
        self.write("Defined static site publishing targets:")
        self.write("")
        publishing_targets = get_publishing_targets()
        if publishing_targets:
            for target_name, target_options in publishing_targets.items():
                self.write(f"    {target_name}:")
                for param, value in target_options.items():
                    self.write(f"        {param}: {value}")
            self.write("")
        else:
            self.write(
                "    No publishing targets defined, add one to settings.DISTILL_PUBLISH"
            )
            self.write("")
