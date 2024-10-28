import re
from typing import Optional

import boto3
from botocore import exceptions
from fastapi import Depends, status
from urllib import parse
from src.config import settings
from .error_codes import SfsErrorCodes
from .exception import CustomHTTPException

_boto_client: Optional[boto3.client] = None


def get_boto_client() -> boto3.client:
    global _boto_client

    if _boto_client is None:
        try:
            _boto_client = boto3.client(
                "s3",
                endpoint_url=settings.STORAGE_HOST,
                aws_access_key_id=settings.STORAGE_ACCESS_KEY,
                aws_secret_access_key=settings.STORAGE_SECRET_KEY,
                region_name=settings.STORAGE_REGION_NAME,
            )
        except (exceptions.ClientError, exceptions.BotoCoreError) as err:
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_UNKNOWN_ERROR,
                error_message=err.response.get("Error").get("Message"),
                status_code=err.response.get("ResponseMetadata").get("HTTPStatusCode"),
            ) from err

    return _boto_client


def replace_minio_url_base(domain: str, url: str) -> str:
    """
    Replace the Minio URL base with the provided domain

    :param domain: The domain to replace the Minio URL base
    :param url: The URL to replace the Minio URL base
    """

    new_url = parse.urlparse(url)
    domain = new_url._replace(netloc=domain)
    return domain.geturl()


def is_valid_bucket_name(bucket_name: str) -> str:
    """
    Format a bucket name to lowercase and limits its length
    """
    formatted = bucket_name.lower()[:63]
    if re.match(settings.APP_BUCKET_NAME_PATTERN, formatted):
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_NAME,
            error_message=f"Bucket name '{bucket_name}' is invalid. "
            f"The bucket name must contain lowercase letters and numbers,"
            f" and be between 3 and 63 characters long.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return bucket_name


def check_bucket_exist(bucket_name: str, boto_client: boto3.client = Depends(get_boto_client)) -> str:
    """
    Check if bucket name exist
    """

    try:
        boto_client.head_bucket(Bucket=bucket_name)
    except (exceptions.ClientError, exceptions.BotoCoreError) as exc:
        error_message = exc.response.get("Error", {}).get("Message", "An error occurred")
        status_code = int(exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", status.HTTP_400_BAD_REQUEST))

        if status_code == status.HTTP_404_NOT_FOUND:
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_INVALID_NAME,
                error_message=error_message,
                status_code=status.HTTP_404_NOT_FOUND,
            ) from exc
        elif status_code == status.HTTP_403_FORBIDDEN:
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_ACCESS_DENIED,
                error_message=error_message,
                status_code=status.HTTP_403_FORBIDDEN,
            ) from exc
        else:
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_UNKNOWN_ERROR,
                error_message="An unknown error occurred while checking the bucket.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from exc

    return bucket_name
