# -*- coding: utf-8 -*-

import sys
import warnings
import ftplib

from django_distill.errors import DistillPublishError
from django_distill.backends import BackendBase

class FTPBackend(BackendBase):
    '''
        Publisher for FTP. Implements the BackendBase.
    '''

    REQUIRED_OPTIONS = ('ENGINE', 'PUBLIC_URL', 'HOSTNAME', 'USERNAME',
                        'PASSWORD', 'REMOTE_DIRECTORY')

    def account_username(self):
        return self.options.get('USERNAME', '')

    def account_container(self):
        return self.options.get('REMOTE_DIRECTORY', '')

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

backend_class = FTPBackend

# eof
