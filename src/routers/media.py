import json
from mimetypes import guess_type
from typing import Optional

import boto3
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, status, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi_pagination.async_paginator import paginate as async_paginate
from pymongo import ASCENDING, DESCENDING

from src.common.boto_client import check_bucket_exists, get_boto_client
from src.common.error_codes import SfsErrorCodes
from src.common.exception import CustomHTTPException
from src.common.functional import customize_page
from src.common.permissions import CheckAccessAllow
from src.common.utils import SortEnum
from src.models import Media
from src.schemas import MediaFilter
from src.services import delete_media_if_exist_from_mongo, download_media, find_public_media, get_media, upload_media

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
@media_router.post(
    "/_write",
    response_model=Media,
    summary="Upload a file to an S3 object (unsecured).",
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
async def upload_file_to_buckect(
    bucket_name: str = Form(..., description="Bucket name to upload the file"),
    is_public: bool = Form(False, description="If the file is public or not"),
    ttl_minutes: Optional[int] = Form(None, description="Time to live in minutes for the file"),
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
    except (json.JSONDecodeError, Exception) as exc:
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_TAGS_FORMAT,
            error_message="Tags should  be like: \"{'key': 'value'}\" dumped. \n Error: " f"{str(exc)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc

    result = await upload_media(
        botoclient=botoclient,
        bucket_name=bucket_name,
        tags=tags_dict,
        file=file,
        is_public=is_public,
        ttl_minutes=ttl_minutes,
    )
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
    if query.filename:
        search.update({"name_in_minio": {"$regex": query.filename, "$options": "i"}})
    if query.public:
        search.update({"is_public": query.public})
    if query.tags:
        del query["tags"]
        search.update({f"tags.{k}": v for k, v in query.tags.items()})

    sorted = DESCENDING if sort == SortEnum.DESC else ASCENDING
    medias = await Media.find(search, sort=[("created_at", sorted)]).to_list()
    media = [await get_media(filename=media.name_in_minio, bucket_name=media.bucket_name) for media in medias if media]
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
    download: bool = Query(default=False, description="Download the file"),
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
    status_code=status.HTTP_200_OK,
)
async def delete_file(bucket_name: str, filename: str, botoclient: boto3.client = Depends(get_boto_client)):
    await delete_media_if_exist_from_mongo(bucket_name=bucket_name, filename=filename, botoclient=botoclient)
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "File deleted successfully."})


@media_router.get(
    "/public/{bucket_name}/{filename}",
    summary="Retrieve public media",
    status_code=status.HTTP_200_OK,
)
async def get_public_media(bucket_name: str, filename: str, botoclient: boto3.client = Depends(get_boto_client)):
    items_found = await find_public_media(bucket_name=bucket_name, filename=filename)

    if not items_found:
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_FILE_NOT_FOUND,
            error_message=f"File {filename} not found in bucket {bucket_name} or is not public or expirartion date exceeded.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # retrieve the media from MinIO and stream it
    try:
        media = await get_media(bucket_name=bucket_name, filename=filename, botoclient=botoclient)
    except Exception as exc:
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_FILE_NOT_FOUND,
            error_message=str(exc),
            status_code=status.HTTP_404_NOT_FOUND,
        ) from exc

    return StreamingResponse(
        content=media,
        media_type="application/octet-stream",
    )
