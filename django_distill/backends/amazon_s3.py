# -*- coding: utf-8 -*-


import sys
import warnings


try:
    from boto.s3.connection import S3Connection
    from boto.s3.key import Key
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
                        'SECRET_ACCESS_KEY', 'BUCKET')

    def account_username(self):
        return self.options.get('ACCESS_KEY_ID', '')

    def account_container(self):
        return self.options.get('BUCKET', '')

    def authenticate(self):
        access_key_id = self.account_username()
        secret_access_key = self.options.get('SECRET_ACCESS_KEY', '')
        bucket = self.account_container()
        self.d['connection'] = S3Connection(access_key_id, secret_access_key)
        self.d['bucket'] = self.d['connection'].get_bucket(bucket)

    def list_remote_files(self):
        rtn = set()
        for k in self.d['bucket'].list():
            rtn.add(k.name)
        return rtn

    def delete_remote_file(self, remote_name):
        key = self.d['bucket'].get_key(remote_name)
        return key.delete()

    def compare_file(self, local_name, remote_name):
        key = self.d['bucket'].get_key(remote_name)
        local_hash = self._get_local_file_hash(local_name)
        return local_hash == key.etag[1:-1]

    def upload_file(self, local_name, remote_name):
        k = Key(self.d['bucket'])
        k.key = remote_name
        k.set_contents_from_filename(local_name)
        return True

    def create_remote_dir(self, remote_dir_name):
        # not required for S3 buckets
        return True


backend_class = AmazonS3Backend


# eof
