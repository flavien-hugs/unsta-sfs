from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

_mongoclient: Optional[AsyncIOMotorClient] = None


async def config_mongodb_client(mongodb_uri: str) -> AsyncIOMotorClient:
    """
    Connect to mongodb server and return the client

    :param mongodb_uri: MongoDB URI
    """

    global _mongoclient

    if _mongoclient is None or _mongoclient.closed is True:
        _mongoclient = AsyncIOMotorClient(mongodb_uri)
    return _mongoclient
