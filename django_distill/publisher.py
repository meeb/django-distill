# -*- coding: utf-8 -*-


from django_distill.errors import DistillPublishError


def publish_dir(local_dir, backend, stdout):
    stdout('Authenticating')
    backend.authenticate()
    stdout('Getting file indexes')
    remote_files = backend.list_remote_files()
    local_files = backend.list_local_files()
    local_dirs = backend.list_local_dirs()
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
                stdout('File stale (hash different): {}'.format(remote_f))
                to_upload.add(f)
            else:
                stdout('File fresh: {}'.format(remote_f))
    # check for remote files to delete
    for f in remote_files:
        if f not in local_files_r:
            to_delete.add(f)
    # upload any new or changed files
    for f in to_upload:
        remote_f = backend.remote_path(f)
        stdout('Publishing: {} -> {}'.format(f, remote_f))
        backend.upload_file(f, backend.remote_path(f))
        url = backend.remote_url(f)
        stdout('Verifying: {}'.format(url))
        if not backend.check_file(f, url):
            err = 'Remote file {} failed hash check'
            raise DistillPublishError(err.format(url))
    # delete any orphan files
    for f in to_delete:
        stdout('Deleting remote: {}'.format(f))
        backend.delete_remote_file(f)


# eof
