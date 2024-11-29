from typing import Optional

from pydantic import BaseModel, Field


class MediaSchema(BaseModel):
    filename: str = Field(..., description="Media filename")
    bucket_name: str = Field(..., description="Bucket name")
    name_in_minio: str = Field(..., description="Media object name in minio")
    tags: dict = Field(None, description="list of tags")
    is_public: Optional[bool] = Field(False, description="Is media public")
    ttl_minutes: Optional[int] = Field(None, description="Time to live in minutes")


class MediaFilter(BaseModel):
    bucket_name: Optional[str] = Field(None, description="Bucket name")
    filename: Optional[str] = Field(None, description="Media filename")
    public: Optional[bool] = Field(None, description="Is media public")
    tags: Optional[dict] = Field(None, description="Media tags", examples=['{"key":"value"}'])
