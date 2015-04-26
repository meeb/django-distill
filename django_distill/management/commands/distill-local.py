# -*- coding: utf-8 -*-

import os

from django.core.management.base import (BaseCommand, CommandError)
from django.conf import settings
from django.conf.urls import include as include_urls

from django_distill import (urls_to_distill, DistillRender)

class Command(BaseCommand):

    help = 'Generates a static local site using distill'
    ignore_static_dirs = ('admin', 'grappelli')

    def add_arguments(self, parser):
        parser.add_argument('output_dir', nargs='?', type=str)

    def handle(self, *args, **options):
        #if settings.USE_I18N:
        #    e = 'settings.USE_I18N needs to be False to use distill'
        #    raise CommandError(e)
        output_dir = options.get('output_dir')
        static_dir = settings.STATIC_ROOT
        static_output_dir = os.path.join
        if not output_dir:
            raise CommandError('Usage: ./manage.py distill-local [directory]')
        output_dir = os.path.abspath(os.path.expanduser(output_dir))

        self.stdout.write('Output path: {}'.format(output_dir))
        if os.path.isdir(output_dir):
            q = 'Output directory already exists, overwrite it? (YES/no): '
            answer = raw_input(q)
            if not answer or answer == 'YES':
                self.stdout.write('Overwriting directory...')
            else:
                raise CommandError('Aborting...')
        else:
            answer = raw_input('Does not exist, create it? (YES/no): ')
            if not answer or answer == 'YES':
                self.stdout.write('Creating directory...')
                os.makedirs(output_dir)
            else:
                raise CommandError('Aborting...')
        self.stdout.write('Loading site URLs')
        self.load_urls()
        self.stdout.write('Rendering site:')
        renderer = DistillRender(output_dir, urls_to_distill)
        for (page_uri, http_response) in renderer.render():
            full_path = os.path.join(output_dir, page_uri[1:])
            content = http_response.content
            self.stdout.write('Writing page: {} to {} ["{}", {} bytes]'.format(
                page_uri, full_path, http_response.get('Content-Type'),
                len(content)))
            with open(full_path, 'w') as f:
                f.write(content)
        self.stdout.write('Copying static media:')

        self.stdout.write('Done.')

    def load_urls(self):
        site_urls = getattr(settings, 'ROOT_URLCONF')
        if site_urls:
            include_urls(site_urls)

# eof
