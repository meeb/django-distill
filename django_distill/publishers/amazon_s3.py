from django_distill.publisher import PublisherBackendBase, check_publisher_dependencies
from django_distill.utils import Path

boto3 = check_publisher_dependencies("django_distill.publishers.amazon_s3", "boto3")


class AmazonS3Backend(PublisherBackendBase):
    """Publisher for Amazon S3."""

    REQUIRED_OPTIONS = ("ENGINE", "PUBLIC_URL", "BUCKET")

    def get_object(self, name: str) -> dict:
        bucket = self.account_container()
        return self.d["connection"].head_object(Bucket=bucket, Key=name)

    def account_username(self) -> str:
        return self.options.get("ACCESS_KEY_ID", "")

    def account_container(self) -> str:
        return self.options.get("BUCKET", "")

    def authenticate(
        self,
    ) -> bool:
        access_key_id = self.account_username()
        secret_access_key = self.options.get("SECRET_ACCESS_KEY", "")
        endpoint_url = self.options.get("ENDPOINT_URL", None)
        bucket = self.account_container()
        if access_key_id and secret_access_key:
            self.d["connection"] = boto3.client(
                "s3",
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                endpoint_url=endpoint_url,
            )
        else:
            self.d["connection"] = boto3.client("s3")
        self.d["bucket"] = bucket
        self._authenticated = True
        return True

    def get_remote_files(self) -> set[str]:
        rtn = set()
        response = self.d["connection"].list_objects_v2(Bucket=self.d["bucket"])
        if "Contents" in response:
            for obj in response["Contents"]:
                rtn.add(obj["Key"])
        return rtn

    def delete_remote_file(self, remote_name: str) -> bool:
        self.d["connection"].delete_object(Bucket=self.d["bucket"], Key=remote_name)
        return True

    def compare_file(self, local_name: Path | str, remote_name: str) -> bool:
        obj = self.get_object(remote_name)
        local_hash = self.get_local_file_hash(local_name)
        return local_hash == obj["ETag"][1:-1]

    def upload_file(
        self, local_name: Path | str, remote_name: str, verify: bool = True
    ) -> bool:
        default_content_type = self.options.get(
            "DEFAULT_CONTENT_TYPE", "application/octet-stream"
        )
        content_type = self.detect_local_file_mimetype(local_name, default_content_type)
        extra_args = {"ContentType": content_type}
        self.d["connection"].upload_file(
            local_name, self.d["bucket"], remote_name, ExtraArgs=extra_args
        )
        return True

    def create_remote_dir(self, remote_dir_name: str) -> bool:
        # not required for S3 buckets
        return True


backend_class = AmazonS3Backend
