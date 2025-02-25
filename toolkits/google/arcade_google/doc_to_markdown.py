import arcade_google.doc_to_html as doc_to_html


def convert_document_to_markdown(document: dict) -> str:
    md = f"---\ntitle: {document['title']}\ndocumentId: {document['documentId']}\n---\n"
    for element in document["body"]["content"]:
        md += convert_structural_element(element)
    return md


def convert_structural_element(element: dict) -> str:
    if "sectionBreak" in element or "tableOfContents" in element:
        return ""

    elif "paragraph" in element:
        md = ""
        prepend = get_paragraph_style_prepend_str(element["paragraph"]["paragraphStyle"])
        for item in element["paragraph"]["elements"]:
            if "textRun" not in item:
                continue
            content = extract_paragraph_content(item["textRun"])
            md += f"{prepend}{content}"
        return md

    elif "table" in element:
        return doc_to_html.convert_structural_element(element)

    else:
        raise ValueError(f"Unknown document body element type: {element}")


def extract_paragraph_content(text_run: dict) -> str:
    content = text_run["content"]
    style = text_run["textStyle"]
    return apply_text_style(content, style)


def apply_text_style(content: str, style: dict) -> str:
    append = "\n" if content.endswith("\n") else ""
    content = content.rstrip("\n")
    italic = style.get("italic", False)
    bold = style.get("bold", False)
    if italic:
        content = f"_{content}_"
    if bold:
        content = f"**{content}**"
    return f"{content}{append}"


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
