from storages.backends.s3boto3 import S3Boto3Storage


class PublicMediaStorage(S3Boto3Storage):
    location = "public"
    querystring_auth = False
    default_acl = "public-read"


class PrivateMediaStorage(S3Boto3Storage):
    location = "private"
    querystring_auth = True
    custom_domain = False
