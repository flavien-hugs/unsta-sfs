import logging
from typing import Optional

import boto3
from botocore import exceptions
from fastapi import Depends, status

from src.config import settings
from .error_codes import SfsErrorCodes
from .exception import CustomHTTPException

logging.basicConfig(format="%(message)s", level=logging.INFO)
_log = logging.getLogger(__name__)

_botoclient: Optional[boto3.client] = None


def get_boto_client() -> boto3.client:
    global _botoclient

    if _botoclient is None:
        _log.info("==> Connecting to Minio server...")
        _botoclient = boto3.client(
            "s3",
            endpoint_url=settings.STORAGE_HOST,
            aws_access_key_id=settings.STORAGE_ACCESS_KEY,
            aws_secret_access_key=settings.STORAGE_SECRET_KEY,
            region_name=settings.STORAGE_REGION_NAME,
        )
        try:
            _botoclient.list_buckets()
            _log.info("==> Connected to Minio server successfully !")
        except (exceptions.ClientError, exceptions.BotoCoreError, exceptions.NoCredentialsError) as err:
            _log.error("==> An error occurred while connecting to Minio server.")
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_UNKNOWN_ERROR,
                error_message=err.response.get("Error").get("Message"),
                status_code=err.response.get("ResponseMetadata").get("HTTPStatusCode"),
            ) from err

    return _botoclient


def check_bucket_exists(bucket_name: str, botoclient: boto3.client = Depends(get_boto_client)) -> str:
    """
    Check if bucket name exist
    """

    try:
        botoclient.head_bucket(Bucket=bucket_name)
        _log.warning(f"==> Bucket '{bucket_name}' exists.")
    except (exceptions.ClientError, exceptions.BotoCoreError) as exc:
        error_message = exc.response.get("Error", {}).get("Message", "An error occurred")
        status_code = int(exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", status.HTTP_400_BAD_REQUEST))

        if status_code == status.HTTP_404_NOT_FOUND:
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_INVALID_NAME,
                error_message=f"Bucket '{bucket_name}' does not exist. Please create it first. {error_message}",
                status_code=status.HTTP_404_NOT_FOUND,
            ) from exc
        elif status_code == status.HTTP_403_FORBIDDEN:
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_ACCESS_DENIED,
                error_message=f"Access denied to check the bucket '{bucket_name}'.",
                status_code=status.HTTP_403_FORBIDDEN,
            ) from exc
        else:
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_UNKNOWN_ERROR,
                error_message="An unknown error occurred while checking the bucket.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from exc

    return bucket_name
