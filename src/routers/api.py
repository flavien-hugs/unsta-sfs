import os
import tempfile

import boto3
from botocore import exceptions
from fastapi import APIRouter, Depends, File, status, UploadFile, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi_pagination import response
from fastapi_pagination.async_paginator import paginate

from src.common.boto_client import check_bucket_exist, get_boto_client, is_valid_bucket_name, replace_minio_url_base
from src.common.error_codes import SfsErrorCodes
from src.common.exception import CustomHTTPException
from src.common.functional import customize_page
from src.config import settings
from src.schemas import BucketSchema

router: APIRouter = APIRouter(
    prefix="/buckets",
    tags=["BUCKETS"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "",
    response_model=customize_page(BucketSchema),
    summary="List all buckets",
    status_code=status.HTTP_200_OK
)
async def list_bucket(boto_client: boto3.client = Depends(get_boto_client)):
    list_buckets = boto_client.list_buckets()
    buckets = list_buckets.get("Buckets", [])
    return await paginate([BucketSchema(name=bucket["Name"], created_at=bucket["CreationDate"]) for bucket in buckets if buckets])


@router.post(
    "",
    dependencies=[Depends(is_valid_bucket_name)],
    summary="Create a bucket",
    status_code=status.HTTP_201_CREATED,
)
def create_bucket(bucket_name: str, boto_client: boto3.client = Depends(get_boto_client)):
    try:
        location = {"LocationConstraint": settings.STORAGE_REGION_NAME}
        boto_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
    except (exceptions.ClientError, exceptions.BotoCoreError) as exc:
        error_message = exc.response.get("Error", {}).get("Message", "An error occurred")
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", status.HTTP_400_BAD_REQUEST)
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_BUCKET_NAME_ALREADY_EXIST,
            error_message=error_message,
            status_code=status_code
        ) from exc

    return JSONResponse(
        content={"message": f"Bucket '{bucket_name}' created successfully."}, status_code=status.HTTP_201_CREATED
    )


@router.delete(
    "/{bucket_name}",
    dependencies=[Depends(check_bucket_exist)],
    summary="Delete a bucket",
    status_code=status.HTTP_200_OK
)
def delete_bucket(bucket_name: str, boto_client: boto3.client = Depends(get_boto_client)):
    boto_client.delete_bucket(Bucket=bucket_name)
    response = {"message": f"Bucket '{bucket_name}' deleted successfully."}
    return JSONResponse(content=response, status_code=status.HTTP_200_OK)


@router.get(
    "/{bucket_name}",
    dependencies=[Depends(check_bucket_exist)],
    response_model=customize_page(str),
    summary="List all files in a bucket",
    status_code=status.HTTP_200_OK,
)
async def list_files(bucket_name: str, boto_client: boto3.client = Depends(get_boto_client)):
    bucket = boto_client.list_objects(Bucket=bucket_name)
    bucket_contents = bucket.get("Contents", [])
    data = [file.get("Key") for file in bucket_contents]
    return await paginate(data)


@router.put(
    "/{bucket_name}",
    dependencies=[Depends(check_bucket_exist)],
    summary="Upload a file to a bucket",
    status_code=status.HTTP_202_ACCEPTED,
)
def upload_file(bucket_name: str, file: UploadFile = File(...), boto_client: boto3.client = Depends(get_boto_client)):
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(file.file.read())

    try:
        boto_client.upload_file(Filename=temp_file.name, Bucket=bucket_name, Key=file.filename)
        os.remove(temp_file.name)
    except (exceptions.ClientError, exceptions.BotoCoreError) as exc:
        error_message = exc.response.get("Error", {}).get("Message", "An error occurred")
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", status.HTTP_400_BAD_REQUEST)
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_NAME,
            error_message=error_message,
            status_code=status_code
        ) from exc

    response = {"filename": file.filename, "type": file.content_type}
    return JSONResponse(content=response, status_code=status.HTTP_202_ACCEPTED)


@router.get(
    "/{bucket_name}/{filename}",
    dependencies=[Depends(check_bucket_exist)],
    summary="Download file from a bucket",
    status_code=status.HTTP_200_OK
)
def get_file(
    request: Request,
    bucket_name: str,
    filename: str,
    boto_client: boto3.client = Depends(get_boto_client)
):
    try:
        head_object = boto_client.head_object(Bucket=bucket_name, Key=filename)
        boto_client.download_file(Bucket=bucket_name, Filename=filename, Key=filename)

        content_type = head_object["ContentType"]

        with open(file=filename, mode="rb") as f:
            file_content = f.read()

        response = Response(
            content=file_content,
            status_code=status.HTTP_200_OK,
            headers={
                "Content-Disposition": f"attachment;filename={filename}",
                "Content-Type": content_type
            },
        )
    except (exceptions.ClientError, exceptions.BotoCoreError) as exc:
        error_message = exc.response.get("Error", {}).get("Message", "An error occurred")
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", status.HTTP_400_BAD_REQUEST)
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_NAME,
            error_message=error_message,
            status_code=status_code
        ) from exc

    return response


@router.delete(
    "/{bucket_name}/{filename}",
    dependencies=[Depends(check_bucket_exist)],
    summary="Delete a file from a bucket",
    status_code=status.HTTP_200_OK
)
def delete_file(bucket_name: str, filename: str, boto_client: boto3.client = Depends(get_boto_client)):
    boto_client.delete_object(Bucket=bucket_name, Key=filename)
    response = {"message": f"File '{filename}' deleted successfully."}

    return JSONResponse(content=response, status_code=status.HTTP_200_OK)
