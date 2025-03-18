import pytest

from arcade_notion_toolkit.block_to_markdown_converter import BlockToMarkdownConverter


@pytest.mark.asyncio
async def test_convert_paragraph():
    block = {
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "plain_text": "Hello, world!",
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "code": False,
                        "strikethrough": False,
                        "underline": False,
                        "color": "default",
                    },
                    "text": {"content": "Hello, world!", "link": None},
                    "type": "text",
                }
            ],
            "color": "default",
        },
    }
    converter = BlockToMarkdownConverter(context=None)
    result = await converter.convert_block(block)
    assert result == "Hello, world!  \n"


@pytest.mark.asyncio
async def test_convert_heading_1():
    block = {
        "type": "heading_1",
        "heading_1": {
            "rich_text": [
                {
                    "plain_text": "Heading Test",
                    "annotations": {
                        "bold": True,
                        "italic": False,
                        "code": False,
                        "strikethrough": False,
                        "underline": False,
                        "color": "default",
                    },
                    "text": {"content": "Heading Test", "link": None},
                    "type": "text",
                }
            ],
            "color": "default",
        },
    }
    converter = BlockToMarkdownConverter(context=None)
    result = await converter.convert_block(block)
    expected = "# **Heading Test**  \n"
    assert result == expected


@pytest.mark.asyncio
async def test_convert_bulleted_list_item():
    block = {
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {
                    "plain_text": "list item",
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "code": False,
                        "strikethrough": False,
                        "underline": False,
                        "color": "default",
                    },
                    "text": {"content": "list item", "link": None},
                    "type": "text",
                }
            ],
            "color": "default",
        },
    }
    converter = BlockToMarkdownConverter(context=None)
    result = await converter.convert_block(block)
    expected = "- list item  \n"
    assert result == expected


@pytest.mark.asyncio
async def test_convert_equation():
    block = {"type": "equation", "equation": {"expression": "x+1=2"}}
    converter = BlockToMarkdownConverter(context=None)
    result = await converter.convert_block(block)
    expected = "$$ x+1=2 $$  \n"
    assert result == expected


@pytest.mark.asyncio
async def test_convert_child_page(monkeypatch):
    block = {
        "type": "child_page",
        "id": "child123",
        "child_page": {
            "rich_text": [
                {
                    "plain_text": "Child Title",
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "code": False,
                        "strikethrough": False,
                        "underline": False,
                        "color": "default",
                    },
                    "text": {"content": "Child Title", "link": None},
                    "type": "text",
                }
            ],
            "title": "Child Title",
        },
    }

    async def fake_get_page_url(context, block_id):
        return f"http://example.com/{block_id}"

    monkeypatch.setattr(
        "arcade_notion_toolkit.block_to_markdown_converter.get_page_url", fake_get_page_url
    )
    converter = BlockToMarkdownConverter(context=None)
    result = await converter.convert_block(block)
    expected = "[Child Title](http://example.com/child123)  \n"
    assert result == expected


@pytest.mark.asyncio
async def test_fallback_plaintext():
    block = {
        "type": "unsupported-type",
        "unsupported-type": {
            "rich_text": [
                {
                    "plain_text": "Fallback text",
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "code": False,
                        "strikethrough": False,
                        "underline": False,
                        "color": "default",
                    },
                    "text": {"content": "Fallback text", "link": None},
                    "type": "text",
                }
            ]
        },
    }
    converter = BlockToMarkdownConverter(context=None)
    result = await converter.convert_block(block)
    expected = "Fallback text"
    assert result == expected
