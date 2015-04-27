# -*- coding: utf-8 -*-

import sys

try:
    import pyrax
except ImportError:
    l = 'django_distill.backends.rackspace_files'
    m = 'pyrax'
    sys.stdout.write('{} backend requires {}:\n'.format(l, m))
    sys.stdout.write('$ pip install {}\n\n'.format(m))
    raise

from django_distill.errors import DistillPublishError
from django_distill.backends import BackendBase

class RackspaceCloudFilesBackend(BackendBase):
    '''
        Publisher for Rackspace Cloud Files. Implements the BackendBase.
    '''

    def authenticate(self):
        username = self.options.get('USERNAME', '')
        api_get = self.options.get('API_KEY', '')
        region = self.options.get('REGION', '')
        container = self.options.get('CONTAINER', '')
        pyrax.set_setting('identity_type', 'rackspace')
        pyrax.set_credentials(username, api_get, region=region)
        self.d['connection'] = pyrax.cloudfiles
        self.d['container'] = self.d['connection'].get_container(container)

    def list_remote_files(self):
        raise NotImplementedError('list_remote_files must be implemented')

    def list_local_files(self):
        raise NotImplementedError('list_local_files must be implemented')

    def delete_remote_file(self, remote_name):
        return self.d['container'].delete_object(remote_name)

    def compare_file(self, local_name, remote_name):
        return True

    def upload_file(self, local_name, remote_name):
        if not self._file_exists(local_name):
            raise DistillPublishError('File does not exist: {}'.format(
                local_name))
        local_hash = self._get_local_file_hash(local_name)
        remote_obj = self.d['container'].upload_file(local_name, remote_name,
            etag=local_hash)
        return local_hash == remote_obj.etag

    def check_file(self, local_name, remote_name):
        return True

backend_class = RackspaceCloudFilesBackend

# eof
