import os
from base64 import b64decode
from binascii import hexlify

from django_distill.errors import DistillPublishError
from django_distill.publisher import PublisherBackendBase, check_publisher_dependencies
from django_distill.utils import Path

discovery = check_publisher_dependencies(
    "django_distill.backends.google_storage",
    "googleapiclientgoogleapiclient",
    "discovery",
)
storage = check_publisher_dependencies(
    "django_distill.backends.google_storage", "google.cloud", "storage"
)


class GoogleCloudStorageBackend(PublisherBackendBase):
    """Publisher for Google Cloud Storage."""

    REQUIRED_OPTIONS = ("ENGINE", "BUCKET")

    def account_username(self) -> str:
        return ""

    def account_container(self) -> str:
        return self.options.get("BUCKET", "")

    def authenticate(self) -> bool:
        credentials_file = self.options.get("JSON_CREDENTIALS", "")
        if credentials_file:
            credentials_path = Path(credentials_file)
            if not credentials_path.is_file():
                raise DistillPublishError(
                    f"Distill site backend for Google Cloud Storage "
                    f"credentials file does not exist: {credentials_path}"
                )
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_file
        bucket = self.account_container()
        self.d["connection"] = storage.Client()
        self.d["bucket"] = self.d["connection"].get_bucket(bucket)
        self._authenticated = True
        return True

    def get_remote_files(self) -> set[str]:
        rtn = set()
        for b in self.d["bucket"].list_blobs():
            rtn.add(b.name)
        return rtn

    def delete_remote_file(self, remote_name: str) -> bool:
        b = self.d["bucket"].get_blob(remote_name)
        return b.delete()

    def compare_file(self, local_name: Path | str, remote_name: str) -> bool:
        b = self.d["bucket"].get_blob(remote_name)
        local_hash = self.get_local_file_hash(local_name)
        remote_hash = str(hexlify(b64decode(b.md5_hash)).decode())
        return local_hash == remote_hash

    def upload_file(
        self, local_name: Path | str, remote_name: str, verify: bool = True
    ) -> bool:
        b = self.d["bucket"].blob(remote_name)
        b.upload_from_filename(local_name)
        b.make_public()
        return True

    def create_remote_dir(self, remote_dir_name: str) -> bool:
        # not required for Google Storage buckets
        return True

    def remote_path(self, local_name: Path | str) -> str:
        truncated_path = super().remote_path(local_name)
        # Replace \ for /, Google Cloud Files API docs state they handle both \ and /
        # as directory separators but really make sure we're only using / in blob names
        return truncated_path.replace("\\", "/")


backend_class = GoogleCloudStorageBackend
