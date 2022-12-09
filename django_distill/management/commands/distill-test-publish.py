import os
from binascii import hexlify
from tempfile import NamedTemporaryFile
from django.conf import settings
from django.core.management.base import (BaseCommand, CommandError)
from django_distill.backends import get_backend


class Command(BaseCommand):

    help = 'Tests a distill publishing target'

    def add_arguments(self, parser):
        parser.add_argument('publish_target_name', nargs='?', type=str)

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
        self.stdout.write('')
        self.stdout.write('You have requested to test a publishing target:')
        self.stdout.write('')
        self.stdout.write('    Name:   {}'.format(publish_target_name))
        self.stdout.write('    Engine: {}'.format(publish_engine))
        self.stdout.write('')
        ans = input('Type \'yes\' to continue, or \'no\' to cancel: ')
        if ans.lower() == 'yes':
            self.stdout.write('')
            self.stdout.write('Testing publishing target...')
        else:
            raise CommandError('Testing publishing target cancelled.')
        self.stdout.write('')
        self.stdout.write('Connecting to backend engine')
        backend_class = get_backend(publish_engine)
        random_file = NamedTemporaryFile(delete=False)
        random_str = hexlify(os.urandom(16))
        random_file.write(random_str)
        random_file.close()
        backend = backend_class(os.path.dirname(random_file.name),
                                publish_target)
        self.stdout.write('Authenticating')
        backend.authenticate()
        remote_file_name = os.path.basename(random_file.name)
        self.stdout.write('Uploading test file: {}'.format(random_file.name))
        backend.upload_file(random_file.name, remote_file_name)
        url = backend.remote_url(random_file.name)
        self.stdout.write('Verifying remote test file: {}'.format(url))
        if backend.check_file(random_file.name, url):
            self.stdout.write('File uploaded correctly, file hash is correct')
        else:
            msg = 'File error, remote file hash differs from local hash'
            self.stderr.write(msg)
        self.stdout.write('Final checks')
        backend.final_checks()
        self.stdout.write('Deleting remote test file')
        backend.delete_remote_file(remote_file_name)
        if os.path.exists(random_file.name):
            self.stdout.write('Deleting local test file')
            os.unlink(random_file.name)
        self.stdout.write('')
        self.stdout.write('Backend testing complete.')
