from concurrent.futures import ThreadPoolExecutor

from django_distill.errors import DistillPublishError


def publish_dir(backend, stdout, verify=True, parallel_publish=1, ignore_remote_content=False):
    stdout('Authenticating')
    backend.authenticate()
    stdout('Getting file indexes')
    remote_files = set() if ignore_remote_content else backend.list_remote_files()
    local_files = backend.list_local_files()
    to_upload = set()
    to_delete = set()
    local_files_r = set()
    # check local files to upload
    for f in local_files:
        remote_f = backend.remote_path(f)
        local_files_r.add(remote_f)
        if remote_f not in remote_files:
            # local file not present remotely, upload it
            to_upload.add(f)
        else:
            # file is present remotely, check its hash
            if not backend.compare_file(f, remote_f):
                stdout(f'File stale (hash different): {remote_f}')
                to_upload.add(f)
            else:
                stdout(f'File fresh: {remote_f}')
    # check for remote files to delete
    for f in remote_files:
        if f not in local_files_r:
            to_delete.add(f)
    with ThreadPoolExecutor(max_workers=parallel_publish) as executor:
        # upload any new or changed files
        executor.map(lambda f: _publish_file(backend, f, verify, stdout), to_upload)
        # Call any final checks that may be needed by the backend
        stdout('Final checks')
        backend.final_checks()
        # delete any orphan files
        executor.map(lambda f: _delete_file(backend, f, stdout), to_delete)


def _publish_file(backend, f, verify, stdout):
    remote_f = backend.remote_path(f)
    stdout(f'Publishing: {f} -> {remote_f}')
    backend.upload_file(f, backend.remote_path(f))
    if verify:
        url = backend.remote_url(f)
        stdout(f'Verifying: {url}')
        if not backend.check_file(f, url):
            err = f'Remote file {url} failed hash check'
            raise DistillPublishError(err)


def _delete_file(backend, f, stdout):
    stdout(f'Deleting remote: {f}')
    backend.delete_remote_file(f)
