from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BaseBucketSchema(BaseModel):
    name: str = Field(..., title="Bucket name")
    description: Optional[str] = Field(None, title="Bucket description")


class BucketSchema(BaseBucketSchema):
    created_at: datetime = Field(..., title="Bucket creation date")


class BucketFilter(BaseModel):
    name: Optional[str] = Field(None, title="Bucket name")
    description: Optional[str] = Field(None, title="Bucket description")
    created_at: Optional[datetime] = Field(None, title="Bucket creation date")
    updated_at: Optional[datetime] = Field(None, title="Bucket update date")
