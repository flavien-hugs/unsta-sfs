from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class SfsBaseSettings(BaseSettings):
    # APP SETTINGS
    APP_NAME: Optional[str] = Field(default="sfs", alias="APP_NAME", description="Name of the application")
    APP_RELOAD: Optional[bool] = Field(default=True, alias="APP_RELOAD", description="Reload the server on changes")
    APP_LOOP: Optional[str] = Field(
        default="uvloop", alias="APP_LOOP", description="Type of loop to use: none, auto, asyncio or uvloop"
    )
    APP_LOG_LEVEL: Optional[str] = Field(
        default="info", alias="APP_LOG_LEVEL", description="Log level to use: debug, info, warning, error, critical"
    )
    APP_HOSTNAME: Optional[str] = Field(default="0.0.0.0", alias="APP_HOSTNAME", description="Hostname to use")
    APP_ACCESS_LOG: Optional[bool] = Field(default=False, alias="APP_ACCESS_LOG", description="Enable access log")
    APP_DEFAULT_PORT: Optional[int] = Field(default=1993, alias="APP_DEFAULT_PORT", description="Default port to use")
    APP_TITLE: Optional[str] = Field(
        default="UNSTA: Simple file storage", alias="APP_TITLE", description="Title of the application"
    )

    # STORAGE SETTINGS
    STORAGE_HOST: str = Field(..., alias="STORAGE_HOST")
    STORAGE_API_PORT: int = Field(..., alias="STORAGE_API_PORT")
    STORAGE_ROOT_USER: str = Field(..., alias="STORAGE_ROOT_USER")
    STORAGE_ACCESS_KEY: str = Field(..., alias="STORAGE_ACCESS_KEY")
    STORAGE_SECRET_KEY: str = Field(..., alias="STORAGE_SECRET_KEY")
    STORAGE_CONSOLE_PORT: int = Field(..., alias="STORAGE_CONSOLE_PORT")
    STORAGE_ROOT_PASSWORD: str = Field(..., alias="STORAGE_ROOT_PASSWORD")
    STORAGE_REGION_NAME: Optional[str] = Field(default="af-south-1", alias="STORAGE_REGION_NAME")


@lru_cache()
def sfs_settings() -> SfsBaseSettings:
    return SfsBaseSettings()
