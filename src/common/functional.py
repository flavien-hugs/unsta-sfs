import re
import secrets
from datetime import datetime
from urllib import parse

from fastapi_pagination import Page
from fastapi_pagination.customization import CustomizedPage, UseOptionalParams
from fastapi_pagination.utils import disable_installed_extensions_check
from starlette import status

from src.common.error_codes import SfsErrorCodes
from src.common.exception import CustomHTTPException

disable_installed_extensions_check()


def customize_page(model):
    """
    Customize the pagination page.

    :param model: model to be used for pagination
    :type model: document
    :return: list of paginated items
    :rtype: dict

    Example:
    ---------

    install module fastapi-pagination

    ```python
    from src.common.helper.pagination import customize_page
    from src.models import ItemModel
    from fastapi_pagination.ext.beanie import paginate # if use beanie-odm

    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/items", response_model=customize_page(ItemModel))
    async def get_all_items():
        items = ItemModel.find({})
        return await paginate(items)
    ```
    """
    return CustomizedPage[Page[model], UseOptionalParams()]


def replace_minio_url_base(domain: str, url: str) -> str:
    """
    Replace the Minio URL base with the provided domain

    :param domain: The domain to replace the Minio URL base
    :param url: The URL to replace the Minio URL base
    """

    new_url = parse.urlparse(url)
    domain = new_url._replace(netloc=domain)
    return domain.geturl()


def format_bucket(bucket_name: str) -> str:
    """
    Format a bucket name to lowercase and limits its length.

    :param bucket_name: The bucket name to format
    :type bucket_name: str
    :return: The formatted bucket name
    """

    formatted = bucket_name.lower()[:63]
    if not re.match(pattern=r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$", string=formatted):
        raise CustomHTTPException(
            error_code=SfsErrorCodes.SFS_INVALID_NAME,
            error_message=f"Invalid bucket name {formatted}."
            " Must be between 3 and 63 characters and contain only lowercase letters,"
            " numbers, dots, and hyphens.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return formatted


async def generate_media_name(extension: str) -> str:
    """
    Generates a unique media_router file name using the current timestamp, a UUID, and the provided file extension.

    :param extension: The file extension (e.g., 'jpg', 'png').
    :type extension: str
    :return: Unique media_router file name with the provided extension.
    :rtype: str
    """

    timestamp, unique_id = datetime.now().strftime("%Y%m%d%H%M%S"), secrets.token_hex(nbytes=10)
    result = f"{unique_id}-{timestamp}.{extension.lower()}"
    return result
