from binascii import hexlify
from pathlib import Path
from time import sleep
from urllib.parse import quote_plus, urlsplit, urlunsplit

from django_distill.errors import DistillPublishError
from django_distill.publisher import PublisherBackendBase, check_publisher_dependencies

BlobServiceClient = check_publisher_dependencies(
    "django_distill.backends.azure_storage", "azure.storage.blob", "BlobServiceClient"
)
BlobClient = check_publisher_dependencies(
    "django_distill.backends.azure_storage", "azure.storage.blob", "BlobClient"
)
ContentSettings = check_publisher_dependencies(
    "django_distill.backends.azure_storage", "azure.storage.blob", "ContentSettings"
)


class AzureBlobStorateBackend(PublisherBackendBase):
    """Publisher for Azure Blob Storage. Azure static websites in containers are relatively
    slow to make the files available via the public URL. To work around this, uploaded files are
    cached and then verified in a loop at the end with up to RETRY_ATTEMPTS attempts with a delay of
    SLEEP_BETWEEN_RETRIES seconds between each attempt."""

    REQUIRED_OPTIONS = ("ENGINE", "CONNECTION_STRING")
    RETRY_ATTEMPTS = 30
    SLEEP_BETWEEN_RETRIES = 3

    def account_username(self) -> str:
        return ""

    def account_container(self) -> str:
        """Azure Blob Storage containers are all named $web for public websites."""
        return "$web"

    def connection_string(self) -> str:
        return self.options.get("CONNECTION_STRING", "")

    def get_container(self):
        return self.d["connection"].get_container_client(
            container=self.account_container()
        )

    def get_blob(self, name: str) -> BlobClient:
        return self.d["connection"].get_blob_client(
            container=self.account_container(), blob=name
        )

    def get_blob_url(self, blob: BlobClient) -> str:
        blob_parts = urlsplit(blob.url)
        prefix = f"/{quote_plus(self.account_container())}/"
        path = blob_parts.path
        path = path.removeprefix(prefix)
        parts = (
            self.remote_url_parts.scheme,
            self.remote_url_parts.netloc,
            path,
            None,
            None,
        )
        return urlunsplit(parts).decode("utf-8")

    def authenticate(self) -> bool:
        self.d["connection"] = BlobServiceClient.from_connection_string(
            conn_str=self.connection_string()
        )
        self._authenticated = True
        return True

    def get_remote_files(self) -> set[str]:
        container = self.get_container()
        rtn = set()
        for obj in container.list_blobs():
            rtn.add(obj.name)
        return rtn

    def delete_remote_file(self, remote_name: str) -> bool:
        container = self.get_container()
        return container.delete_blob(remote_name)

    def check_file(self, local_name: Path | str, url: str) -> bool:
        # Azure uploads are checked in bulk at the end of the uploads, do nothing here
        return True

    def compare_file(self, local_name: Path | str, remote_name: str) -> bool:
        blob = self.get_blob(remote_name)
        properties = blob.get_blob_properties()
        content_md5 = properties.get("content_settings", {}).get("content_md5")
        if not content_md5:
            return False
        local_hash = self.get_local_file_hash(local_name)
        remote_hash = str(hexlify(bytes(content_md5)).decode())
        return local_hash == remote_hash

    def upload_file(
        self, local_name: Path | str, remote_name: str, verify: bool = True
    ) -> bool:
        blob = self.get_blob(remote_name)
        mimetype = self.detect_local_file_mimetype(local_name)
        content_settings = ContentSettings(content_type=mimetype)
        with open(local_name, "rb") as data:
            result = blob.upload_blob(
                data, overwrite=True, content_settings=content_settings
            )
            if result:
                actual_url = self.get_blob_url(blob)
                self.d.setdefault("azure_uploads_to_check", []).append(
                    (local_name, remote_name, actual_url)
                )
        return result

    def _check_file(self, local_name: Path | str, actual_url: str) -> bool:
        # Azure specific patched check_file with retries to account for Azure being slow
        local_hash = self.get_local_file_hash(local_name)
        i: int = 0
        for i in range(self.RETRY_ATTEMPTS):
            remote_hash = self.get_url_hash(actual_url)
            if not remote_hash:
                sleep(self.SLEEP_BETWEEN_RETRIES)
                continue
            if local_hash == remote_hash:
                return True
        raise DistillPublishError(
            f'Failed to upload local file "{local_name}" blob to Azure container at '
            f'URL "{actual_url}" not available over the public URL after {i + 1} attempts'
        )

    def final_checks(self) -> None:
        # Iterate over any cached files to check and verify they have been uploaded correctly.
        to_check = self.d.setdefault("azure_uploads_to_check", [])
        for local_name, remote_name, actual_url in to_check:
            # Verify the upload, this may require retries
            self.check_file(local_name, actual_url)
        # If we reached here, no StaticSitePublishError was raised

    def create_remote_dir(self, remote_dir_name: str) -> bool:
        # not required for Azure Blob Storage containers
        return True


backend_class = AzureBlobStorateBackend
