import os
import tempfile

import boto3
from botocore import exceptions
from fastapi import APIRouter, Depends, File, status, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi_pagination.async_paginator import paginate

from src.common.boto_client import BotoClient, check_bucket_exist, is_valid_bucket_name
from src.common.error_codes import SfsErrorCodes
from src.common.exception import CustomHTTPException
from src.common.functional import customize_page
from src.config import settings
from src.schemas import BucketSchema

router: APIRouter = APIRouter(
    prefix="/storages",
    tags=["STORAGES"],
    responses={404: {"description": "Not found"}},
)


def _get_error(error_code: str, exc: exceptions.ClientError):
    error_message = exc.response.get("Error", {}).get("Message", "An error occurred")
    status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", status.HTTP_400_BAD_REQUEST)

    raise CustomHTTPException(error_code=error_code, error_message=error_message, status_code=status_code) from exc


@router.get("", response_model=customize_page(BucketSchema), summary="List all buckets", status_code=status.HTTP_200_OK)
async def list_bucket(boto: boto3.client = Depends(BotoClient)):
    buckets_list = boto.client.list_buckets()
    buckets = buckets_list.get("Buckets", [])
    return await paginate([BucketSchema(name=bucket["Name"], created_at=bucket["CreationDate"]) for bucket in buckets])


@router.post("", dependencies=[Depends(is_valid_bucket_name)], summary="Create a bucket", status_code=status.HTTP_201_CREATED)
def create_bucket(bucket_name: str, boto: boto3.client = Depends(BotoClient)):
    try:
        location = {"LocationConstraint": settings.STORAGE_REGION_NAME}
        boto.client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
    except exceptions.ClientError as exc:
        return _get_error(error_code=SfsErrorCodes.SFS_INVALID_DATA, exc=exc)

    return JSONResponse(
        content={"message": f"Bucket '{bucket_name}' created successfully."}, status_code=status.HTTP_201_CREATED
    )


@router.get(
    "/{bucket_name}", response_model=customize_page(str), summary="List all files in a bucket", status_code=status.HTTP_200_OK
)
async def list_files(bucket_name: str, boto: boto3.client = Depends(BotoClient)):
    try:
        bucket = boto.client.list_objects(Bucket=bucket_name)
    except exceptions.ClientError as exc:
        return _get_error(error_code=SfsErrorCodes.SFS_INVALID_NAME, exc=exc)

    bucket_contents = bucket.get("Contents", [])
    data = [file.get("Key") for file in bucket_contents]
    return await paginate(data)


@router.put(
    "/{bucket_name}",
    dependencies=[Depends(check_bucket_exist)],
    summary="Upload a file to a bucket",
    status_code=status.HTTP_202_ACCEPTED,
)
def upload_file(bucket_name: str, file: UploadFile = File(...), boto: boto3.client = Depends(BotoClient)):
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file.file.read())

        boto.client.upload_file(Filename=temp_file.name, Bucket=bucket_name, Key=file.filename)
        os.remove(temp_file.name)
    except exceptions.ClientError as exc:
        return _get_error(error_code=SfsErrorCodes.SFS_INVALID_FILE, exc=exc)

    response = {"filename": file.filename, "type": file.content_type}
    return JSONResponse(content=response, status_code=status.HTTP_202_ACCEPTED)


@router.get("/{bucket_name}/{filename}", summary="Get a file from a bucket", status_code=status.HTTP_200_OK)
def get_file(bucket_name: str, filename: str, boto: boto3.client = Depends(BotoClient)):
    try:
        boto.client.download_file(Bucket=bucket_name, Filename=filename, Key=filename)
        head_object = boto.client.head_object(Bucket=bucket_name, Key=filename)
        contenttype = head_object["ContentType"]

        with open(file=filename, mode="rb") as file:
            file_content = file.read()

        response = Response(content=file_content, status_code=status.HTTP_200_OK, headers={"Content-Type": contenttype})
    except exceptions.ClientError as exc:
        return _get_error(error_code=SfsErrorCodes.SFS_INVALID_FILE, exc=exc)

    return response


@router.delete("/{bucket_name}/{filename}", summary="Delete a file from a bucket", status_code=status.HTTP_200_OK)
def delete_file(bucket_name: str, filename: str, boto: boto3.client = Depends(BotoClient)):
    try:
        boto.client.delete_object(Bucket=bucket_name, Key=filename)
        response = {"message": f"File '{filename}' deleted successfully."}
    except exceptions.ClientError as exc:
        return _get_error(error_code=SfsErrorCodes.SFS_INVALID_FILE, exc=exc)

    return JSONResponse(content=response, status_code=status.HTTP_200_OK)
