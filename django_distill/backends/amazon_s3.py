# -*- coding: utf-8 -*-

import sys
import warnings

try:
    import boto
except ImportError:
    l = 'django_distill.backends.amazon_s3'
    m = 'boto'
    sys.stdout.write('{} backend requires {}:\n'.format(l, m))
    sys.stdout.write('$ pip install {}\n\n'.format(m))
    raise

from django_distill.errors import DistillPublishError
from django_distill.backends import BackendBase

class AmazonS3Backend(BackendBase):
    '''
        Publisher for Amazon S3. Implements the BackendBase.
    '''

    REQUIRED_OPTIONS = ('ENGINE', 'PUBLIC_URL', 'ACCESS_KEY_ID',
                        'SECRET_ACCESS_KEY', 'BUCKET', 'ENDPOINT')

    def account_username(self):
        return self.options.get('ACCESS_KEY_ID', '')

    def account_container(self):
        return self.options.get('BUCKET', '')

    def authenticate(self):
        raise DistillPublishError('TODO')

    def list_remote_files(self):
        raise DistillPublishError('TODO')

    def delete_remote_file(self, remote_name):
        raise DistillPublishError('TODO')

    def compare_file(self, local_name, remote_name):
        raise DistillPublishError('TODO')

    def upload_file(self, local_name, remote_name):
        raise DistillPublishError('TODO')

    def create_remote_dir(self, remote_dir_name):
        raise DistillPublishError('TODO')

backend_class = AmazonS3Backend

# eof
