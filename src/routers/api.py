import os
import tempfile

import boto3
from botocore import exceptions
from fastapi import APIRouter, Depends, File, status, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi_pagination import paginate
from slugify import slugify

from src.common.boto_client import BotoClient
from src.common.error_codes import SfsErrorCodes
from src.common.exception import CustomHTTPException
from src.common.functional import customize_page
from src.config import settings

sfs_router: APIRouter = APIRouter(
    prefix="/storages",
    tags=["STORAGES"],
    responses={404: {"description": "Not found"}},
)


def _get_error(err):
    error_message = err.response.get("Error", {}).get("Message", "An error occurred")
    status_code = err.response.get("ResponseMetadata", {}).get("HTTPStatusCode", status.HTTP_400_BAD_REQUEST)

    raise CustomHTTPException(
        error_code=SfsErrorCodes.SFS_INVALID_KEY, error_message=error_message, status_code=status_code
    ) from err


@sfs_router.get("", response_model=customize_page(dict), summary="List all buckets", status_code=status.HTTP_200_OK)
def list_bucket(boto: boto3.client = Depends(BotoClient)):
    buckets_list = boto.client.list_buckets()
    buckets = buckets_list.get("Buckets", [])
    return paginate([bucket for bucket in buckets])


@sfs_router.post("", summary="Create a bucket", status_code=status.HTTP_201_CREATED)
def create_bucket(bucket_name: str, boto: boto3.client = Depends(BotoClient)):
    try:
        bucket_name = slugify(bucket_name)
        location = {"LocationConstraint": settings.STORAGE_REGION_NAME}
        boto.client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
        response = {"message": f"Bucket '{bucket_name}' created successfully."}
    except exceptions.ClientError as err:
        return _get_error(err)

    return JSONResponse(content=response, status_code=status.HTTP_201_CREATED)


@sfs_router.get(
    "/{bucket_name}",
    response_model=customize_page(str),
    summary="List all files in a bucket",
    status_code=status.HTTP_200_OK
)
def list_files(bucket_name: str, boto: boto3.client = Depends(BotoClient)):
    bucket_name = slugify(bucket_name)
    bucket_contents = boto.client.list_objects(Bucket=bucket_name).get("Contents", [])
    data = [file.get("Key") for file in bucket_contents]
    return paginate(data)


@sfs_router.put(
    "/{bucket_name}",
    dependencies=[Depends(BotoClient.check_bucket_exist)],
    summary="Upload a file to a bucket",
    status_code=status.HTTP_201_CREATED,
)
def upload_file(bucket_name: str, file: UploadFile = File(...), boto: boto3.client = Depends(BotoClient)):
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file.file.read())

        boto.client.upload_file(Filename=temp_file.file, Bucket=bucket_name, Keyword=file.filename)
        os.remove(temp_file.name)

        response = {"filename": file.filename, "type": file.content_type}
    except exceptions.ClientError as err:
        return _get_error(err)

    return JSONResponse(content=response, status_code=status.HTTP_201_CREATED)


@sfs_router.get("/{bucket_name}/{filename}", summary="Get a file from a bucket", status_code=status.HTTP_200_OK)
def get_file(bucket_name: str, filename: str, boto: boto3.client = Depends(BotoClient)):
    bucket_name = slugify(bucket_name)
    try:
        boto.client.download_file(Bucket=bucket_name, Filename=filename, Key=filename)
        head_object = boto.client.head_object(Bucket=bucket_name, Key=filename)
        content_type = head_object["ContentType"]

        with open(file=filename, mode="rb") as file:
            file_content = file.read()

        response = Response(
            content=file_content,
            status_code=status.HTTP_200_OK,
            headers={"Content-Type": content_type}
        )
    except exceptions.ClientError as err:
        return _get_error(err)

    return response


@sfs_router.delete(
    "/{bucket_name}/{filename}",
    summary="Delete a file from a bucket",
    status_code=status.HTTP_200_OK
)
def delete_file(bucket_name: str, filename: str, boto: boto3.client = Depends(BotoClient)):
    bucket_name = slugify(bucket_name)
    try:
        boto.client.delete_object(Bucket=bucket_name, Key=filename)
        response = {"message": f"File '{filename}' deleted successfully."}
    except exceptions.ClientError as err:
        return _get_error(err)

    return JSONResponse(content=response, status_code=status.HTTP_200_OK)
