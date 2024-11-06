import json
from typing import Optional
from mimetypes import guess_type

import boto3
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, status, UploadFile
from fastapi.responses import StreamingResponse
from fastapi_pagination.async_paginator import paginate as async_paginate
from pymongo import ASCENDING, DESCENDING

from src.common.boto_client import check_bucket_exists, get_boto_client
from src.common.error_codes import SfsErrorCodes
from src.common.permissions import CheckAccessAllow
from src.common.exception import CustomHTTPException
from src.common.functional import customize_page
from src.common.utils import SortEnum
from src.models import Media
from src.schemas import MediaFilter
from src.services import delete_media_if_exist_from_mongo, download_media, get_media, upload_media

media_router: APIRouter = APIRouter(
    prefix="/media",
    tags=["MEDIAS"],
    responses={404: {"description": "Not found"}},
)


@media_router.post(
    "",
    dependencies=[Depends(CheckAccessAllow(permissions={"sfs:can-write-bucket"}))],
    response_model=Media,
    summary="Upload a file to an S3 object.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_file_to_buckect(
    bucket_name: str = Form(..., description="Bucket name to upload the file"),
    file: UploadFile = File(..., description="File to be uploaded"),
    tags: Optional[str] = Form(
        None,
        examples=['{"category":"documents","author":"John Doe"}'],
        description="Tags to be added to the file as a JSON string",
    ),
    botoclient: boto3.client = Depends(get_boto_client),
):
    try:
        tags_dict = json.loads(tags) if tags else {}
    except json.JSONDecodeError as exc:
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_TAGS,
            error_message="Invalid JSON string for tags.",
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc

    result = await upload_media(botoclient=botoclient, bucket_name=bucket_name, tags=tags_dict, file=file)
    return result


@media_router.get(
    "",
    dependencies=[Depends(CheckAccessAllow(permissions={"sfs:can-read-file"}))],
    response_model=customize_page(Media),
    summary="List media files",
    status_code=status.HTTP_200_OK,
)
async def list_media(
    query: MediaFilter = Depends(MediaFilter),
    sort: Optional[SortEnum] = Query(default=SortEnum.DESC, alias="sort", description="Sort by 'asc' or 'desc"),
    botoclient: boto3.client = Depends(get_boto_client),
):
    search = {}
    if query.bucket_name:
        check_bucket_exists(bucket_name=query.bucket_name, botoclient=botoclient)
        search.update({"bucket_name": {"$regex": query.bucket_name, "$options": "i"}})
    if query.tags:
        del query["tags"]
        search.update({f"tags.{k}": v for k, v in query.tags.items()})

    sorted = DESCENDING if sort == SortEnum.DESC else ASCENDING
    medias = await Media.find(search, sort=[("created_at", sorted)]).to_list()
    media = [await get_media(filename=m.name_in_minio, bucket_name=m.bucket_name) for m in medias if m]
    return await async_paginate(media)


@media_router.get(
    "/{bucket_name}/{filename}/_read", summary="Get media url", status_code=status.HTTP_200_OK, include_in_schema=False
)
@media_router.get(
    "/{bucket_name}/{filename}",
    dependencies=[Depends(CheckAccessAllow(permissions={"sfs:can-read-file"}))],
    summary="Retrieve single media",
    status_code=status.HTTP_200_OK,
)
async def get_media_obj(
    bg: BackgroundTasks,
    bucket_name: str,
    filename: str,
    download: bool = Query(default=False),
    botoclient: boto3.client = Depends(get_boto_client),
):
    if download:
        return await download_media(bucket_name=bucket_name, filename=filename, bg=bg, botoclient=botoclient)
    else:
        media = await get_media(bucket_name=bucket_name, filename=filename, botoclient=botoclient)

        content_type = media.get("ContentType")
        if not content_type:
            content_type, _ = guess_type(filename)
            if not content_type:
                content_type = "application/octet-stream"

        return StreamingResponse(
            content=media["Body"],
            media_type=content_type,
            headers={
                "Content-Length": str(media.get("ContentLength")),
                "ETag": media.get("ETag"),
                "Content-Disposition": f'inline; filename="{filename}"',
            },
        )


@media_router.delete(
    "/{bucket_name}/{filename}",
    dependencies=[Depends(CheckAccessAllow(permissions={"sfs:can-delete-file"}))],
    summary="Delete a file from a bucket",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_file(bucket_name: str, filename: str, botoclient: boto3.client = Depends(get_boto_client)):
    await delete_media_if_exist_from_mongo(bucket_name=bucket_name, filename=filename, botoclient=botoclient)
