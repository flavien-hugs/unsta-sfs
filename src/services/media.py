import os
import tempfile
from typing import Optional
from urllib.parse import urljoin

import boto3
from botocore import exceptions
from fastapi import BackgroundTasks, Depends, File, status, UploadFile
from fastapi.responses import FileResponse
from typing_extensions import deprecated
from urllib3 import BaseHTTPResponse, HTTPResponse

from src.common.boto_client import get_boto_client, check_bucket_exists
from src.common.error_codes import SfsErrorCodes
from src.common.exception import CustomHTTPException
from src.common.functional import format_bucket, generate_media_name, replace_minio_url_base
from src.config import settings
from src.models import Media
from src.schemas import MediaSchema


def _upload_media_to_minio(
    file: UploadFile,
    key: str,
    tags: Optional[dict] = None,
    bucket_name: str = Depends(format_bucket),
    botoclient: boto3.client = Depends(get_boto_client),
):
    check_bucket_exists(bucket_name, botoclient=botoclient)

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(file.file.read())

    try:
        extra_args = {}
        if tags:
            tag_set = [{"Key": key, "Value": str(value)} for key, value in tags.items()]
            extra_args["Tagging"] = "&".join([f"{tag['Key']}:{tag['Value']}" for tag in tag_set])

        response = botoclient.upload_file(Filename=temp_file.name, Bucket=bucket_name, Key=key, ExtraArgs=extra_args)
    except (exceptions.ClientError, exceptions.BotoCoreError) as exc:
        error_message = exc.response.get("Error", {}).get("Message", "An error occurred")
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", status.HTTP_400_BAD_REQUEST)
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_NAME, error_message=error_message, status_code=status_code
        ) from exc

    os.remove(temp_file.name)

    return response


@deprecated("Url will not be generated by minio directly. Use _generate_media_url instead.")
def _media_url_from_minio(
    filename: str,
    bucket_name: str = Depends(format_bucket),
    redirect_url: Optional[str] = None,
    botoclient: boto3.client = Depends(get_boto_client),
) -> str:

    try:
        url = botoclient.generate_presigned_url(ClientMethod="get_object", Params={"Bucket": bucket_name, "Key": filename})
    except (exceptions.ClientError, exceptions.BotoCoreError) as exc:
        error_message = exc.response.get("Error", {}).get("Message", "An error occurred")
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", status.HTTP_400_BAD_REQUEST)
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_NAME, error_message=error_message, status_code=status_code
        ) from exc

    result = replace_minio_url_base(redirect_url, url) if redirect_url else url
    return result


def _generate_media_url(
    filename: str, bucket_name: str = Depends(format_bucket), botoclient: boto3.client = Depends(get_boto_client)
) -> str:
    """
    Generate a media URL from Minio.

    :param filename: The name of the media file
    :rtype filename: str
    :param bucket_name: The name of the bucket
    :rtype bucket_name: str
    :param botoclient: The boto3 client object
    :rtype botoclient: boto3.client
    :return str: The media URL
    :rtype str
    """
    media_path = urljoin(settings.STORAGE_BROWSER_REDIRECT_URL, f"media/{bucket_name}/{filename}")
    return media_path


async def _save_media(media: MediaSchema, file: UploadFile, botoclient: boto3.client = Depends(get_boto_client)) -> Media:
    _upload_media_to_minio(
        bucket_name=media.bucket_name, file=file, tags=media.tags, key=media.name_in_minio, botoclient=botoclient
    )
    obj_url = _generate_media_url(bucket_name=media.bucket_name, filename=media.name_in_minio, botoclient=botoclient)
    media = await Media(**media.model_dump(), url=obj_url).create()
    return media


async def upload_media(
    bucket_name: str,
    tags: Optional[dict] = None,
    file: UploadFile = File(...),
    is_public: Optional[bool] = False,
    ttl_minutes: Optional[int] = None,
    botoclient: boto3.client = Depends(get_boto_client),
):
    extension = file.filename.split(".")[-1]
    media_name = await generate_media_name(extension=extension)

    media_schema = MediaSchema(
        bucket_name=bucket_name,
        name_in_minio=media_name,
        tags=tags if tags else None,
        filename=media_name,
        is_public=is_public,
        ttl_minutes=ttl_minutes,
    )
    media = await _save_media(media=media_schema, file=file, botoclient=botoclient)
    return media


async def get_media(
    filename: str, bucket_name: str = Depends(format_bucket), botoclient: boto3.client = Depends(get_boto_client)
) -> HTTPResponse | BaseHTTPResponse:
    media_doc = await Media.find_one({"name_in_minio": filename, "bucket_name": bucket_name})
    if media_doc:
        try:
            file_data = botoclient.get_object(Bucket=bucket_name, Key=filename)
        except (exceptions.ClientError, exceptions.BotoCoreError) as exc:
            error_message = exc.response.get("Error", {}).get("Message", "An error occurred")
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", status.HTTP_400_BAD_REQUEST)
            raise CustomHTTPException(
                error_code=SfsErrorCodes.SFS_INVALID_NAME, error_message=error_message, status_code=status_code
            ) from exc

        return file_data
    else:
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_NAME,
            error_message=f"Media '{filename}' not found.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


async def delete_media_if_exist_from_mongo(
    filename: str, bucket_name: str = Depends(format_bucket), botoclient: boto3.client = Depends(get_boto_client)
) -> None:
    if media := Media.find_one({"name_in_minio": filename, "bucket_name": bucket_name}):
        delete_from_bucket = botoclient.delete_object(Bucket=bucket_name, Key=filename)
        if delete_from_bucket.get("ResponseMetadata", {}).get("HTTPStatusCode") == status.HTTP_204_NO_CONTENT:
            await media.delete()


async def download_media(
    filename: str,
    bucket_name: str = Depends(format_bucket),
    bg: BackgroundTasks = Depends(BackgroundTasks()),
    botoclient: boto3.client = Depends(get_boto_client),
):
    # Rechercher le média dans votre base de données
    if (media := await Media.find_one({"name_in_minio": filename, "bucket_name": bucket_name})) is None:
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_NAME, error_message="Media not found", status_code=status.HTTP_400_BAD_REQUEST
        )

    # Télécharger le fichier depuis MinIO
    try:
        media_object = botoclient.get_object(Bucket=bucket_name, Key=media.name_in_minio)
    except (exceptions.ClientError, exceptions.BotoCoreError) as exc:
        error_message = exc.response.get("Error", {}).get("Message", "An error occurred")
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", status.HTTP_400_BAD_REQUEST)
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_NAME, error_message=error_message, status_code=status_code
        ) from exc

    # Créer un fichier temporaire pour stocker le contenu
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(media_object["Body"].read())
        temp_file_path = temp_file.name

    # Déterminer le type de contenu
    content_type = media_object.get("ContentType", "application/octet-stream")

    # Définir la fonction de nettoyage
    bg.add_task(os.remove, temp_file_path)

    # Utiliser FileResponse avec la tâche de fond
    response = FileResponse(
        path=temp_file_path,
        media_type=content_type,
        filename=media.filename,
        headers={
            "Content-Disposition": f"attachment; filename={media.filename}",
        },
        background=bg,
    )

    return response


async def find_public_media(bucket_name: str, filename: str):
    pipeline = [
        {"$match": {"bucket_name": bucket_name, "name_in_minio": filename, "is_public": True}},
        {
            "$addFields": {
                "expiration_time": {
                    "$cond": {
                        "if": {"$ne": ["$ttl_minutes", None]},
                        "then": {"$add": ["$updated_at", {"$multiply": ["$ttl_minutes", 60000]}]},  # 1mn -> ms
                        "else": None,
                    }
                }
            }
        },
        {"$match": {"$or": [{"expiration_time": {"$gt": datetime.now()}}, {"expiration_time": None}]}},
    ]

    media_from_db = await Media.aggregate(pipeline).to_list()
    return media_from_db
