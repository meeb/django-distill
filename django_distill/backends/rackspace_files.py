# -*- coding: utf-8 -*-


import sys
import warnings


try:
    import pyrax
except ImportError:
    name = 'django_distill.backends.rackspace_files'
    pipm = 'pyrax'
    sys.stdout.write('{} backend requires {}:\n'.format(name, pipm))
    sys.stdout.write('$ pip install {}\n\n'.format(pipm))
    raise


from django_distill.errors import DistillPublishError
from django_distill.backends import BackendBase


class RackspaceCloudFilesBackend(BackendBase):
    '''
        Publisher for Rackspace Cloud Files. Implements the BackendBase.
    '''

    REQUIRED_OPTIONS = ('ENGINE', 'PUBLIC_URL', 'USERNAME', 'API_KEY',
                        'REGION', 'CONTAINER')

    def account_username(self):
        return self.options.get('USERNAME', '')

    def account_container(self):
        return self.options.get('CONTAINER', '')

    def authenticate(self):
        username = self.account_username()
        api_key = self.options.get('API_KEY', '')
        region = self.options.get('REGION', '')
        container = self.account_container()
        pyrax.set_setting('identity_type', 'rackspace')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            pyrax.set_credentials(username, api_key, region=region)
        self.d['connection'] = pyrax.cloudfiles
        if not self.d['connection']:
            e = 'Failed to connect to Rackspace Cloud Files, check credentials'
            raise DistillPublishError(e)
        self.d['container'] = self.d['connection'].get_container(container)

    def list_remote_files(self):
        rtn = set()
        marker, limit = 100, ''
        while True:
            objects = self.d['container'].get_objects(limit=limit,
                                                      marker=marker)
            if not objects:
                break
            for obj in objects:
                rtn.add(obj.name)
            marker = objects[-1].name
        return rtn

    def delete_remote_file(self, remote_name):
        return self.d['container'].delete_object(remote_name)

    def compare_file(self, local_name, remote_name):
        if not self._file_exists(local_name):
            raise DistillPublishError('File does not exist: {}'.format(
                local_name))
        local_hash = self._get_local_file_hash(local_name)
        o = self.d['container'].get_object(remote_name)
        return o.etag == local_hash

    def upload_file(self, local_name, remote_name):
        if not self._file_exists(local_name):
            raise DistillPublishError('File does not exist: {}'.format(
                local_name))
        local_hash = self._get_local_file_hash(local_name)
        remote_obj = self.d['container'].upload_file(local_name, remote_name,
                                                     etag=local_hash)
        return local_hash == remote_obj.etag

    def create_remote_dir(self, remote_dir_name):
        # Rackspace Files containers have no directories
        pass


backend_class = RackspaceCloudFilesBackend


# eof
