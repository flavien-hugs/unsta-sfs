from src.config import settings


async def test_get_boto_client_success(mock_boto_client):

    from src.common.boto_client import get_boto_client

    mock_boto_instance = mock_boto_client.return_value
    boto_client = get_boto_client()

    mock_boto_client.assert_called_once()
    mock_boto_client.assert_called_once_with(
        "s3",
        endpoint_url=settings.STORAGE_HOST,
        aws_access_key_id=settings.STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.STORAGE_SECRET_KEY,
        region_name=settings.STORAGE_REGION_NAME,
    )
    assert boto_client is mock_boto_instance
