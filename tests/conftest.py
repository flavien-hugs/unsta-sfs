from unittest import mock

import pytest
from beanie import init_beanie
from httpx import AsyncClient
from mongomock_motor import AsyncMongoMockClient

from src.config import settings


@pytest.fixture
def fake_data():
    import faker

    return faker.Faker()


@pytest.fixture()
async def mock_app_instance():
    from src.main import app as mock_app

    yield mock_app


@pytest.fixture()
def fixture_models():
    from src import models

    return models


@pytest.fixture(autouse=True)
async def mongo_client():
    yield AsyncMongoMockClient()


@pytest.fixture(autouse=True)
def mock_boto_client():
    with mock.patch("src.common.boto_client.boto3.client", return_value=mock.Mock()) as mock_client:
        yield mock_client


@pytest.fixture(autouse=True)
async def fixture_client_mongo(mock_app_instance, mongo_client, fixture_models):
    mock_app_instance.mongo_db_client = mongo_client[settings.MONGO_DB]
    await init_beanie(
        database=mock_app_instance.mongo_db_client,
        document_models=[fixture_models.Bucket, fixture_models.Media],
    )
    yield mongo_client


@pytest.fixture()
def bucket_data(fake_data):
    return {"bucket_name": "unsta-storage", "description": fake_data.text()}


@pytest.mark.asyncio
@pytest.fixture()
async def default_bucket(fixture_models, bucket_data):
    result = await fixture_models.Bucket(**bucket_data).create()
    return result


@pytest.fixture()
def media_data(fake_data):
    file_name = fake_data.file_name()
    return {"filename": file_name, "bucket_name": "unsta-storage", "name_in_minio": file_name, "tags": {"tag": "value"}}


@pytest.mark.asyncio
@pytest.fixture()
async def default_media(fixture_models, media_data, fake_data):
    result = await fixture_models.Media(**media_data, url=fake_data.url()).create()
    return result


@pytest.fixture
async def http_client_api(mock_app_instance, fixture_client_mongo, mock_boto_client):
    from src.common.boto_client import get_boto_client

    mock_app_instance.dependency_overrides[get_boto_client] = lambda: mock_boto_client

    async with AsyncClient(app=mock_app_instance, base_url="http://sfs.api") as bucket_api:
        yield bucket_api

    mock_app_instance.dependency_overrides = {}
