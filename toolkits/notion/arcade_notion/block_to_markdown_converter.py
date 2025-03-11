import asyncio
from typing import Any, Optional

from arcade.sdk import ToolContext

from arcade_notion.enums import BlockType
from arcade_notion.utils import get_page_url


class BlockToMarkdownConverter:
    """
    A converter class that transforms Notion blocks into Markdown.

    The class registers conversion handlers for different Notion block types.
    If a block type does not have a handler, then the block's plain text is returned.
    """

    def __init__(self, context: ToolContext):
        self.context = context
        # block types whose conversion logic has been implemented
        # TODO: implement conversion logic for more block types
        self.handlers = {
            BlockType.BULLETED_LIST_ITEM.value: self._convert_bulleted_list_item,
            BlockType.EQUATION.value: self._convert_equation,
            BlockType.HEADING_1.value: self._convert_heading_1,
            BlockType.HEADING_2.value: self._convert_heading_2,
            BlockType.HEADING_3.value: self._convert_heading_3,
            BlockType.LINK_PREVIEW.value: self._convert_link_preview,
            BlockType.NUMBERED_LIST_ITEM.value: self._convert_numbered_list_item,
            BlockType.PARAGRAPH.value: self._convert_paragraph,
        }

    async def convert_block(self, block: dict[str, Any]) -> str:
        """
        Convert a single Notion block to a Markdown string

        Args:
            block (dict[str, Any]): A Notion block.

        Returns:
            str: A Markdown string.
        """
        block_type = block.get("type")
        if block_type in self.handlers:
            converter = self.handlers[block_type]
            if asyncio.iscoroutinefunction(converter):
                md: str = await converter(block)
                return md
            else:
                return converter(block)
        elif block_type == BlockType.CHILD_PAGE.value:
            return await self._convert_child_page(block)
        else:
            return self._get_plaintext(block)

    @staticmethod
    def rich_text_to_markdown(rich_text_items: list[dict[str, Any]]) -> str:
        """
        Convert a list of rich text items (from a Notion block) into Markdown.

        Handles formatting such as bold, italic, strikethrough, underline (via HTML),
        inline code, text coloring, hyperlinks, and equations.
        """
        md = ""
        for item in rich_text_items:
            annotations = item.get("annotations", {})
            type_val = item.get("type", "text")
            link = None

            # Special handling for inline equations.
            if type_val == "equation":
                expression = item.get("equation", {}).get("expression", "")
                md += f"${expression}$"
                continue

            if type_val == "text":
                text_obj = item.get("text", {})
                text = text_obj.get("content", "")
                link_obj = text_obj.get("link")
                link = (
                    link_obj.get("url")
                    if (link_obj and isinstance(link_obj, dict))
                    else item.get("href")
                )
            elif type_val == "mention":
                text = item.get("plain_text", "")
                link = item.get("href")
            else:
                text = item.get("plain_text", "")
                link = item.get("href")

            if text.strip() == "":
                continue

            # Apply annotation formatting.
            text = BlockToMarkdownConverter.apply_formatting(text, annotations, link)

            md += text

        return md

    @staticmethod
    def apply_formatting(text: str, annotations: dict[str, Any], link: Optional[str] = None) -> str:
        """Apply formatting to a text string based on the annotations.
        Used when converting rich text to markdown

        Args:
            text (str): The text to format.
            annotations (dict[str, Any]): The annotations to apply to the text.
            link (Optional[str]): An optional link for a hyperlink.

        Returns:
            str: The formatted text.
        """
        # If code block, wrap in backticks and skip other formatting.
        if annotations.get("code"):
            return f"`{text}`"

        # Add underline
        if annotations.get("underline"):
            text = f"<u>{text}</u>"

        # Apply color
        color = annotations.get("color", "default")
        if color != "default":
            text = f'<span style="color: {color};">{text}</span>'

        # Add bold, italic, and strikethrough
        markers = [
            marker
            for key, marker in (("bold", "**"), ("italic", "*"), ("strikethrough", "~~"))
            if annotations.get(key)
        ]
        if markers:
            text = "".join(markers) + text + "".join(reversed(markers))

        # Add hyperlink
        if link:
            text = f"[{text}]({link})"

        return text

    def _get_plaintext(self, block: dict[str, Any]) -> str:
        """
        Extract and return the plain text from a Notion block.
        This acts as a fallback for unsupported block types.
        """
        block_type: str = block.get("type", "")
        content = block.get(block_type, {})
        if isinstance(content, dict):
            rich_text_items = content.get("rich_text", [])
            return "".join(item.get("plain_text", "") for item in rich_text_items)
        return ""

    def _convert_text_block(self, block: dict[str, Any], element_key: str, prefix: str = "") -> str:
        """
        Helper method to convert a Notion block's rich_text element into a Markdown string.
        Optionally, a prefix (like a markdown list marker or heading hashes) is added.
        """
        element = block.get(element_key, {})
        rich_text_items = element.get("rich_text", [])
        text = self.rich_text_to_markdown(rich_text_items)
        return f"{prefix}{text}  \n"

    async def _convert_child_page(self, block: dict[str, Any]) -> str:
        """
        Asynchronously convert a child page block. This requires fetching the page's URL.
        """
        page_url = await get_page_url(self.context, block.get("id", ""))
        child_page = block.get("child_page", {})
        rich_text_items = child_page.get("rich_text", [])
        if rich_text_items:
            title = self.rich_text_to_markdown(rich_text_items)
        else:
            title = child_page.get("title", "")
        return f"[{title}]({page_url})  \n"

    def _convert_bulleted_list_item(self, block: dict[str, Any]) -> str:
        return self._convert_text_block(block, "bulleted_list_item", "- ")

    def _convert_equation(self, block: dict[str, Any]) -> str:
        expression = block.get("equation", {}).get("expression", "")
        return f"$$ {expression} $$  \n"

    def _convert_heading_1(self, block: dict[str, Any]) -> str:
        return self._convert_text_block(block, "heading_1", "# ")

    def _convert_heading_2(self, block: dict[str, Any]) -> str:
        return self._convert_text_block(block, "heading_2", "## ")

    def _convert_heading_3(self, block: dict[str, Any]) -> str:
        return self._convert_text_block(block, "heading_3", "### ")

    def _convert_link_preview(self, block: dict[str, Any]) -> str:
        return self._convert_text_block(block, "link_preview")

    def _convert_numbered_list_item(self, block: dict[str, Any]) -> str:
        return self._convert_text_block(block, "numbered_list_item", "1. ")

    def _convert_paragraph(self, block: dict[str, Any]) -> str:
        return self._convert_text_block(block, "paragraph")
