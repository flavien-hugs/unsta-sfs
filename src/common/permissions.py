from typing import Set
from urllib.parse import urlencode, urljoin

import httpx
from fastapi import Header, status

from src.config import settings
from .error_codes import SfsErrorCodes
from .exception import CustomHTTPException


class CheckAccessAllow:
    """
    This class is used to check if a user has the necessary permissions to access a resource.
    """

    def __init__(self, permissions: Set, raise_exception: bool = True):
        self.url = urljoin(settings.API_AUTH_URL_BASE, settings.API_AUTH_CHECK_ACCESS_ENDPOINT)
        self.permissions = permissions
        self.raise_exception = raise_exception

    async def __call__(self, authorization: str = Header(...)):
        headers = {"Authorization": authorization}
        query_params = urlencode([("permission", item) for item in self.permissions])
        url = f"{self.url}?{query_params}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)

            if response.is_success is False:
                if self.raise_exception:
                    raise CustomHTTPException(
                        error_code=SfsErrorCodes.AUTH_ACCESS_DENIED,
                        error_message="Access denied",
                        status_code=status.HTTP_403_FORBIDDEN,
                    )
                return False

            access = response.json()["access"]
            if access is False and self.raise_exception:
                raise CustomHTTPException(
                    error_code=SfsErrorCodes.AUTH_ACCESS_DENIED,
                    error_message="Access denied",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            return access
