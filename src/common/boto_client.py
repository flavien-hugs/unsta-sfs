from typing import Optional

import boto3
from botocore import exceptions
from starlette import status

from src.config import settings
from .error_codes import SfsErrorCodes
from .exception import CustomHTTPException


class BotoClient:

    def __init__(self):
        self.endpoint_url = settings.STORAGE_HOST
        self.aws_access_key_id = settings.STORAGE_ACCESS_KEY
        self.aws_secret_access_key = settings.STORAGE_SECRET_KEY
        self.region_name = settings.STORAGE_REGION_NAME

        self.botoclient: Optional[boto3.client] = None

    def __call__(self, *args, **kwargs) -> boto3.client:
        if self._botoclient is None:
            try:
                self._botoclient = boto3.client(
                    "s3",
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.region_name,
                )
            except exceptions.ClientError as err:
                error_message = err.response.get("Error", {}).get("Message", "An error occurred")
                status_code = err.response.get("ResponseMetadata", {}).get("HTTPStatusCode", status.HTTP_400_BAD_REQUEST)

                raise CustomHTTPException(
                    error_code=SfsErrorCodes.SFS_INVALID_KEY,
                    error_message=error_message,
                    status_code=status_code,
                ) from err

        return self.botoclient

    @property
    def client(self):
        return self()

    def check_bucket_exist(self, bucket_name: str) -> list:
        """
        Check if bucket name exist

        :param bucket_name:
        :type bucket_name: str
        :return:
        :rtype:
        """

        bucket_names = [b["Name"] for b in self.botoclient.list_buckets()["Buckets"]]
        if bucket_name not in bucket_names:
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_INVALID_NAME,
                error_message=f"Bucket '{bucket_name}' not found",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return bucket_names


botoclient = BotoClient()
