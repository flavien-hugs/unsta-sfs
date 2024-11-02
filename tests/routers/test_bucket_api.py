from unittest import mock

import pytest
from botocore import exceptions
from starlette import status

from src.common.error_codes import SfsErrorCodes
from src.config import settings


@pytest.mark.asyncio
async def test_ping_api(http_bucket_api):
    response = await http_bucket_api.get("/sfs/@ping")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json() == {"message": "pong !"}


@pytest.mark.asyncio
async def test_create_bucket_success(http_bucket_api, mock_boto_client, default_bucket, bucket_data):
    bucket_data.update({"bucket_name": "storage-unsta-pictures"})

    # Simuler que le bucket n'existe pas en levant une exception 404
    mock_boto_client.head_bucket.side_effect = exceptions.ClientError(
        error_response={"Error": {"Code": "404", "Message": "Not Found"}}, operation_name="HeadBucket"
    )

    # Simuler la création réussie du bucket
    mock_boto_client.create_bucket.return_value = {}
    mock_boto_client.put_bucket_policy.return_value = {}

    response = await http_bucket_api.post("/buckets", json=bucket_data)

    assert response.status_code == status.HTTP_201_CREATED, response.text
    assert response.json()["bucket_name"] == bucket_data.get("bucket_name")

    mock_boto_client.head_bucket.assert_called_once()
    mock_boto_client.head_bucket.assert_called_once_with(Bucket=bucket_data.get("bucket_name"))
    mock_boto_client.create_bucket.assert_called_once()
    mock_boto_client.create_bucket.assert_called_once_with(
        Bucket=bucket_data.get("bucket_name"), CreateBucketConfiguration={"LocationConstraint": settings.STORAGE_REGION_NAME}
    )


async def test_create_bucket_failure(http_bucket_api, mock_boto_client, bucket_data):
    mock_boto_client.head_bucket.side_effect = exceptions.ClientError(
        error_response={"Error": {"Code": "400", "Message": "Error checking bucket"}}, operation_name="HeadBucket"
    )

    bucket_data.update({"bucket_name": "storage-pictures"})
    response = await http_bucket_api.post("/buckets", json=bucket_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response.json()["error_code"] == SfsErrorCodes.SFS_INVALID_NAME
    assert response.json()["error_message"] == (
        "An error occurred (400) when calling the HeadBucket operation: " "Error checking bucket"
    )

    mock_boto_client.head_bucket.assert_called_once_with(Bucket="storage-pictures")


@pytest.mark.asyncio
async def test_list_bucket_with_data(http_bucket_api, mock_boto_client, default_bucket):
    response = await http_bucket_api.get("/buckets")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["total"] >= 1
    assert response.json()["items"][0]["bucket_name"] == default_bucket.bucket_name


@pytest.mark.asyncio
async def test_list_bucket_without_data(http_bucket_api, mock_boto_client):
    response = await http_bucket_api.get("/buckets")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": None, "pages": 0}


@pytest.mark.asyncio
async def test_list_filter(http_bucket_api, mock_boto_client, default_bucket, fake_data):
    # Test filter by bucket_name
    response = await http_bucket_api.get("/buckets", params={"bucket_name": f"{default_bucket.bucket_name}"})
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["items"][0]["bucket_name"] == default_bucket.bucket_name

    # Test filter by description
    response = await http_bucket_api.get("/buckets", params={"description": default_bucket.description})
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["items"][0]["description"] == default_bucket.description

    # Test filter by created_at
    query_date = fake_data.date()
    response = await http_bucket_api.get("/buckets", params={"created_at": query_date})
    assert response.status_code == status.HTTP_200_OK, response.text
    assert "items" in response.json()


@pytest.mark.asyncio
async def test_get_bucket_and_create_bucket_if_not_exist(http_bucket_api, mock_boto_client):
    # Simuler que le bucket n'existe pas en levant une exception 404
    mock_boto_client.head_bucket.side_effect = exceptions.ClientError(
        error_response={"Error": {"Code": "404", "Message": "Not Found"}}, operation_name="HeadBucket"
    )

    # Simuler la création réussie du bucket
    mock_boto_client.create_bucket.return_value = {}
    mock_boto_client.put_bucket_policy.return_value = {}

    response = await http_bucket_api.get("/buckets/unsta-pictures", params={"create_bucket_if_not_exist": True})
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["bucket_name"] == "unsta-pictures"

    mock_boto_client.head_bucket.assert_called_once()
    mock_boto_client.head_bucket.assert_called_once_with(Bucket="unsta-pictures")
    mock_boto_client.create_bucket.assert_called_once()
    mock_boto_client.create_bucket.assert_called_once_with(
        Bucket="unsta-pictures", CreateBucketConfiguration={"LocationConstraint": settings.STORAGE_REGION_NAME}
    )


@pytest.mark.asyncio
async def test_get_bucket_and_create_bucket_if_exist(http_bucket_api, mock_boto_client, default_bucket):
    response = await http_bucket_api.get(f"/buckets/{default_bucket.bucket_name}", params={"create_bucket_if_not_exist": False})
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response.json()["error_code"] == SfsErrorCodes.SFS_BUCKET_NOT_FOUND
    assert response.json()["error_message"] == f"Bucket '{default_bucket.bucket_name}' not found."


@pytest.mark.asyncio
async def test_delete_bucket(http_bucket_api, mock_boto_client, default_bucket):
    mock_boto_client.delete_bucket.return_value = mock.Mock()

    response = await http_bucket_api.delete(f"/buckets/{default_bucket.bucket_name}")

    assert response.status_code == status.HTTP_200_OK, response.text

    mock_boto_client.delete_bucket.assert_called_once()
    mock_boto_client.delete_bucket.assert_called_once_with(Bucket=default_bucket.bucket_name)
