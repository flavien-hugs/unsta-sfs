from typing import Optional

from pydantic import BaseModel, Field


class MediaSchema(BaseModel):
    filename: str = Field(..., description="Media filename")
    bucket_name: str = Field(..., description="Bucket name")
    name_in_minio: str = Field(..., description="Media object name in minio")
    tags: dict = Field(None, description="list of tags")


class MediaFilter(BaseModel):
    bucket_name: Optional[str] = Field(None, description="Bucket name")
    tags: Optional[dict] = Field(None, description="Media tags")
