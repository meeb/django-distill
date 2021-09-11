import os
import sys
import warnings
import mimetypes
from hashlib import md5
from binascii import hexlify
import requests
from urllib.parse import urlsplit, urlunsplit
from django_distill.errors import DistillPublishError
from django_distill.renderer import filter_dirs


class BackendBase(object):
    '''
        Generic base class for all backends, mostly an interface / template.
    '''

    REQUIRED_OPTIONS = ()

    def __init__(self, source_dir, options):
        if not source_dir.endswith(os.sep):
            source_dir += os.sep
        self.source_dir = source_dir
        self.options = options
        self.local_files = set()
        self.local_dirs = set()
        self.remote_files = set()
        self.remote_url_parts = urlsplit(options.get('PUBLIC_URL', ''))
        self.d = {}
        self._validate_options()

    def _validate_options(self):
        for o in self.REQUIRED_OPTIONS:
            if o not in self.options:
                e = 'Missing required settings value for this backend: {}'
                raise DistillPublishError(e.format(o))

    def index_local_files(self):
        for root, dirs, files in os.walk(self.source_dir):
            dirs[:] = filter_dirs(dirs)
            for d in dirs:
                self.local_dirs.add(os.path.join(root, d))
            for f in files:
                self.local_files.add(os.path.join(root, f))

    def _get_local_file_hash(self, file_path, digest_func=md5, chunk=1048576):
        # md5 is used by Amazon S3, Rackspace Cloud Files and Google Storage
        if not self._file_exists(file_path):
            return None
        digest = digest_func()
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(chunk)
                if not data:
                    break
                digest.update(data)
        return digest.hexdigest()

    def _get_url_hash(self, url, digest_func=md5, chunk=1024):
        # CDN cache buster
        url += '?' + hexlify(os.urandom(16)).decode('utf-8')
        request = requests.get(url, stream=True)
        if request.status_code == 404:
            return False
        digest = digest_func()
        for block in request.iter_content(chunk_size=chunk):
            if block:
                digest.update(block)
        return digest.hexdigest()

    def _file_exists(self, file_path):
        return os.path.isfile(file_path)

    def local_file_mimetype(self, local_name):
        try:
            return mimetypes.guess_type(local_name)[0]
        except Exception:
            return 'application/octet-stream'

    def remote_url(self, local_name):
        if local_name[:len(self.source_dir)] != self.source_dir:
            raise DistillPublishError('File {} is not in source dir {}'.format(
                local_name, self.source_dir))
        truncated = local_name[len(self.source_dir):]
        remote_file = '/'.join(truncated.split(os.sep))
        remote_uri = self.remote_url_parts.path + remote_file
        return urlunsplit((self.remote_url_parts.scheme,
                           self.remote_url_parts.netloc, remote_uri, '', ''))

    def list_local_dirs(self):
        return self.local_dirs

    def list_local_files(self):
        return self.local_files

    def check_file(self, local_name, url):
        if not self._file_exists(local_name):
            raise DistillPublishError('File does not exist: {}'.format(
                local_name))
        local_hash = self._get_local_file_hash(local_name)
        remote_hash = self._get_url_hash(url)
        return local_hash == remote_hash

    def final_checks(self):
        pass

    def remote_path(self, local_name):
        return local_name[len(self.source_dir):]

    def account_username(self):
        raise NotImplementedError('account_username must be implemented')

    def account_container(self):
        raise NotImplementedError('account_container must be implemented')

    def authenticate(self):
        raise NotImplementedError('authenticate must be implemented')

    def list_remote_files(self):
        raise NotImplementedError('list_remote_files must be implemented')

    def delete_remote_file(self, remote_name):
        raise NotImplementedError('delete_remote_file must be implemented')

    def compare_file(self, local_name, remote_name):
        raise NotImplementedError('compare_file must be implemented')

    def upload_file(self, local_name, remote_name):
        raise NotImplementedError('upload_file must be implemented')

    def create_remote_dir(self, remote_dir_name):
        raise NotImplementedError('create_remote_dir must be implemented')


def get_backend(engine):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        try:
            backend = __import__(engine, globals(), locals(),
                                 ['backend_class'])
        except ImportError as e:
            err = 'Failed to import backend engine: {} ({})\n'
            sys.stderr.write(err.format(engine, e))
            raise
    module = getattr(backend, 'backend_class')
    if not module:
        raise ImportError('Backend engine has no backend_class attribute')
    return module
