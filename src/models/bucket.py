from typing import Optional

from beanie import Document
from pydantic import Field

from src.config import settings
from src.schemas import BucketSchema
from .mixins import DatetimeTimestamp


class Bucket(Document, BucketSchema, DatetimeTimestamp):
    bucket_slug: Optional[str] = Field(None, description="Bucket slug validated for minio")

    class Settings:
        name = settings.BUCKET_DB_COLLECTION.split(".")[1]
        use_state_management = True
