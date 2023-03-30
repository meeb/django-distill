import os
import tempfile
from django.conf import settings
from django.core.management.base import (BaseCommand, CommandError)
from django_distill.backends import get_backend
from django_distill.distill import urls_to_distill
from django_distill.errors import DistillError
from django_distill.renderer import (run_collectstatic, render_to_dir,
                                     copy_static_and_media_files)
from django_distill.publisher import publish_dir


class Command(BaseCommand):

    help = 'Distills a site into a temporary local directory then publishes it'

    def add_arguments(self, parser):
        parser.add_argument('publish_target_name', nargs='?', type=str)
        parser.add_argument('--collectstatic', dest='collectstatic',
                            action='store_true')
        parser.add_argument('--quiet', dest='quiet', action='store_true')
        parser.add_argument('--force', dest='force', action='store_true')
        parser.add_argument('--exclude-staticfiles', dest='exclude_staticfiles',
                    action='store_true')
        parser.add_argument('--skip-verify', dest='skip_verify', action='store_true')
        parser.add_argument('--ignore-remote-content', dest='ignore_remote_content', action='store_true')
        parser.add_argument('--parallel-publish', dest='parallel_publish', type=int, default=1)

    def _quiet(self, *args, **kwargs):
        pass

    def handle(self, *args, **options):
        publish_target_name = options.get('publish_target_name')
        if not publish_target_name:
            publish_target_name = 'default'
        publish_targets = getattr(settings, 'DISTILL_PUBLISH', {})
        publish_target = publish_targets.get(publish_target_name)
        if type(publish_target) != dict:
            e = 'Invalid publish target name: "{}"'.format(publish_target_name)
            e += ', check your settings.DISTILL_PUBLISH values'
            raise CommandError(e)
        publish_engine = publish_target.get('ENGINE')
        if not publish_engine:
            e = 'Publish target {} has no ENGINE'.format(publish_target_name)
            raise CommandError(e)
        collectstatic = options.get('collectstatic')
        exclude_staticfiles = options.get('exclude_staticfiles')
        skip_verify = options.get('skip_verify', False)
        parallel_publish = options.get('parallel_publish')
        ignore_remote_content = options.get('ignore_remote_content', False)
        quiet = options.get('quiet')
        force = options.get('force')
        if quiet:
            stdout = self._quiet
        else:
            stdout = self.stdout.write
        with tempfile.TemporaryDirectory() as output_dir:
            if not output_dir.endswith(os.sep):
                output_dir += os.sep
            backend_class = get_backend(publish_engine)
            backend = backend_class(output_dir, publish_target)
            username = backend.account_username()
            container = backend.account_container()
            stdout('')
            stdout('You have requested to distill and publish this site')
            stdout('to the following target:')
            stdout('')
            stdout('    Settings name: {}'.format(publish_target_name))
            stdout('    Engine:        {}'.format(publish_engine))
            stdout('    Username:      {}'.format(username))
            stdout('    Container:     {}'.format(container))
            stdout('')
            if collectstatic:
                run_collectstatic(stdout)
            if not exclude_staticfiles and not os.path.isdir(settings.STATIC_ROOT):
                e = 'Static source directory does not exist, run collectstatic'
                raise CommandError(e)
            if force:
                ans = 'yes'
            else:
                ans = input('Type \'yes\' to continue, or \'no\' to cancel: ')
            if ans.lower() == 'yes':
                pass
            else:
                raise CommandError('Publishing site cancelled.')
            self.stdout.write('')
            msg = 'Generating static site into directory: {}'
            stdout(msg.format(output_dir))
            try:
                render_to_dir(output_dir, urls_to_distill, stdout)
                if not exclude_staticfiles:
                    copy_static_and_media_files(output_dir, stdout)
            except DistillError as err:
                raise CommandError(str(err)) from err
            stdout('')
            stdout('Publishing site')
            backend.index_local_files()
            publish_dir(backend, stdout, not skip_verify, parallel_publish, ignore_remote_content)

        stdout('')
        stdout('Site generation and publishing complete.')
