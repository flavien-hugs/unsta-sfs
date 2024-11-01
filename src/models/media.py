from beanie import Document
from pydantic import Field

from src.config import settings
from src.schemas import MediaSchema
from .mixins import DatetimeTimestamp


class Media(Document, MediaSchema, DatetimeTimestamp):
    url: str = Field(..., description="Media URL")

    class Settings:
        name = settings.MEDIA_DB_COLLECTION.split(".")[1]
        use_state_management = True
