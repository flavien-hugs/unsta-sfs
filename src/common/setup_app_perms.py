import os.path
from pathlib import Path

import yaml
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from slugify import slugify

BASE_DIR = Path(__file__).parent.parent.parent


async def __init_collection(client: AsyncIOMotorClient, collection_path: str) -> AsyncIOMotorCollection:
    """
    Initialize a collection with a unique index on the 'app' field.

    :param client: Motor client instance to connect to the database.
    :rtype client: AsyncIOMotorClient
    :param collection_path: Path to the collection in the format 'database.collection'.
    :rtype collection_path: str
    :return: Collection instance.
    :rtype: AsyncIOMotorCollection
    """
    database_name, collection_name = collection_path.split(".")
    database = client[database_name]
    collection = database[collection_name]

    await collection.create_index("app", unique=True, background=True)

    return collection


async def __load_app_description(filpath) -> dict:
    """
    Load the app description from a JSON file.

    :param filpath: Path to the JSON file.
    :rtype filpath: str
    :return: App description.
    :rtype: dict
    """

    if os.path.exists(filpath) is False:
        raise ValueError("App description file not found.")

    with open(filpath, "r") as f:
        data = yaml.safe_load(f)

    return data


async def load_app_description(
    mongodb_client: AsyncIOMotorClient,
    collection_path: str = None,
    filename: str = "appdesc.yml",
):
    """
    Load the app description from a JSON file and update the database.
    """

    if not (coll_path := collection_path or os.environ.get("APP_DESC_DB_COLLECTION")):
        raise ValueError("Invalid collection path")

    coll = await __init_collection(mongodb_client, coll_path)

    filepath = BASE_DIR / f"{filename}"
    data = await __load_app_description(filepath)

    if not (appname := data[0].get("app", {}).get("name", "").strip()):
        raise ValueError(f"App name '{appname}' not found in {filepath}")

    if not (title := data[0].get("app", {}).get("title", {})):
        raise ValueError(f"title section for app '{appname}' not found in {filepath}")

    await coll.update_one(
        {"app": slugify(appname)},
        {"$set": {"title": title}},
        upsert=True,
    )


async def load_app_permissions(
    mongodb_client: AsyncIOMotorClient,
    collection_path: str = None,
    filename: str = "appdesc.yml",
):
    """
    Load the app permissions from a JSON file and update the database.
    """

    if not (coll_path := collection_path or os.environ.get("PERMS_DB_COLLECTION")):
        raise ValueError("Invalid collection path")

    coll = await __init_collection(mongodb_client, coll_path)

    filepath = BASE_DIR / f"{filename}"
    data = await __load_app_description(filepath)

    if not (appname := data[0].get("app", {}).get("name", "").strip()):
        raise ValueError(f"App name '{appname}' not found in {filepath}")

    if not (permissions := data[0].get("app", {}).get("permissions", [])):
        return

    await coll.update_one(
        {"app": slugify(appname)},
        {
            "$set": {
                "permissions": [
                    {"code": slugify(item["code"], regex_pattern=r"[^a-zA-Z0-9:]+"), "desc": item["desc"]} for item in permissions
                ]
            }
        },
        upsert=True,
    )
