def convert_structural_element(element: dict) -> str:
    if "sectionBreak" in element or "tableOfContents" in element:
        return ""

    elif "paragraph" in element:
        md = ""
        prepend, append = get_paragraph_style_tags(element["paragraph"]["paragraphStyle"])
        for item in element["paragraph"]["elements"]:
            content = extract_paragraph_content(item["textRun"])
            md += f"{prepend}{content}{append}"
        return md.replace("\n", "<br>")

    elif "table" in element:
        table = [
            [
                "".join([
                    convert_structural_element(cell_element) for cell_element in cell["content"]
                ])
                for cell in row["tableCells"]
            ]
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
    append = "\n" if content.endswith("\n") else ""
    content = content.rstrip("\n")
    italic = style.get("italic", False)
    bold = style.get("bold", False)
    if italic:
        content = f"<i>{content}</i>"
    if bold:
        content = f"<b>{content}</b>"
    return f"{content}{append}"


def get_paragraph_style_tags(style: dict) -> tuple[str, str]:
    named_style = style["namedStyleType"]
    if named_style == "NORMAL_TEXT":
        return "", ""
    elif named_style == "TITLE":
        return "<h1>", "</h1>"
    elif named_style == "SUBTITLE":
        return "<h2>", "</h2>"
    elif named_style.startswith("HEADING_"):
        try:
            heading_level = int(named_style.split("_")[1])
        except ValueError:
            return "", ""
        else:
            return f"<h{heading_level}>", f"</h{heading_level}>"
    return "", ""


def table_list_to_html(table: list[list[str]]) -> str:
    html = "<table>"
    for row in table:
        html += "<tr>"
        for cell in row:
            if cell.endswith("<br>"):
                cell = cell[:-4]
            html += f"<td>{cell}</td>"
        html += "</tr>"
    html += "</table>"
    return html
