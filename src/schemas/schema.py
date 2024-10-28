from datetime import datetime
from pydantic import BaseModel, Field


class BucketSchema(BaseModel):
    name: str = Field(..., title="Bucket name")
    created_at: datetime = Field(..., title="Bucket creation date")
