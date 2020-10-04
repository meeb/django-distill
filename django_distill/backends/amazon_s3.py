import sys


try:
    import boto3
except ImportError:
    name = 'django_distill.backends.amazon_s3'
    pipm = 'boto3'
    sys.stdout.write('{} backend requires {}:\n'.format(name, pipm))
    sys.stdout.write('$ pip install {}\n\n'.format(pipm))
    raise


from django_distill.errors import DistillPublishError
from django_distill.backends import BackendBase


class AmazonS3Backend(BackendBase):
    '''
        Publisher for Amazon S3. Implements the BackendBase.
    '''

    REQUIRED_OPTIONS = ('ENGINE', 'PUBLIC_URL', 'ACCESS_KEY_ID',
                        'SECRET_ACCESS_KEY', 'BUCKET')

    def _get_object(self, name):
        bucket = self.account_container()
        return self.d['connection'].get_object(Bucket=bucket, Key=name)

    def account_username(self):
        return self.options.get('ACCESS_KEY_ID', '')

    def account_container(self):
        return self.options.get('BUCKET', '')

    def authenticate(self, calling_format=None):
        access_key_id = self.account_username()
        secret_access_key = self.options.get('SECRET_ACCESS_KEY', '')
        bucket = self.account_container()
        self.d['connection'] = boto3.client('s3', aws_access_key_id=access_key_id,
                                            aws_secret_access_key=secret_access_key)
        self.d['bucket'] = self.d['connection'].get_bucket(bucket)

    def list_remote_files(self):
        rtn = set()
        for obj in self.d['bucket'].objects.all():
            rtn.add(obj.key)
        return rtn

    def delete_remote_file(self, remote_name):
        obj = self._get_object(remote_name)
        return obj.delete()

    def compare_file(self, local_name, remote_name):
        obj = self._get_object(remote_name)
        local_hash = self._get_local_file_hash(local_name)
        return local_hash == obj.e_tag[1:-1]

    def upload_file(self, local_name, remote_name):
        return self.d['bucket'].upload_file(local_name, remote_name)

    def create_remote_dir(self, remote_dir_name):
        # not required for S3 buckets
        return True


backend_class = AmazonS3Backend
