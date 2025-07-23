import pytest

# Simulates a single block with no children
fake_get_next_page_simple = (
    {
        "results": [
            {
                "object": "block",
                "id": "block1",
                "has_children": False,
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "plain_text": "Hello World",
                            "type": "text",
                            "text": {"content": "Hello World", "link": None},
                            "annotations": {
                                "bold": False,
                                "italic": False,
                                "underline": False,
                                "strikethrough": False,
                                "code": False,
                                "color": "default",
                            },
                            "href": None,
                        }
                    ]
                },
            }
        ]
    },
    False,
    None,
)

# Simulates a parent block with a child block
fake_get_next_page_nested = (
    {
        "results": [
            {
                "object": "block",
                "id": "parent_block",
                "has_children": True,
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "plain_text": "Parent Block",
                            "type": "text",
                            "text": {"content": "Parent Block", "link": None},
                            "annotations": {
                                "bold": False,
                                "italic": False,
                                "underline": False,
                                "strikethrough": False,
                                "code": False,
                                "color": "default",
                            },
                            "href": None,
                        }
                    ]
                },
            }
        ]
    },
    False,
    None,
)

fake_get_next_page_parent_block = (
    {
        "results": [
            {
                "object": "block",
                "id": "child_block",
                "has_children": False,
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "plain_text": "Child Block",
                            "type": "text",
                            "text": {"content": "Child Block", "link": None},
                            "annotations": {
                                "bold": False,
                                "italic": False,
                                "underline": False,
                                "strikethrough": False,
                                "code": False,
                                "color": "default",
                            },
                            "href": None,
                        }
                    ]
                },
            }
        ]
    },
    False,
    None,
)


@pytest.fixture
def setup_notion_pages(monkeypatch):
    from arcade_notion_toolkit.tools import pages

    monkeypatch.setattr(pages, "get_headers", lambda ctx: {"Authorization": "Bearer test"})
    monkeypatch.setattr(
        pages, "get_url", lambda endpoint, block_id=None: f"https://dummy/{block_id}"
    )
    return pages


@pytest.mark.asyncio
async def test_get_page_content_by_id_simple(mock_context, monkeypatch, setup_notion_pages):
    pages = setup_notion_pages

    # Patch get_object_metadata to return a dummy page with title 'Test Page'
    async def fake_get_object_metadata(context, object_id=None, **kwargs):
        return {
            "id": object_id,
            "object": "page",
            "properties": {"title": {"title": [{"plain_text": "Test Page"}]}},
        }

    monkeypatch.setattr(pages, "get_object_metadata", fake_get_object_metadata)

    # Patch get_next_page to
    async def fake_get_next_page(client, url, headers, params, cursor):
        return fake_get_next_page_simple

    monkeypatch.setattr(pages, "get_next_page", fake_get_next_page)

    # Call the function under test
    result = await pages.get_page_content_by_id(mock_context, "test_page_id")
    expected = "# Test Page\nHello World  \n"
    assert result == expected


@pytest.mark.asyncio
async def test_get_page_content_by_id_nested(mock_context, monkeypatch, setup_notion_pages):
    pages = setup_notion_pages

    # Patch get_object_metadata to return a dummy page with title 'Test Nested'
    async def fake_get_object_metadata(context, object_id=None, **kwargs):
        return {
            "id": object_id,
            "object": "page",
            "properties": {"title": {"title": [{"plain_text": "Test Nested"}]}},
        }

    monkeypatch.setattr(pages, "get_object_metadata", fake_get_object_metadata)

    # Patch get_next_page
    async def fake_get_next_page(client, url, headers, params, cursor):
        if url == "https://dummy/test_nested":
            return fake_get_next_page_nested
        elif url == "https://dummy/parent_block":
            return fake_get_next_page_parent_block
        return ({"results": []}, False, None)

    monkeypatch.setattr(pages, "get_next_page", fake_get_next_page)

    # Call the function under test
    result = await pages.get_page_content_by_id(mock_context, "test_nested")
    expected = "# Test Nested\nParent Block  \n    Child Block  \n"
    assert result == expected


@pytest.mark.asyncio
async def test_append_content_to_end_of_page_with_large_content(
    mock_context, monkeypatch, setup_notion_pages
):
    pages = setup_notion_pages

    # Mock is_page_id to return True
    monkeypatch.setattr(pages, "is_page_id", lambda x: True)

    # Create 150 dummy blocks (more than the 100 chunk size)
    dummy_blocks = []
    for i in range(150):
        dummy_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"Block {i}"}}]},
        })

    # Mock convert_markdown_to_blocks to return our 150 blocks
    def fake_convert_markdown_to_blocks(content):
        return dummy_blocks

    monkeypatch.setattr(pages, "convert_markdown_to_blocks", fake_convert_markdown_to_blocks)

    # Mock get_page_url to return a dummy URL
    async def fake_get_page_url(context, page_id):
        return f"https://notion.so/page/{page_id}"

    monkeypatch.setattr(pages, "get_page_url", fake_get_page_url)

    # Track the HTTP requests
    request_count = 0
    request_payloads = []

    class MockResponse:
        def raise_for_status(self):
            pass

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def patch(self, url, headers, json):
            nonlocal request_count
            request_count += 1
            request_payloads.append(json)
            return MockResponse()

    # Mock httpx.AsyncClient
    monkeypatch.setattr(pages.httpx, "AsyncClient", MockClient)

    _ = await pages.append_content_to_end_of_page(
        mock_context, "test_page_id", "Large content that will be converted to 150 blocks"
    )

    # Verify chunking behavior: 150 blocks should be split into 2 requests
    # First request: 100 blocks (0-99)
    # Second request: 50 blocks (100-149)
    assert request_count == 2
    assert len(request_payloads) == 2

    # Verify first chunk has 100 blocks
    first_chunk = request_payloads[0]["children"]
    assert len(first_chunk) == 100
    assert first_chunk[0]["paragraph"]["rich_text"][0]["text"]["content"] == "Block 0"
    assert first_chunk[99]["paragraph"]["rich_text"][0]["text"]["content"] == "Block 99"

    # Verify second chunk has 50 blocks
    second_chunk = request_payloads[1]["children"]
    assert len(second_chunk) == 50
    assert second_chunk[0]["paragraph"]["rich_text"][0]["text"]["content"] == "Block 100"
    assert second_chunk[49]["paragraph"]["rich_text"][0]["text"]["content"] == "Block 149"
