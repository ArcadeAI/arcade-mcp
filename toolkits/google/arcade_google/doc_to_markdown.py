def convert_document_to_markdown(document: dict) -> str:
    md = ""
    for element in document["body"]["content"]:
        md += convert_structural_element(element)
    return md


def convert_structural_element(element: dict) -> str:
    if "sectionBreak" in element or "tableOfContents" in element:
        return ""

    elif "paragraph" in element:
        md = ""
        for item in element["paragraph"]["elements"]:
            prepend = get_paragraph_style_prepend_str(item["paragraphStyle"])
            content = extract_paragraph_content(item["textRun"])
            md += f"{prepend}{content}"
        return md

    elif "table" in element:
        table = [
            [convert_structural_element(cell) for cell in row["tableCells"]]
            for row in element["table"]["tableRows"]
        ]
        return table_list_to_html(table)

    else:
        raise ValueError(f"Unknown document body element type: {element}")


def extract_paragraph_content(text_run: dict) -> str:
    content = text_run["content"]
    style = text_run["textStyle"]
    return apply_text_style(content, style)


def apply_text_style(content: str, style: dict) -> str:
    italic = style.get("italic", False)
    bold = style.get("bold", False)
    if italic:
        content = f"_{content}_"
    if bold:
        content = f"**{content}**"
    return content


def get_paragraph_style_prepend_str(style: dict) -> str:
    named_style = style["namedStyleType"]
    if named_style == "NORMAL_TEXT":
        return ""
    elif named_style == "TITLE":
        return "# "
    elif named_style == "SUBTITLE":
        return "## "
    elif named_style.startswith("HEADING_"):
        try:
            heading_level = int(named_style.split("_")[1])
            return f"{'#' * heading_level} "
        except ValueError:
            return ""
    return ""


def table_list_to_html(table: list[list[str]]) -> str:
    return (
        "<table>"
        + "".join([f"<tr>{''.join([f'<td>{cell}</td>' for cell in row])}</tr>" for row in table])
        + "</table>"
    )
