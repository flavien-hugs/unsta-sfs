from datetime import datetime

from pydantic import BaseModel, Field


class DatetimeTimestamp(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now, description="Creation date")
    updated_at: datetime = Field(default_factory=datetime.now, title="Update date")
