# -*- coding: utf-8 -*-

import os
from shutil import rmtree

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
        static_dir = settings.STATIC_ROOT
        static_url = settings.STATIC_URL
        if not output_dir:
            raise CommandError('Usage: ./manage.py distill-local [directory]')
        output_dir = os.path.abspath(os.path.expanduser(output_dir))
        static_output_dir = os.path.join(output_dir, static_url[1:])
        self.stdout.write('Static path: {}'.format(static_dir))
        self.stdout.write('Output path: {}'.format(output_dir))
        if os.path.isdir(output_dir):
            q = 'Output directory exists, delete all files in it? (YES/no): '
            answer = raw_input(q)
            if not answer or answer == 'YES':
                self.stdout.write('Deleting all files in output directory...')
                rmtree(output_dir)
                os.makedirs(output_dir)
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
        self.stdout.write('Rendering site...')
        renderer = DistillRender(output_dir, urls_to_distill)
        for page_uri, http_response in renderer.render():
            full_path = os.path.join(output_dir, page_uri[1:])
            content = http_response.content
            self.stdout.write('Rendering page: {} -> {} ["{}", {} bytes]'.format(
                page_uri, full_path, http_response.get('Content-Type'),
                len(content)))
            with open(full_path, 'w') as f:
                f.write(content)
        self.stdout.write('Copying static media...')
        for file_from, file_to in renderer.copy_static(static_dir, static_output_dir):
            self.stdout.write('Copying static: {} -> {}'.format(file_from,
                file_to))
        self.stdout.write('Done.')

    def load_urls(self):
        site_urls = getattr(settings, 'ROOT_URLCONF')
        if site_urls:
            include_urls(site_urls)

# eof
