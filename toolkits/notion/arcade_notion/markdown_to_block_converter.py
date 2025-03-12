import re
from typing import Any

# TODO: This is a partial implementation.
# TODO: Does not support children blocks. Instead, the markdown content is flattened.
# TODO: Does not support equation blocks.
# TODO: Does not support colored text styling.
# TODO: Does not support underline text styling.
# TODO: Does not support multiple text styles for the same block.


def convert_markdown_to_blocks(content: str) -> list[dict[str, Any]]:  # noqa: C901
    """Convert markdown content to Notion blocks."""
    blocks: list[dict[str, Any]] = []
    code_block: list[str] = []
    in_code: bool = False
    language: str = "plain text"
    numbered_list_index: int = 0

    for line in content.splitlines():
        line = line.strip()

        if line.startswith("```"):
            if in_code:
                blocks.append({
                    "type": "code",
                    "code": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "\n".join(code_block)},
                            }
                        ],
                        "language": language,
                    },
                })
                code_block = []
                in_code = False
            else:
                in_code = True
                language = line[3:].strip() or "plain text"
            continue

        if in_code:
            code_block.append(line)
            continue

        if not line:
            numbered_list_index = 0
            continue

        if line.startswith("### "):
            block_type, text = "heading_3", line[4:]
        elif line.startswith("## "):
            block_type, text = "heading_2", line[3:]
        elif line.startswith("# "):
            block_type, text = "heading_1", line[2:]
        elif numbered_match := re.match(r"(\d+)\.\s+(.+)", line):
            block_type, text = "numbered_list_item", numbered_match.group(2)
            numbered_list_index += 1
        elif line.startswith("- "):
            block_type, text = "bulleted_list_item", line[2:]
        elif line.startswith("> "):
            block_type, text = "quote", line[2:]
        elif line == "---":
            blocks.append({"type": "divider", "divider": {}})
            continue
        else:
            block_type, text = "paragraph", line

        blocks.append({"type": block_type, block_type: {"rich_text": format_text(text)}})

    return blocks


def format_text(text: str) -> list[dict[str, Any]]:
    """Convert text with markdown formatting to Notion rich text."""
    patterns = [
        (r"\[([^\]]+)\]\(([^\)]+)\)", "link"),  # [text](url)
        (r"\*\*(.*?)\*\*", "bold"),  # **bold**
        (r"__(.*?)__", "bold"),  # __bold__
        (r"\*(.*?)\*", "italic"),  # *italic*
        (r"_(.*?)_", "italic"),  # _italic_
        (r"~~(.*?)~~", "strikethrough"),  # ~~strikethrough~~
        (r"`(.*?)`", "code"),  # `code`
    ]

    rich_text = []
    last_index = 0
    combined_pattern = "|".join(f"({pattern})" for pattern, _ in patterns)

    for match in re.finditer(combined_pattern, text):
        start, end = match.span()
        if start > last_index:
            rich_text.append({
                "type": "text",
                "text": {"content": text[last_index:start]},
                "annotations": {
                    "bold": False,
                    "italic": False,
                    "strikethrough": False,
                    "underline": False,
                    "code": False,
                    "color": "default",
                },
            })

        matched_text = match.group(0)
        for pattern, format_type in patterns:
            if m := re.match(pattern, matched_text):
                if format_type == "link":
                    rich_text.append({
                        "type": "text",
                        "text": {
                            "content": m.group(1),
                            "link": {"url": m.group(2)},
                        },
                        "annotations": {
                            "bold": False,
                            "italic": False,
                            "strikethrough": False,
                            "underline": False,
                            "code": False,
                            "color": "default",
                        },
                    })
                else:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": m.group(1)},
                        "annotations": {
                            "bold": format_type == "bold",
                            "italic": format_type == "italic",
                            "strikethrough": format_type == "strikethrough",
                            "underline": False,
                            "code": format_type == "code",
                            "color": "default",
                        },
                    })
                break

        last_index = end

    if last_index < len(text):
        rich_text.append({
            "type": "text",
            "text": {"content": text[last_index:]},
            "annotations": {
                "bold": False,
                "italic": False,
                "strikethrough": False,
                "underline": False,
                "code": False,
                "color": "default",
            },
        })

    return rich_text
