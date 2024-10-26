import re
from typing import Optional

import boto3
from botocore import exceptions
from fastapi import Depends, status

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
        if self.botoclient is None:
            try:
                self.botoclient = boto3.client(
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


def is_valid_bucket_name(bucket_name: str) -> bool:
    try:
        if re.match(settings.APP_BUCKET_NAME_PATTERN, bucket_name):
            return True
    except exceptions.ParamValidationError as exc:
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_KEY,
            error_message=f"Bucket name '{bucket_name}' is invalid."
            f"The bucket name must contain lowercase letters and numbers,"
            f" and be between 3 and 63 characters long.",
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc


def check_bucket_exist(bucket_name: str, boto: boto3.client = Depends(BotoClient)) -> str:
    """
    Check if bucket name exist
    """

    try:
        boto.client.head_bucket(Bucket=bucket_name)
    except exceptions.ClientError as exc:
        error_code = int(exc.response.get("Error", {}).get("Code", 0))
        if error_code == status.HTTP_404_NOT_FOUND:
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_INVALID_NAME,
                error_message=f"Bucket '{bucket_name}' does not exist.",
                status_code=status.HTTP_404_NOT_FOUND,
            ) from exc
        elif error_code == status.HTTP_403_FORBIDDEN:
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_ACCESS_DENIED,
                error_message=f"Access denied to bucket '{bucket_name}'.",
                status_code=status.HTTP_403_FORBIDDEN,
            ) from exc
        else:
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_UNKNOWN_ERROR,
                error_message="An unknown error occurred while checking the bucket.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from exc
    return bucket_name
