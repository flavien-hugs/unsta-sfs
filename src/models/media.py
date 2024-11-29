from urllib.parse import urljoin

from beanie import Document
from pydantic import computed_field, Field
from pymongo import ASCENDING, IndexModel

from src.config import settings
from src.schemas import MediaSchema
from .mixins import DatetimeTimestamp


class Media(Document, MediaSchema, DatetimeTimestamp):
    url: str = Field(..., description="Media URL")

    class Settings:
        name = settings.MEDIA_DB_COLLECTION.split(".")[1]
        indexes = [
            IndexModel(
                [("bucket_name", ASCENDING), ("name_in_minio", ASCENDING)],
                unique=True,
                name="bucket_name_name_in_minio_index",
            )
        ]

    @computed_field
    def media_url(self) -> str:
        file_path = f"{self.bucket_name}/{self.name_in_minio}"
        if self.is_public:
            return urljoin(settings.STORAGE_BROWSER_REDIRECT_URL, f"/media/public/{file_path}")
        else:
            return urljoin(settings.STORAGE_BROWSER_REDIRECT_URL, f"/media/{file_path}")
