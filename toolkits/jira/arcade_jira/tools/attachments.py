from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Atlassian
from arcade.sdk.errors import ToolExecutionError

from arcade_jira.client import JiraClient
from arcade_jira.utils import build_file_data, clean_attachment_dict


@tool(requires_auth=Atlassian(scopes=["write:jira-work"]))
async def attach_file_to_issue(
    context: ToolContext,
    issue: Annotated[str, "The issue ID or key to add the attachment to"],
    filename: Annotated[
        str,
        "The name of the file to add as an attachment. The filename should contain the "
        "file extension (e.g. 'test.txt', 'report.pdf'), but it is not mandatory.",
    ],
    file_content_str: Annotated[
        str | None,
        "The string content of the file to attach. Use this if the file is a text file. "
        "Defaults to None.",
    ] = None,
    file_content_base64: Annotated[
        str | None,
        "The base64-encoded binary contents of the file. "
        "Use this for binary files like images or PDFs. Defaults to None.",
    ] = None,
    file_encoding: Annotated[
        str,
        "The encoding of the file to attach. Only used with file_content_str. Defaults to 'utf-8'.",
    ] = "utf-8",
    file_type: Annotated[
        str | None,
        "The type of the file to attach. E.g. 'application/pdf', 'text', 'image/png'. "
        "If not provided, the tool will try to infer the type from the filename. "
        "If the filename is not recognized, it will attach the file without specifying a type. "
        "Defaults to None (infer from filename or attach without type).",
    ] = None,
) -> Annotated[dict[str, Any], "Metadata about the attachment"]:
    """Add an attachment to an issue.

    Must provide exactly one of file_content_str or file_content_base64.
    """
    file_contents = [file_content_str, file_content_base64]

    if not any(file_contents) or all(file_contents):
        raise ToolExecutionError(
            "Must provide exactly one of file_content_str or file_content_base64."
        )

    if not filename:
        raise ToolExecutionError("Must provide a filename.")

    client = JiraClient(context.get_auth_token_or_empty())

    response = await client.post(
        f"/issue/{issue}/attachments",
        headers={
            # "Content-Type": "multipart/form-data",
            "X-Atlassian-Token": "no-check",
        },
        files=build_file_data(
            filename=filename,
            file_content_str=file_content_str,
            file_content_base64=file_content_base64,
            file_type=file_type,
            file_encoding=file_encoding,
        ),
    )

    return {
        "status": {
            "success": True,
            "message": f"Attachment '{filename}' successfully added to the issue '{issue}'",
        },
        "attachment": clean_attachment_dict(response[0]),
    }
