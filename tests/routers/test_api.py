import pytest
from unittest import mock
from starlette import status

from src.config import settings
from botocore import exceptions
from src.common.error_codes import SfsErrorCodes


@pytest.mark.asyncio
async def test_ping_api(http_client_api):
    response = await http_client_api.get("/sfs/@ping")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json() == {"message": "pong !"}


@pytest.mark.asyncio
async def test_list_bucket(http_client_api, mock_boto_client, mock_bucket_data):
    mock_boto_client.list_buckets.return_value = mock_bucket_data

    response = await http_client_api.get("/storages")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["total"] >= 1
    assert response.json()["items"][0]["name"] == mock_bucket_data["Buckets"][0]["Name"]

    mock_boto_client.list_buckets.assert_called_once()


async def test_list_files_failure(http_client_api, mock_boto_client, fake_data):
    mock_boto_client.list_objects.side_effect = exceptions.ClientError(
        error_response={
            "Error": {
                "Code": "NoSuchBucket",
                "Message": "The specified bucket does not exist",
            }
        },
        operation_name="list_objects",
    )

    bucket_name = fake_data.name()
    response = await http_client_api.get("/storages", params={"bucket_name": f"{bucket_name}"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"items": [], "page": 1, "pages": 0, "size": None, "total": 0}


async def test_create_bucket(http_client_api, mock_boto_client, fake_data):
    mock_boto_client.create_bucket.return_value = mock.Mock()

    bucket_name = fake_data.name()
    response = await http_client_api.post("/storages", params={"bucket_name": bucket_name})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["message"] == f"Bucket '{bucket_name}' created successfully."

    mock_boto_client.create_bucket.assert_called_once_with(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": settings.STORAGE_REGION_NAME},
    )
    mock_boto_client.create_bucket.assert_called_once()


async def test_create_bucket_failure(http_client_api, mock_boto_client, fake_data):
    mock_boto_client.create_bucket.side_effect = exceptions.ClientError(
        error_response={"Error": {"Code": "BucketAlreadyExists"}},
        operation_name="create_bucket",
    )

    bucket_name = fake_data.name()
    response = await http_client_api.post("/storages", params={"bucket_name": bucket_name})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error_code"] == SfsErrorCodes.SFS_BUCKET_NAME_ALREADY_EXIST
    assert response.json()["error_message"] == "An error occurred"
    mock_boto_client.create_bucket.assert_called_once_with(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": settings.STORAGE_REGION_NAME},
    )


async def test_delete_bucket(http_client_api, mock_boto_client, fake_data):
    mock_boto_client.delete_bucket.return_value = mock.Mock()

    bucket_name = fake_data.name()
    response = await http_client_api.delete(f"/storages/{bucket_name}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == f"Bucket '{bucket_name}' deleted successfully."

    mock_boto_client.delete_bucket.assert_called_once_with(Bucket=bucket_name)
    mock_boto_client.delete_bucket.assert_called_once()


async def test_upload_file_bucket_success(http_client_api, mock_boto_client, fake_data):
    mock_boto_client.upload_file.return_value = None

    bucket_name = fake_data.name()
    response = await http_client_api.put(f"/storages/{bucket_name}", files={"file": ("sfs.txt", "test")})
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {"filename": "sfs.txt", "type": "text/plain"}

    mock_boto_client.upload_file.assert_called_once_with(Filename=mock.ANY, Bucket=bucket_name, Key="sfs.txt")
    mock_boto_client.upload_file.assert_called_once()


async def test_upload_file_bucket_not_found(http_client_api, mock_boto_client, fake_data):
    mock_boto_client.upload_file.side_effect = exceptions.ClientError(
        error_response={
            "Error": {
                "Code": "NoSuchBucket",
                "Message": "The specified bucket does not exist",
            }
        },
        operation_name="upload_file",
    )

    bucket_name = fake_data.name()
    response = await http_client_api.put(f"/storages/{bucket_name}", files={"file": ("sfs.txt", "test")})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error_code"] == SfsErrorCodes.SFS_INVALID_NAME
    assert response.json()["error_message"] == "The specified bucket does not exist"

    mock_boto_client.upload_file.assert_called_once_with(Filename=mock.ANY, Bucket=bucket_name, Key="sfs.txt")
    mock_boto_client.upload_file.assert_called_once()
