import logging
from typing import List, Type

from beanie import Document, init_beanie
from fastapi import FastAPI

from src.common.mongo_client import config_mongodb_client

from .settings import sfs_settings as settings

logging.basicConfig(format="%(message)s", level=logging.INFO)
_log = logging.getLogger(__name__)


async def startup_db_client(app: FastAPI, models: List[Type[Document]]) -> None:
    client = await config_mongodb_client(settings().MONGODB_URI)
    if app:
        app.mongo_db_client = client

    DATABASE_NAME = settings().MEDIA_DB_COLLECTION.split(".")[0]
    await init_beanie(database=client[DATABASE_NAME], document_models=models, multiprocessing_mode=True)
    _log.info("==> Database init successfully !")


async def shutdown_db_client(app: FastAPI):
    app.mongo_db_client.close()
    _log.info("==> Database closed successfully !")
