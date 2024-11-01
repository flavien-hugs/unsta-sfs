from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BucketSchema(BaseModel):
    bucket_name: str = Field(..., title="Bucket name")
    description: Optional[str] = Field(None, title="Bucket description")


class BucketFilter(BaseModel):
    bucket_name: Optional[str] = Field(None, title="Bucket name")
    description: Optional[str] = Field(None, title="Bucket description")
    created_at: Optional[datetime] = Field(None, title="Bucket creation date")
    updated_at: Optional[datetime] = Field(None, title="Bucket update date")
