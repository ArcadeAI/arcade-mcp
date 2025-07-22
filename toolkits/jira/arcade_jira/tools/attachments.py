from typing import Annotated, Any, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian
from arcade_tdk.errors import ToolExecutionError

from arcade_jira.client import JiraClient
from arcade_jira.exceptions import NotFoundError
from arcade_jira.utils import build_file_data, clean_attachment_dict, resolve_cloud_id


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
    atlassian_cloud_id: Annotated[
        str | None,
        "The ID of the Atlassian Cloud to use (defaults to None). If not provided and the user has "
        "a single cloud authorized, the tool will use that. Otherwise, an error will be raised.",
    ] = None,
) -> Annotated[dict[str, Any], "Metadata about the attachment"]:
    """Add an attachment to an issue.

    Must provide exactly one of file_content_str or file_content_base64.
    """
    atlassian_cloud_id = await resolve_cloud_id(context, atlassian_cloud_id)
    file_contents = [file_content_str, file_content_base64]

    if not any(file_contents) or all(file_contents):
        raise ToolExecutionError(
            message="Must provide exactly one of file_content_str or file_content_base64."
        )

    if not filename:
        raise ToolExecutionError(message="Must provide a filename.")

    client = JiraClient(context=context, cloud_id=atlassian_cloud_id)

    response = await client.post(
        f"/issue/{issue}/attachments",
        headers={
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


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def list_issue_attachments_metadata(
    context: ToolContext,
    issue: Annotated[str, "The ID or key of the issue to retrieve"],
    atlassian_cloud_id: Annotated[
        str | None,
        "The ID of the Atlassian Cloud to use (defaults to None). If not provided and the user has "
        "a single cloud authorized, the tool will use that. Otherwise, an error will be raised.",
    ] = None,
) -> Annotated[dict, "Information about the issue"]:
    """Get the metadata about the files attached to an issue.

    This tool does NOT return the actual file contents. To get a file content,
    use the `Jira.DownloadAttachment` tool.
    """
    from arcade_jira.tools.issues import get_issue_by_id  # Avoid circular imports

    response = await get_issue_by_id(
        context=context,
        issue=issue,
        atlassian_cloud_id=atlassian_cloud_id,
    )
    if response.get("error"):
        return cast(dict, response)
    return {
        "issue": {
            "id": response["issue"]["id"],
            "key": response["issue"]["key"],
            "attachments": response["issue"]["attachments"],
        }
    }


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_attachment_metadata(
    context: ToolContext,
    attachment_id: Annotated[str, "The ID of the attachment to retrieve"],
    atlassian_cloud_id: Annotated[
        str | None,
        "The ID of the Atlassian Cloud to use (defaults to None). If not provided and the user has "
        "a single cloud authorized, the tool will use that. Otherwise, an error will be raised.",
    ] = None,
) -> Annotated[dict[str, Any], "The metadata of the attachment"]:
    """Get the metadata of an attachment."""
    atlassian_cloud_id = await resolve_cloud_id(context, atlassian_cloud_id)
    client = JiraClient(context=context, cloud_id=atlassian_cloud_id)
    try:
        response = await client.get(f"/attachment/{attachment_id}")
    except NotFoundError:
        return {"error": f"Attachment not found with ID '{attachment_id}'."}

    return {"attachment": clean_attachment_dict(response)}


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def download_attachment(
    context: ToolContext,
    attachment_id: Annotated[str, "The ID of the attachment to download"],
    atlassian_cloud_id: Annotated[
        str | None,
        "The ID of the Atlassian Cloud to use (defaults to None). If not provided and the user has "
        "a single cloud authorized, the tool will use that. Otherwise, an error will be raised.",
    ] = None,
) -> Annotated[dict[str, Any], "The content of the attachment"]:
    """Download the contents of an attachment associated with an issue."""
    atlassian_cloud_id = await resolve_cloud_id(context, atlassian_cloud_id)
    client = JiraClient(context=context, cloud_id=atlassian_cloud_id)

    attachment = await get_attachment_metadata(
        context=context,
        attachment_id=attachment_id,
        atlassian_cloud_id=atlassian_cloud_id,
    )

    if attachment.get("error"):
        return cast(dict, attachment)

    try:
        content = await client.get(
            f"/attachment/content/{attachment_id}",
            params={
                "redirect": False,
            },
        )
    except NotFoundError:
        return {"error": f"Attachment not found with ID '{attachment_id}'."}

    attachment["attachment"]["content"] = content["text"]

    return cast(dict, attachment)
