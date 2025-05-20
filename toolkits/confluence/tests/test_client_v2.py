from unittest.mock import patch

import pytest

from arcade_confluence.client import ConfluenceClientV2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "space_identifier, is_id",
    [
        (
            "12345",
            True,
        ),
        (
            "test-space",
            False,
        ),
    ],
)
async def test_get_space_id(space_identifier, is_id) -> None:
    with patch("arcade_confluence.client.ConfluenceClient._get_cloud_id", return_value=None):
        client_v2 = ConfluenceClientV2("fake-token")
        with patch(
            "arcade_confluence.client.ConfluenceClientV2.get_space_by_key",
            return_value={"space": {"id": "12345"}},
        ):
            space_id = await client_v2.get_space_id(space_identifier)
        if is_id:
            assert space_id == space_identifier
        else:
            assert space_id == "12345"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "page_identifier, is_id",
    [
        (
            "67890",
            True,
        ),
        (
            "test-page",
            False,
        ),
    ],
)
async def test_get_page_id(page_identifier, is_id) -> None:
    with patch("arcade_confluence.client.ConfluenceClient._get_cloud_id", return_value=None):
        client_v2 = ConfluenceClientV2("fake-token")
        with patch(
            "arcade_confluence.client.ConfluenceClientV2.get_page_by_title",
            return_value={"page": {"id": "67890"}},
        ):
            page_id = await client_v2.get_page_id(page_identifier)
        if is_id:
            assert page_id == page_identifier
        else:
            assert page_id == "67890"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "space_identifier, is_id",
    [
        (
            "12345",
            True,
        ),
        (
            "test-space",
            False,
        ),
    ],
)
async def test_get_space(space_identifier, is_id) -> None:
    with patch("arcade_confluence.client.ConfluenceClient._get_cloud_id", return_value=None):
        client_v2 = ConfluenceClientV2("fake-token")

        mock_space = {"space": {"id": "12345", "key": "TEST"}}

        with (
            patch(
                "arcade_confluence.client.ConfluenceClientV2.get_space_by_id",
                return_value=mock_space,
            ) as mock_by_id,
            patch(
                "arcade_confluence.client.ConfluenceClientV2.get_space_by_key",
                return_value=mock_space,
            ) as mock_by_key,
        ):
            result = await client_v2.get_space(space_identifier)

            if is_id:
                mock_by_id.assert_called_once_with(space_identifier)
                mock_by_key.assert_not_called()
            else:
                mock_by_id.assert_not_called()
                mock_by_key.assert_called_once_with(space_identifier)

            assert result == mock_space
