import pytest
from starlette import status
from src.common.error_codes import SfsErrorCodes


@pytest.mark.asyncio
async def test_get_all_media_without_data(http_client_api):
    response = await http_client_api.get("/media")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": None, "pages": 0}


@pytest.mark.asyncio
async def test_list_media_with_data(http_client_api, default_media):
    response = await http_client_api.get("/media")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["total"] >= 1
    assert response.json()["items"][0]["bucket_name"] == default_media.bucket_name


@pytest.mark.asyncio
async def test_list_media_filter(http_client_api, default_media, fake_data):
    # Test filter by bucket_name
    response = await http_client_api.get("/media", params={"bucket_name": f"{default_media.bucket_name}"})
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["items"][0]["bucket_name"] == default_media.bucket_name

    # Test filter by description
    response = await http_client_api.get("/media", params={"tags.tag": "value"})
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["items"][0]["tags"] == default_media.tags


@pytest.mark.asyncio
async def test_get_media_url(http_client_api, default_media):
    response = await http_client_api.get(f"/media/{default_media.bucket_name}/{default_media.filename}")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["url"] == default_media.url


@pytest.mark.skip
@pytest.mark.asyncio
async def test_get_media_url_download(http_client_api, default_media):
    response = await http_client_api.get(
        f"/media/{default_media.bucket_name}/{default_media.filename}", params={"download": True}
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["url"] == default_media.url


@pytest.mark.asyncio
async def test_get_media_view(http_client_api):
    response = await http_client_api.get("/media/filename")
    assert response.status_code == status.HTTP_200_OK, response.text


@pytest.mark.skip
@pytest.mark.asyncio
async def test_upload_media_success(http_client_api, default_bucket, fake_data):
    response = await http_client_api.post(
        "/media",
        data={"bucket_name": default_bucket.bucket_name, "tags": '{"tag": "value"}'},
        files={"file": ("test.txt", fake_data.text().encode("utf-8"))},
    )
    assert response.status_code == status.HTTP_201_CREATED, response.text
    assert response.json()["bucket_name"] == default_bucket.bucket_name
    assert response.json()["tags"] == {"tag": "value"}
    assert response.json()["url"] is not None


@pytest.mark.asyncio
async def test_upload_media_invalid_tags(http_client_api, default_bucket, fake_data):
    response = await http_client_api.post(
        "/media",
        data={"bucket_name": default_bucket.bucket_name, "tags": "invalid"},
        files={"file": ("test.txt", fake_data.text().encode("utf-8"))},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response.json()["error_code"] == SfsErrorCodes.SFS_INVALID_TAGS
    assert response.json()["error_message"] == "Invalid JSON string for tags."


@pytest.mark.skip
@pytest.mark.asyncio
async def test_upload_media_invalid_bucket_name(http_client_api, fake_data):
    response = await http_client_api.post(
        "/media",
        data={"bucket_name": "invalid", "tags": '{"tag": "value"}'},
        files={"file": ("test.txt", fake_data.text().encode("utf-8"))},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response.json()["error_code"] == SfsErrorCodes.SFS_BUCKET_NOT_FOUND
    assert response.json()["error_message"] == "Bucket not found."


@pytest.mark.asyncio
async def test_upload_media_invalid_file(http_client_api, default_bucket):
    response = await http_client_api.post(
        "/media",
        data={"bucket_name": default_bucket.bucket_name, "tags": "{'tag': 'value'}"},
        files={"file": ("fooooo", "foooo")},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response.json()["error_code"] == SfsErrorCodes.SFS_INVALID_TAGS
    assert response.json()["error_message"] == "Invalid JSON string for tags."


@pytest.mark.asyncio
async def test_delete_media(http_client_api, default_media):

    bucket_name, filename = default_media.bucket_name, default_media.filename

    response = await http_client_api.delete(f"/media/{bucket_name}/{filename}")
    assert response.status_code == status.HTTP_204_NO_CONTENT, response.text
