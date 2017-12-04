# -*- coding: utf-8 -*-


import os
import sys
from shutil import rmtree


from future.utils import raise_with_traceback


from django.core.management.base import (BaseCommand, CommandError)
from django.conf import settings


from django_distill.distill import urls_to_distill
from django_distill.renderer import (run_collectstatic, render_to_dir)
from django_distill.errors import DistillError


try:
    input = raw_input
except NameError:
    pass


class Command(BaseCommand):

    help = 'Generates a static local site using distill'

    def add_arguments(self, parser):
        parser.add_argument('output_dir', nargs='?', type=str)
        parser.add_argument('--collectstatic', dest='collectstatic',
                            action='store_true')
        parser.add_argument('--quiet', dest='quiet', action='store_true')
        parser.add_argument('--force', dest='force', action='store_true')

    def _quiet(self, *args, **kwargs):
        pass

    def handle(self, *args, **options):
        output_dir = options.get('output_dir')
        collectstatic = options.get('collectstatic')
        quiet = options.get('quiet')
        force = options.get('force')
        if quiet:
            stdout = self._quiet
        else:
            stdout = self.stdout.write
        if not output_dir:
            output_dir = getattr(settings, 'DISTILL_DIR', None)
            if not output_dir:
                e = 'Usage: ./manage.py distill-local [directory]'
                raise CommandError(e)
        if collectstatic:
            run_collectstatic(stdout)
        if not os.path.isdir(settings.STATIC_ROOT):
            e = 'Static source directory does not exist, run collectstatic'
            raise CommandError(e)
        output_dir = os.path.abspath(os.path.expanduser(output_dir))
        stdout('')
        stdout('You have requested to create a static version of')
        stdout('this site into the output path directory:')
        stdout('')
        stdout('    Source static path:  {}'.format(settings.STATIC_ROOT))
        stdout('    Distill output path: {}'.format(output_dir))
        stdout('')
        if os.path.isdir(output_dir):
            stdout('Distill output directory exists, clean up?')
            stdout('This will delete and recreate all files in the output dir')
            stdout('')
            if force:
                ans = 'yes'
            else:
                ans = input('Type \'yes\' to continue, or \'no\' to cancel: ')
            if ans.lower() == 'yes':
                stdout('Recreating output directory...')
                rmtree(output_dir)
                os.makedirs(output_dir)
            else:
                raise CommandError('Distilling site cancelled.')
        else:
            ans = input('Does not exist, create it? (YES/no): ')
            if ans.lower() == 'yes':
                stdout('Creating directory...')
                os.makedirs(output_dir)
            else:
                raise CommandError('Aborting...')
        stdout('')
        stdout('Generating static site into directory: {}'.format(output_dir))
        try:
            render_to_dir(output_dir, urls_to_distill, stdout)
        except DistillError as err:
            raise raise_with_traceback(CommandError(str(err)))
        stdout('')
        stdout('Site generation complete.')


# eof
