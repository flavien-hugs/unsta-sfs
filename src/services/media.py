import os
import tempfile
from datetime import datetime
from typing import Optional

import boto3
from botocore import exceptions
from fastapi import Depends, File, status, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse

from src.common.boto_client import get_boto_client
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
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(file.file.read())

    try:
        extra_args = {}
        if tags:
            tag_set = [{"Key": key, "Value": str(value)} for key, value in tags.items()]
            extra_args["Tagging"] = "&".join([f"{tag['Key']}:{tag['Value']}" for tag in tag_set])

        response = botoclient.upload_file(Filename=temp_file.name, Bucket=bucket_name, Key=key, ExtraArgs=extra_args)
        os.remove(temp_file.name)
    except (exceptions.ClientError, exceptions.BotoCoreError) as exc:
        error_message = exc.response.get("Error", {}).get("Message", "An error occurred")
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", status.HTTP_400_BAD_REQUEST)
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_NAME, error_message=error_message, status_code=status_code
        ) from exc

    return response


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


async def _save_media(media: MediaSchema, file: UploadFile, botoclient: boto3.client = Depends(get_boto_client)) -> Media:
    _upload_media_to_minio(
        bucket_name=media.bucket_name, file=file, tags=media.tags, key=media.name_in_minio, botoclient=botoclient
    )
    obj_url = _media_url_from_minio(bucket_name=media.bucket_name, filename=media.name_in_minio, botoclient=botoclient)
    media = await Media(**media.model_dump(), url=obj_url).create()
    return media


async def upload_media(
    bucket_name: str,
    tags: Optional[dict] = None,
    file: UploadFile = File(...),
    botoclient: boto3.client = Depends(get_boto_client),
):
    extension = file.filename.split(".")[-1]
    media_name = generate_media_name(extension=extension)

    media_schema = MediaSchema(
        bucket_name=bucket_name, name_in_minio=media_name, tags=tags if tags else None, filename=media_name
    )
    media = await _save_media(media=media_schema, file=file, botoclient=botoclient)
    return media


async def get_media(
    filename: str, bucket_name: str = Depends(format_bucket), botoclient: boto3.client = Depends(get_boto_client)
) -> Media:
    redirect_domain = "http://0.0.0.0:9995"
    media_doc = await Media.find_one({"name_in_minio": filename, "bucket_name": bucket_name})
    if media_doc:
        if (datetime.now() - media_doc.updated_at).days > settings.FILE_TTL_DAYS:
            url = _media_url_from_minio(
                filename=media_doc.name_in_minio, bucket_name=bucket_name, redirect_url=redirect_domain, botoclient=botoclient
            )
            media_doc.url = url
            media_doc.updated_at = datetime.now()
            await media_doc.replace(...)
        return media_doc
    else:
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_NAME,
            error_message=f"Media '{filename}' not found.",
            status_code=status.HTTP_404_NOT_FOUND,
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
