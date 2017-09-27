# -*- coding: utf-8 -*-


import sys
import warnings


try:
    from boto.s3.connection import S3Connection, OrdinaryCallingFormat
    from boto.s3.key import Key
except ImportError:
    name = 'django_distill.backends.amazon_s3'
    pipm = 'boto'
    sys.stdout.write('{} backend requires {}:\n'.format(name, pipm))
    sys.stdout.write('$ pip install {}\n\n'.format(pipm))
    raise


from django_distill.errors import DistillPublishError
from django_distill.backends import BackendBase
from ssl import CertificateError


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

    def authenticate(self, calling_format=None):
        access_key_id = self.account_username()
        secret_access_key = self.options.get('SECRET_ACCESS_KEY', '')
        bucket = self.account_container()
        kwargs = {'calling_format': calling_format} if calling_format else {}
        try:
            self.d['connection'] = S3Connection(access_key_id,
                                                secret_access_key, **kwargs)
            self.d['bucket'] = self.d['connection'].get_bucket(bucket)
        except CertificateError as e:
            # work-around for upstream boto bug for buckets containing dots:
            # https://github.com/boto/boto/issues/2836
            if calling_format:
                raise e
            self.authenticate(calling_format=OrdinaryCallingFormat())

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
