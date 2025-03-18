import pytest

from arcade_notion_toolkit.utils import simplify_search_result


@pytest.mark.parametrize(
    "item, expected_title",
    [
        # Case 1: Database object with top-level "title"
        (
            {
                "id": "db1",
                "object": "database",
                "title": [{"plain_text": "Database Title"}],
                "parent": {"type": "workspace", "workspace": True},
                "created_time": "2021-01-01T00:00:00.000Z",
                "last_edited_time": "2021-01-02T00:00:00.000Z",
                "url": "https://notion.so/database/db1",
                "public_url": "https://notion.so/database/public/db1",
            },
            "Database Title",
        ),
        # Case 2: Page object with properties "Title"
        (
            {
                "id": "page1",
                "object": "page",
                "properties": {
                    "Income Item": {
                        "id": "title",
                        "title": [
                            {
                                "annotations": {
                                    "bold": False,
                                    "code": False,
                                    "color": "default",
                                    "italic": False,
                                    "strikethrough": False,
                                    "underline": False,
                                },
                                "href": None,
                                "plain_text": "Page title with database parent",
                                "text": {
                                    "content": "Page title with database parent",
                                    "link": None,
                                },
                                "type": "text",
                            }
                        ],
                        "type": "title",
                    },
                },
                "parent": {"database_id": "db1"},
                "created_time": "2021-01-03T00:00:00.000Z",
                "last_edited_time": "2021-01-04T00:00:00.000Z",
                "url": "https://notion.so/page/page1",
                "public_url": "https://notion.so/page/public/page1",
            },
            "Page title with database parent",
        ),
        # Case 3: Page object with properties "title"
        (
            {
                "id": "page2",
                "object": "page",
                "properties": {"title": {"title": [{"plain_text": "Page Title from title prop"}]}},
                "parent": {"page_id": "parent_id"},
                "created_time": "2021-01-05T00:00:00.000Z",
                "last_edited_time": "2021-01-06T00:00:00.000Z",
                "url": "https://notion.so/page/page2",
                "public_url": "https://notion.so/page/public/page2",
            },
            "Page Title from title prop",
        ),
    ],
)
def test_simplify_search_result(item, expected_title):
    simplified = simplify_search_result(item)
    assert simplified["title"] == expected_title
    assert simplified["id"] == item.get("id")
    assert simplified["object"] == item.get("object")
    assert simplified["parent"] == item.get("parent")
    assert simplified["created_time"] == item.get("created_time")
    assert simplified["last_edited_time"] == item.get("last_edited_time")
    assert simplified["url"] == item.get("url")
    assert simplified["public_url"] == item.get("public_url")
