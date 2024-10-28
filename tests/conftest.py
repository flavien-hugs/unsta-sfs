from unittest import mock

import pytest
from httpx import AsyncClient


@pytest.fixture
def fake_data():
    import faker

    return faker.Faker()


@pytest.fixture()
async def mock_app():
    from src.main import app

    yield app


@pytest.fixture(autouse=True)
def mock_boto_client():
    with mock.patch("src.common.boto_client.boto3.client", return_value=mock.Mock()) as mock_client:
        yield mock_client


@pytest.fixture()
def mock_bucket_data(fake_data):
    return {
        "Buckets": [
            {
                "Name": fake_data.name(),
                "CreationDate": fake_data.date_time_this_year(),
            }
        ]
    }


@pytest.fixture
async def http_client_api(mock_app, mock_boto_client):
    from src.common.boto_client import get_boto_client

    mock_app.dependency_overrides[get_boto_client] = lambda: mock_boto_client

    async with AsyncClient(app=mock_app, base_url="http://sfs.api") as ac:
        yield ac

    mock_app.dependency_overrides = {}
