import os
import sys
import warnings
from urllib.parse import urlsplit, urlunsplit, quote_plus
from time import sleep
from base64 import b64decode
from binascii import hexlify


try:
    from azure.storage.blob import BlobServiceClient, ContentSettings
except ImportError:
    name = 'django_distill.backends.azure_storage'
    pipm = 'azure-storage-blob'
    sys.stdout.write('{} backend requires {}:\n'.format(name, pipm))
    sys.stdout.write('$ pip install .[microsoft]{}\n\n'.format(pipm))
    raise


from django_distill.errors import DistillPublishError
from django_distill.backends import BackendBase


class AzureBlobStorateBackend(BackendBase):
    '''
        Publisher for Azure Blob Storage. Implements the BackendBase. Azure
        static websites in containers are relatively slow to make the files
        available via the public URL. To work around this uploaded files
        are cached and then verified in a loop at the end with up to
        RETRY_ATTEMPTS attempts with a delay of SLEEP_BETWEEN_RETRIES seconds
        between each attempt.
    '''

    REQUIRED_OPTIONS = ('ENGINE', 'CONNECTION_STRING')
    RETRY_ATTEMPTS = 30
    SLEEP_BETWEEN_RETRIES = 3

    def account_username(self):
        return

    def account_container(self):
        return '$web'

    def connection_string(self):
        return self.options.get('CONNECTION_STRING', '')

    def _get_blob(self, name):
        return self.d['connection'].get_blob_client(
            container=self.account_container(),
            blob=name
        )

    def _get_blob_url(self, blob):
        blob_parts = urlsplit(blob.url)
        prefix = '/{}/'.format(quote_plus(self.account_container()))
        path = blob_parts.path
        if path.startswith(prefix):
            path = path[len(prefix):]
        parts = (self.remote_url_parts.scheme, self.remote_url_parts.netloc,
                 path, None, None)
        return urlunsplit(parts)

    def authenticate(self):
        self.d['connection'] = BlobServiceClient.from_connection_string(
            conn_str=self.connection_string()
        )

    def list_remote_files(self):
        container = self.d['connection'].get_container_client(
            container=self.account_container()
        )
        rtn = set()
        for obj in container.list_blobs():
            rtn.add(obj.name)
        return rtn

    def delete_remote_file(self, remote_name):
        container = self.d['connection'].get_container_client(
            container=self.account_container()
        )
        return container.delete_blob(remote_name)

    def check_file(self, local_name, url):
        # Azure uploads are checked in bulk at the end of the uploads, do
        # nothing here
        return True

    def compare_file(self, local_name, remote_name):
        blob = self._get_blob(remote_name)
        properties = blob.get_blob_properties()
        content_settings = properties.content_settings
        content_md5 = properties.get('content_settings', {}).get('content_md5')
        if not content_md5:
            return False
        local_hash = self._get_local_file_hash(local_name)
        remote_hash = str(hexlify(bytes(content_md5)).decode())
        return local_hash == remote_hash

    def upload_file(self, local_name, remote_name):
        blob = self._get_blob(remote_name)
        mimetype = self.local_file_mimetype(local_name)
        content_settings = ContentSettings(content_type=mimetype)
        with open(local_name, 'rb') as data:
            result = blob.upload_blob(
                data, overwrite=True, content_settings=content_settings)
            if result:
                actual_url = self._get_blob_url(blob)
                self.d.setdefault('azure_uploads_to_check', []).append(
                    (local_name, remote_name, actual_url)
                )
        return result

    def _check_file(self, local_name, actual_url):
        # Azure specific patched check_file with retries to account for Azure
        # being slow
        err = ('Failed to upload local file "{}" blob to Azure container at '
               'URL "{}" not available over the public URL after {} attempts')
        local_hash = self._get_local_file_hash(local_name)
        for i in range(self.RETRY_ATTEMPTS):
            remote_hash = self._get_url_hash(actual_url)
            if not remote_hash:
                sleep(self.SLEEP_BETWEEN_RETRIES)
                continue
            if local_hash == remote_hash:
                return True
        DistillPublishError(err.format(local_name, actual_url, i + 1))

    def final_checks(self):
        # Iterate over any cached files to check and verify they have been
        # uploaded correctly.
        to_check = self.d.setdefault('azure_uploads_to_check', [])
        for (local_name, remote_name, actual_url) in to_check:
            # Verify the upload, this may require retries
            self._check_file(local_name, actual_url)
        # If we reached here no DistillPublishError was raised
        return True

    def create_remote_dir(self, remote_dir_name):
        # not required for Azure Blob Storage containers
        return True


backend_class = AzureBlobStorateBackend
