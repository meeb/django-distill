import os
import warnings
from binascii import hexlify
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from hashlib import md5
from http.client import HTTPConnection, HTTPSConnection
from importlib import import_module
from logging import getLogger
from sys import stderr
from types import ModuleType
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings

from django_distill.errors import DistillPublishError
from django_distill.static import filter_static_dirs
from django_distill.utils import Path, guess_filepath_type

log = getLogger("main")


def check_publisher_dependencies(
    required_by: str, module_name: str, package_name: str | None = None
) -> ModuleType:
    try:
        return import_module(module_name, package_name)
    except ImportError:
        stderr.write(
            f'Distill site backend "{required_by}" requires module "{module_name}" to be installed'
        )
        raise


def get_publisher(engine_name: str) -> ModuleType:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return import_module(engine_name, "backend_class")
        except ImportError as e:
            stderr.write(
                f'Distill site backend "{engine_name}" not found or failed to import: {e}'
            )
            raise


def get_publisher_from_options(options: dict) -> ModuleType:
    engine_name = options.get("ENGINE", "")
    if not engine_name:
        raise DistillPublishError(
            "Distill site publishing target does not have an ENGINE defined"
        )
    return get_publisher(engine_name)


def get_publishing_targets() -> dict:
    return getattr(settings, "DISTILL_PUBLISH", {})


def get_publishing_target(target_name: str) -> dict:
    try:
        return get_publishing_targets()[target_name]
    except KeyError:
        raise DistillPublishError(
            f'Distill stite publishing target "{target_name}" not defined, '
            f"check your settings.DISTILL_PUBLISH"
        )


class PublisherBackendBase:
    """Generic base class for all backends, mostly an interface / template."""

    REQUIRED_OPTIONS = ("PUBLIC_URL",)
    HTTP_TIMEOUT = 10

    def __init__(self, source_dir: Path | str, options: dict) -> None:
        if isinstance(source_dir, str):
            source_dir = Path(source_dir)
        if not isinstance(source_dir, Path):
            raise DistillPublishError(
                f"Publishing source directory must be a str or Path, got: {type(source_dir)}"
            )
        if not source_dir.is_dir():
            raise DistillPublishError(
                f"Publishing source directory does not exist: {source_dir}"
            )
        self.source_dir = source_dir
        self.options = options
        self.local_files = set()
        self.local_dirs = set()
        self.remote_files = set()
        self.remote_url_parts = urlsplit(options.get("PUBLIC_URL", ""))
        self.d = {}
        self._authenticated = False
        self.validate_options()

    def validate_options(self) -> None:
        for o in self.REQUIRED_OPTIONS:
            if o not in self.options:
                raise DistillPublishError(
                    f"Missing required settings value for the specified "
                    f"distilled site publishing backend: {o}"
                )

    def index_local_files(self) -> None:
        for root, dirs, files in self.source_dir.walk():
            dirs[:] = filter_static_dirs(dirs)
            for d in dirs:
                self.local_dirs.add(root / d)
            for f in files:
                self.local_files.add(root / f)

    def get_local_file_hash(
        self,
        file_path: Path | str,
        digest_func: Callable[[bytes], Any] = md5,
        chunk: int = 1048576,
    ) -> bool | str:
        if not self.file_exists(file_path):
            raise DistillPublishError(
                f"Local distilled site file does not exist: {file_path}"
            )
        # md5 is used by Amazon S3 and Google Storage
        digest = digest_func(b"")
        with open(file_path, "rb") as f:
            while True:
                data = f.read(chunk)
                if not data:
                    break
                digest.update(data)
        return digest.hexdigest()

    def get_url_hash(
        self, url: str, digest_func: Callable[[bytes], Any] = md5, chunk: int = 4096
    ) -> bool | str:
        # CDN cache buster
        url += "?" + hexlify(os.urandom(16)).decode("utf-8")
        url_parts = urlsplit(url)
        protocol = url_parts.scheme.strip().lower()
        if protocol == "http":
            http_connector, http_port = HTTPConnection, 80
        elif protocol == "https":
            http_connector, http_port = HTTPSConnection, 443
        else:
            raise DistillPublishError(f'Unsupported URL protocol "{protocol}"')
        connection = http_connector(url, http_port, self.HTTP_TIMEOUT)
        connection.request("GET", url_parts.path, headers={"Host": url_parts.netloc})
        response = connection.getresponse()
        if response.status == 404:
            return False
        digest = digest_func(b"")
        while block := response.read(chunk):
            if block:
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def file_exists(file_path: Path | str) -> bool:
        if isinstance(file_path, str):
            file_path = Path(file_path)
        if not isinstance(file_path, Path):
            raise DistillPublishError(
                f"File path must be a str or Path, got: {type(file_path)}"
            )
        return file_path.is_file()

    @staticmethod
    def detect_local_file_mimetype(
        local_name: Path | str, default_mimetype: str = "application/octet-stream"
    ) -> str:
        if isinstance(local_name, str):
            local_name = Path(local_name)
        try:
            mimetype = guess_filepath_type(local_name)[0]
        except Exception as e:
            raise DistillPublishError(
                f"Failed to guess mimetype for {local_name}: {e}"
            ) from e
        return mimetype if mimetype is not None else default_mimetype

    def generate_remote_url(self, local_name: Path | str):
        if isinstance(local_name, str):
            local_name = Path(local_name)
        if not isinstance(local_name, Path):
            raise DistillPublishError(
                f"File path must be a str or Path, got: {type(local_name)}"
            )
        if not local_name.is_relative_to(self.source_dir):
            raise DistillPublishError(
                f'Local distilled site file "{local_name}" is not '
                f'in source dir "{self.source_dir}"'
            )
        remote_path_prefix = self.remote_url_parts.path
        remote_path_prefix = remote_path_prefix.removeprefix("/")
        remote_uri = remote_path_prefix + self.remote_path(local_name)
        return urlunsplit(
            (
                self.remote_url_parts.scheme,
                self.remote_url_parts.netloc,
                remote_uri,
                "",
                "",
            )
        )

    def get_local_dirs(self) -> set[str]:
        return self.local_dirs

    def get_local_files(self) -> set[str]:
        return self.local_files

    def check_file(self, local_name: Path | str, url: str) -> bool:
        if not self.file_exists(local_name):
            raise DistillPublishError(
                f"Local distilled site file does not exist: {local_name}"
            )
        local_hash = self.get_local_file_hash(local_name)
        remote_hash = self.get_url_hash(url)
        return local_hash == remote_hash

    def final_checks(self) -> None:
        pass

    def remote_path(self, local_name: Path | str) -> str:
        if isinstance(local_name, str):
            local_name = Path(local_name)
        remote_path = Path("/") / local_name.relative_to(self.source_dir)
        return str(remote_path).replace(os.sep, "/")

    def publish(
        self,
        verify: bool = True,
        ignore_remote_content: bool = False,
        concurrency: int = 1,
    ) -> bool:
        """Performs a full synchronisation of a local directory of files with a remote publishing target."""
        if not self._authenticated:
            raise DistillPublishError(
                "Not authenticated, please call authenticate() before publishing"
            )
        self.index_local_files()
        local_files = self.get_local_files()
        remote_files = set() if ignore_remote_content else self.list_remote_files()
        local_files_remote_names = set()
        to_upload = set()
        to_delete = set()
        # Check local files to upload
        for local_file in local_files:
            remote_file = self.remote_path(local_file)
            local_files_remote_names.add(remote_file)
            if remote_file not in remote_files:
                # Local file is not present remotely, queue it to be uploaded
                to_upload.add(local_file)
            else:
                # File is present remotely, check its hash
                if not self.compare_file(local_file, remote_file):
                    log.info(f"File stale (hash different): {remote_file}")
                    # Remote file hash is different, queue it to be re-uploaded
                    to_upload.add(local_file)
                else:
                    log.debug(f"File fresh (hash matches): {remote_file}")
        # Check for remote files to delete
        for remote_file in remote_files:
            if remote_file not in local_files_remote_names:
                # Remote file is not present locally, queue it to be deleted
                to_delete.add(remote_file)

        def _publish_local_file(_local_file: Path) -> bool:
            _remote_file = self.remote_path(_local_file)
            log.info(f"Publishing: {_local_file} to {_remote_file}")
            self.upload_file(_local_file, _remote_file, verify=verify)
            if verify:
                url = self.generate_remote_url(_local_file)
                log.info(f"Verifying: {url}")
                if not self.check_file(_local_file, url):
                    raise DistillPublishError(f"Remote file failed hash check: {url}")
            return True

        def _delete_remote_file(_remote_file: str) -> bool:
            log.info(f"Deleting: {_remote_file}")
            self.delete_remote_file(_remote_file)
            return True

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            # upload any new or changed files
            executor.map(lambda f: _publish_local_file(f), to_upload)
            # Call any final checks that may be needed by the backend
            self.final_checks()
            # delete any orphan files
            executor.map(lambda f: _delete_remote_file(f), to_delete)

        return True

    def account_username(self) -> str:
        raise NotImplementedError("account_username() must be implemented")

    def account_container(self) -> str:
        raise NotImplementedError("account_container() must be implemented")

    def authenticate(self) -> bool:
        raise NotImplementedError("authenticate() must be implemented")

    def list_remote_files(self) -> set[str]:
        raise NotImplementedError("list_remote_files() must be implemented")

    def delete_remote_file(self, remote_name: str) -> bool:
        raise NotImplementedError("delete_remote_file() must be implemented")

    def compare_file(self, local_name: Path | str, remote_name: str) -> bool:
        raise NotImplementedError("compare_file() must be implemented")

    def upload_file(
        self, local_name: Path | str, remote_name: str, verify: bool = True
    ) -> bool:
        raise NotImplementedError("upload_file() must be implemented")

    def create_remote_dir(self, remote_dir_name: str) -> bool:
        raise NotImplementedError("create_remote_dir() must be implemented")
