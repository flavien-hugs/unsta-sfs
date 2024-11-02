from unittest import mock

import pytest

from src.config import settings
from src.config.database import shutdown_db_client, startup_db_client


@pytest.mark.asyncio
@mock.patch("src.config.database.init_beanie", return_value=None)
async def test_startup_db_client(mock_init_beanie, fixture_client_mongo, mock_app_instance, fixture_models):
    await startup_db_client(app=mock_app_instance, models=[fixture_models.Bucket, fixture_models.Media])

    assert mock_app_instance.mongo_db_client is not None
    assert fixture_client_mongo.is_mongos is True

    mock_init_beanie.assert_called_once_with(
        database=mock_app_instance.mongo_db_client[settings.MONGO_DB],
        document_models=[fixture_models.Bucket, fixture_models.Media],
        multiprocessing_mode=True,
    )


@pytest.mark.asyncio
async def test_shutdown_db_client(mock_app_instance):
    mock_app_instance.mongo_db_client = mock.AsyncMock()
    await shutdown_db_client(app=mock_app_instance)
    mock_app_instance.mongo_db_client.close.assert_called_once()
