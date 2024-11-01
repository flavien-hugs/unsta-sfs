from typing import Optional

import boto3
from fastapi import APIRouter, Body, Depends, Query, status
from fastapi.responses import JSONResponse
from fastapi_pagination.ext.beanie import paginate
from pymongo import ASCENDING, DESCENDING

from src.common.boto_client import get_boto_client
from src.common.functional import customize_page
from src.common.utils import SortEnum
from src.models import Bucket
from src.schemas import BucketFilter, BucketSchema
from src.services import create_new_bucket, delete_bucket, get_or_create_bucket

bucket_router: APIRouter = APIRouter(
    prefix="/buckets",
    tags=["BUCKETS"],
    responses={404: {"description": "Not found"}},
)


@bucket_router.post(
    "",
    response_model=Bucket,
    summary="Create a bucket",
    status_code=status.HTTP_201_CREATED,
)
async def create_bucket(bucket: BucketSchema = Body(...), botoclient: boto3.client = Depends(get_boto_client)):
    new_bucket = await create_new_bucket(bucket, botoclient=botoclient)
    return new_bucket


@bucket_router.get("", response_model=customize_page(Bucket), summary="List all buckets", status_code=status.HTTP_200_OK)
async def list_buckets(
    query: BucketFilter = Depends(BucketFilter),
    sort: Optional[SortEnum] = Query(default=SortEnum.DESC, alias="sort", description="Sort by 'asc' or 'desc"),
):
    search = {}
    if query.bucket_name:
        search.update({"bucket_name": {"$regex": query.bucket_name, "$options": "i"}})
    if query.description:
        search.update({"description": {"$regex": query.description, "$options": "i"}})
    if query.created_at:
        search.update({"created_at": query.created_at})

    sorted = DESCENDING if sort == SortEnum.DESC else ASCENDING
    buckets = Bucket.find(search, sort=[("created_at", sorted)])
    return await paginate(buckets)


@bucket_router.get("/{bucket_name}", response_model=Bucket, summary="Get a bucket", status_code=status.HTTP_200_OK)
async def get_bucket(
    bucket_name: str,
    create_bucket_if_not_exist: bool = Query(default=False, description="Create the bucket if it doesn't exist"),
    botoclient: boto3.client = Depends(get_boto_client),
):
    """
    Get a bucket by its name.

    Args:
    - bucket_name (str): The bucket name to get
    - create_bucket_if_not_exist (bool): Create the bucket if it doesn't exist (default: False)
    - botoclient (boto3.client): boto3 client object to interact with S3

    Returns:
    - The bucket object (Bucket)
    """
    bucket = await get_or_create_bucket(bucket_name, create_bucket_if_not_exist, botoclient)
    return bucket


@bucket_router.delete("/{bucket_name}", summary="Delete a bucket", status_code=status.HTTP_200_OK)
async def remove_bucket(bucket_name: str, botoclient: boto3.client = Depends(get_boto_client)):
    await delete_bucket(bucket_name, botoclient)
    response = {"message": f"Bucket '{bucket_name}' deleted successfully."}
    return JSONResponse(content=response, status_code=status.HTTP_200_OK)
