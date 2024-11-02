import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi

_mongoclient: Optional[AsyncIOMotorClient] = None
logging.basicConfig(format="%(message)s", level=logging.INFO)
_log = logging.getLogger(__name__)


async def config_mongodb_client(mongodb_uri: str) -> AsyncIOMotorClient:
    """
    Connect to mongodb server and return the client

    :param mongodb_uri: MongoDB URI
    """

    global _mongoclient

    if _mongoclient is None or _mongoclient.closed is True:
        _mongoclient = AsyncIOMotorClient(mongodb_uri, server_api=ServerApi("1"))
        try:
            await _mongoclient.admin.command("ping")
            _log.info("Pinged your deployment. You successfully connected to MongoDB")
        except Exception as e:
            _log.debug(f"Failed to connect to MongoDB: {e}")
            _mongoclient = _mongoclient
    return _mongoclient
