import asyncio
from typing import Any

from arcade_tdk import ToolContext

from arcade_notion_toolkit.block_to_markdown_converter import BlockToMarkdownConverter
from arcade_notion_toolkit.enums import BlockType


class BlockToStructuredConverter:
    """
    A converter class that transforms Notion blocks into structured data format.

    This converter preserves block IDs and hierarchical structure while also
    providing markdown content for each block.
    """

    def __init__(self, context: ToolContext):
        self.context = context
        self.markdown_converter = BlockToMarkdownConverter(context)

    async def convert_blocks_to_structured(
        self, blocks: list[dict[str, Any]], fetch_children_func
    ) -> list[dict[str, Any]]:
        """
        Convert a list of Notion blocks to structured format with parallel processing.

        Args:
            blocks: List of Notion blocks
            fetch_children_func: Async function to fetch child blocks for a given block ID

        Returns:
            List of structured block dictionaries
        """
        if not blocks:
            return []

        chunk_size = max(1, len(blocks) // 5)
        chunks = [blocks[i : i + chunk_size] for i in range(0, len(blocks), chunk_size)]

        # Process chunks in parallel
        chunk_results = await asyncio.gather(*[
            self._convert_chunk_to_structured(chunk, fetch_children_func) for chunk in chunks
        ])

        # Flatten results
        structured_blocks = []
        for chunk_result in chunk_results:
            structured_blocks.extend(chunk_result)

        return structured_blocks

    async def _convert_chunk_to_structured(
        self, blocks: list[dict[str, Any]], fetch_children_func
    ) -> list[dict[str, Any]]:
        """
        Convert a chunk of blocks to structured format.

        Args:
            blocks: Chunk of Notion blocks
            fetch_children_func: Async function to fetch child blocks

        Returns:
            List of structured block dictionaries for this chunk
        """
        structured_blocks = []

        for block in blocks:
            markdown_content = await self.markdown_converter.convert_block(block)

            structured_block = {
                "block_id": block.get("id", ""),
                "type": block.get("type", ""),
                "markdown_content": markdown_content.rstrip("\n") if markdown_content else "",
                "children": [],
            }

            # If the block has children and is not a child page, fetch and process them
            if block.get("has_children", False) and block.get("type") != BlockType.CHILD_PAGE.value:
                child_blocks = await fetch_children_func(block["id"])
                structured_block["children"] = await self.convert_blocks_to_structured(
                    child_blocks, fetch_children_func
                )

            structured_blocks.append(structured_block)

        return structured_blocks
