from fastapi_pagination import Page
from fastapi_pagination.customization import CustomizedPage, UseOptionalParams
from fastapi_pagination.utils import disable_installed_extensions_check


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
