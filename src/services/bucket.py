import boto3
from botocore import exceptions
from fastapi import Depends, status

from src.common.boto_client import check_bucket_exists, get_boto_client
from src.common.error_codes import SfsErrorCodes
from src.common.exception import CustomHTTPException
from src.common.functional import format_bucket
from src.common.utils import policy_document
from src.config import settings
from src.models import Bucket, Media
from src.schemas import BucketSchema


async def create_new_bucket(bucket: BucketSchema, botoclient: boto3.client = Depends(get_boto_client)):
    """
    Create a new bucket in S3 and MongoDB if it doesn't exist.

    :param bucket: BucketSchema object to be created
    :param botoclient: boto3.client object to interact with S3
    :return: Created Bucket object
    """

    bucket_name = format_bucket(bucket.bucket_name)

    try:
        botoclient.head_bucket(Bucket=bucket_name)
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_BUCKET_NAME_ALREADY_EXIST,
            error_message=f"Bucket '{bucket_name}' already exists.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except (exceptions.ClientError, exceptions.BotoCoreError) as exc:
        error_code = status_code = int(exc.response["Error"]["Code"])

        if error_code == status.HTTP_404_NOT_FOUND:
            try:
                location = {"LocationConstraint": settings.STORAGE_REGION_NAME}
                botoclient.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)

                botoclient.put_bucket_policy(Bucket=bucket_name, Policy=policy_document)

                new_doc_bucket = await Bucket(bucket_slug=bucket_name, **bucket.model_dump()).create()

                return new_doc_bucket
            except (exceptions.ClientError, exceptions.BotoCoreError) as exc:
                error_message = exc.response.get("Error", {}).get("Message", "An error occurred")
                status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", status.HTTP_400_BAD_REQUEST)
                raise CustomHTTPException(
                    error_code=SfsErrorCodes.SFS_BUCKET_NAME_ALREADY_EXIST, error_message=error_message, status_code=status_code
                ) from exc
        else:
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_INVALID_NAME,
                error_message=f"Error checking bucket: {str(exc)}",
                status_code=status.HTTP_400_BAD_REQUEST,
            ) from exc


async def get_or_create_bucket(
    bucket_name: str = Depends(format_bucket),
    create_bucket_if_not_exist: bool = False,
    botoclient: boto3.client = Depends(get_boto_client),
) -> Bucket:
    """
    Get a bucket from MongoDB

    :param bucket_name: The bucket name to get
    :type bucket_name: str
    :param create_bucket_if_not_exist: Create the bucket if it doesn't exist
    :type create_bucket_if_not_exist: bool
    :param botoclient: boto3.client object to interact with S3
    :type botoclient: boto3.client
    :return: The bucket object
    :rtype: Bucket
    """

    if not await Bucket.find_one({"bucket_slug": bucket_name}).exists():
        if create_bucket_if_not_exist:
            return await create_new_bucket(bucket=BucketSchema(bucket_name=bucket_name), botoclient=botoclient)
        else:
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_BUCKET_NOT_FOUND,
                error_message=f"Bucket '{bucket_name}' not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

    if create_bucket_if_not_exist:
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_BUCKET_NAME_ALREADY_EXIST,
            error_message=f"Bucket '{bucket_name}' already exists.",
            status_code=status.HTTP_409_CONFLICT,
        )


async def delete_bucket(
    bucket_name: str = list[Depends(format_bucket), Depends(check_bucket_exists)],
    botoclient: boto3.client = Depends(get_boto_client),
) -> None:
    """
    Deletes an S3 bucket and associated records in MongoDB.

    :param bucket_name: The bucket name to delete
    :param botoclient: boto3.client object to interact with S3
    """
    try:
        # Retrieve all items from the bucket
        paginator = botoclient.get_paginator("list_objects_v2")

        # Prepare batch of 1000 objects for removal
        delete_dictionary = {"Objects": [], "Quiet": True}

        # Browse all bucket items
        for page in paginator.paginate(Bucket=bucket_name):
            if "Contents" in page:
                for obj in page["Contents"]:
                    delete_dictionary["Objects"].append({"Key": obj["Key"]})

                    # When we reach 1000 objects, we delete them
                    if len(delete_dictionary["Objects"]) >= 1000:
                        botoclient.delete_objects(Bucket=bucket_name, Delete=delete_dictionary)
                        delete_dictionary["Objects"] = []
            else:
                break

        # Delete remaining objects
        if delete_dictionary["Objects"]:
            botoclient.delete_objects(Bucket=bucket_name, Delete=delete_dictionary)

        # Delete MongoDB bucket and records
        botoclient.delete_bucket(Bucket=bucket_name)
        await Media.find({"bucket_name": bucket_name}).delete_many()
        await Bucket.find_one({"bucket_name": bucket_name}).delete()

    except (exceptions.ClientError, exceptions.BotoCoreError) as exc:
        error_message = exc.response.get("Error", {}).get("Message", "An error occurred")
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_NAME, error_message=error_message, status_code=status.HTTP_400_BAD_REQUEST
        ) from exc
