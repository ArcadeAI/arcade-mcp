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
