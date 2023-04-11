import os
import sys
import warnings
from base64 import b64decode
from binascii import hexlify


try:
    from googleapiclient import discovery
    from google.cloud import storage
except ImportError:
    name = 'django_distill.backends.google_storage'
    pipm = 'google-api-python-client google-cloud-storage'
    sys.stdout.write('{} backend requires {}:\n'.format(name, pipm))
    sys.stdout.write('$ pip install .[google]{}\n\n'.format(pipm))
    raise


from django_distill.errors import DistillPublishError
from django_distill.backends import BackendBase


class GoogleCloudStorageBackend(BackendBase):
    '''
        Publisher for Google Cloud Storage. Implements the BackendBase.
    '''

    REQUIRED_OPTIONS = ('ENGINE', 'BUCKET')

    def account_username(self):
        return

    def account_container(self):
        return self.options.get('BUCKET', '')

    def authenticate(self):
        credentials_file = self.options.get('JSON_CREDENTIALS', '')
        if credentials_file:
            if not os.path.exists(credentials_file):
                err = 'Credentials file does not exist: {}'
                raise DistillPublishError(err.format(credentials_file))
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_file
        
        bucket = self.account_container()
        self.d['connection'] = storage.Client()
        self.d['bucket'] = self.d['connection'].get_bucket(bucket)

    def list_remote_files(self):
        rtn = set()
        for b in self.d['bucket'].list_blobs():
            rtn.add(b.name)
        return rtn

    def delete_remote_file(self, remote_name):
        b = self.d['bucket'].get_blob(remote_name)
        return b.delete()

    def compare_file(self, local_name, remote_name):
        b = self.d['bucket'].get_blob(remote_name)
        local_hash = self._get_local_file_hash(local_name)
        remote_hash = str(hexlify(b64decode(b.md5_hash)).decode())
        return local_hash == remote_hash

    def upload_file(self, local_name, remote_name):
        b = self.d['bucket'].blob(remote_name)
        b.upload_from_filename(local_name)
        b.make_public()
        return True

    def create_remote_dir(self, remote_dir_name):
        # not required for Google Storage buckets
        return True

    def remote_path(self, local_name):
        truncated_path = super().remote_path(local_name)
        # Replace \ for /, Google Cloud Files API docs state they handle both \ and /
        # as directory separators but really make sure we're only using / in blob names
        return truncated_path.replace('\\', '/')


backend_class = GoogleCloudStorageBackend
