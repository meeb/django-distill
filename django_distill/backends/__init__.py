# -*- coding: utf-8 -*-

import os
import sys
import warnings
from hashlib import md5

class BackendBase(object):
    '''
        Generic base class for all backends, mostly an interface / template.
    '''

    def __init__(self, source_dir, options):
        self.source_dir = source_dir
        self.options = options
        self.local_files = set()
        self.remote_files = set()
        self.d = {}

    def _get_local_file_hash(self, file_path, digest_func=md5, chunk=1048576):
        # md5 is used by both Amazon S3 and Rackspace Cloud Files
        if not self._file_exists(file_path):
            return None
        digest = digest_func()
        with open(file_path, 'r') as f:
            while True:
                data = f.read(chunk)
                if not data:
                    break
                digest.update(data)
        return digest.hexdigest()

    def _file_exists(self, file_path):
        return os.path.isfile(file_path)

    def authenticate(self):
        raise NotImplementedError('authenticate must be implemented')

    def list_remote_files(self):
        raise NotImplementedError('list_remote_files must be implemented')

    def list_local_files(self):
        raise NotImplementedError('list_local_files must be implemented')

    def delete_remote_file(self):
        raise NotImplementedError('delete_remote_file must be implemented')

    def compare_file(self):
        raise NotImplementedError('compare_file must be implemented')

    def upload_file(self):
        raise NotImplementedError('upload_file must be implemented')

    def check_file(self, local_file, remote_file):
        raise NotImplementedError('check_file must be implemented')

def get_backend(engine):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        try:
            backend = __import__(engine, globals(), locals(), ['backend_class'])
        except ImportError as e:
            sys.stderr.write('Failed to import backend engine')
            raise
    module = getattr(backend, 'backend_class')
    if not module:
        raise ImportError('Backend engine has no backend_class attribute')
    return module

# eof
