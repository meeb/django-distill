# -*- coding: utf-8 -*-

import os

from django.core.management.base import (BaseCommand, CommandError)
from django.conf import settings
from django.conf.urls import include as include_urls

from django_distill import (urls_to_distill, DistillRender)

class Command(BaseCommand):

    help = 'Generates a static local site using distill'

    def add_arguments(self, parser):
        parser.add_argument('output_dir', nargs='?', type=str)

    def handle(self, *args, **options):
        output_dir = options.get('output_dir')
        if not output_dir:
            raise CommandError('Usage: ./manage.py distill-local [directory name]')
        output_dir = os.path.abspath(os.path.expanduser(output_dir))
        self.stdout.write('Output path: {}'.format(output_dir))
        if os.path.isdir(output_dir):
            answer = raw_input('Already exists, overwrite it? (YES/no)\n')
            if not answer or answer == 'YES':
                self.stdout.write('Overwriting directory...')
            else:
                raise CommandError('Aborting...')
        else:
            answer = raw_input('Does not exist, create it? (YES/no)\n')
            if not answer or answer == 'YES':
                self.stdout.write('Creating directory...')
                os.makedirs(output_dir)
            else:
                raise CommandError('Aborting...')
        self.stdout.write('Loading site URLs')
        self.load_urls()
        self.stdout.write('Rendering site:')
        renderer = DistillRender(output_dir, urls_to_distill)
        for (page_uri, page_data) in renderer:
            self.stdout.write(page_uri[1][0])

    def load_urls(self):
        site_urls = getattr(settings, 'ROOT_URLCONF')
        if site_urls:
            include_urls(site_urls)

# eof
