from storages.backends.s3boto3 import S3Boto3Storage


class PublicMediaStorage(S3Boto3Storage):
    location = "public"
    querystring_auth = False
    default_acl = "public-read"


class PrivateMediaStorage(S3Boto3Storage):
    location = "private"
    querystring_auth = True
    custom_domain = False

    def generate_presigned_put_url(self, name, expiration=900):
        s3_key = self._normalize_name(name)
        s3_client = self.connection.meta.client

        return s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": s3_key,
                "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
            ExpiresIn=expiration,
            HttpMethod="PUT",
        )
