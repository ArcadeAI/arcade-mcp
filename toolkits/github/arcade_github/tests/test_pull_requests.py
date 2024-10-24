from unittest.mock import AsyncMock, patch

import pytest
from arcade_github.tools.models import (
    DiffSide,
    ReviewCommentSubjectType,
)
from arcade_github.tools.pull_requests import (
    create_reply_for_review_comment,
    create_review_comment,
    get_pull_request,
    list_pull_request_commits,
    list_pull_requests,
    list_review_comments_on_pull_request,
    update_pull_request,
)
from httpx import Response

from arcade.sdk.errors import RetryableToolError, ToolExecutionError


@pytest.fixture
def mock_context():
    context = AsyncMock()
    context.authorization.token = "mock_token"  # noqa: S105
    return context


@pytest.fixture
def mock_client():
    with patch("arcade_github.tools.pull_requests.httpx.AsyncClient") as client:
        yield client.return_value.__aenter__.return_value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "func,args,status_code,json_response,expected_result,error_message",
    [
        (list_pull_requests, ("owner", "repo"), 200, [], '{"pull_requests": []}', None),
        (
            get_pull_request,
            ("owner", "repo", 1),
            404,
            {"message": "Not Found"},
            None,
            "Error accessing.*: Resource not found",
        ),
        (
            update_pull_request,
            ("owner", "repo", 1, "New Title"),
            409,
            {"message": "Conflict"},
            None,
            "Error accessing.*: Failed to process request",
        ),
        (
            list_pull_request_commits,
            ("owner", "repo", 1),
            500,
            {"message": "Internal Server Error"},
            None,
            "Error accessing.*: Failed to process request",
        ),
        (
            list_review_comments_on_pull_request,
            ("owner", "repo", 1),
            403,
            {"message": "API rate limit exceeded"},
            None,
            "Error accessing.*: Forbidden",
        ),
    ],
)
async def test_pull_request_functions(
    mock_context,
    mock_client,
    func,
    args,
    status_code,
    json_response,
    expected_result,
    error_message,
):
    mock_client.get.return_value = mock_client.post.return_value = (
        mock_client.patch.return_value
    ) = Response(status_code, json=json_response)

    if error_message:
        with pytest.raises(ToolExecutionError, match=error_message):
            await func(mock_context, *args)
    else:
        result = await func(mock_context, *args)
        assert result == expected_result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "func,args,json_response,expected_assertions",
    [
        (
            list_pull_requests,
            ("owner", "repo"),
            [
                {
                    "number": 1,
                    "title": "Test PR",
                    "body": "This is a test PR",
                    "state": "open",
                    "html_url": "https://github.com/owner/repo/pull/1",
                    "created_at": "2023-05-01T12:00:00Z",
                    "updated_at": "2023-05-01T12:00:00Z",
                    "user": {"login": "testuser"},
                    "base": {"ref": "main"},
                    "head": {"ref": "feature-branch"},
                }
            ],
            ["Test PR", "https://github.com/owner/repo/pull/1"],
        ),
        (
            update_pull_request,
            ("owner", "repo", 1, "Updated PR Title", "Updated PR body"),
            {
                "number": 1,
                "title": "Updated PR Title",
                "body": "Updated PR body",
                "state": "open",
                "html_url": "https://github.com/owner/repo/pull/1",
                "created_at": "2023-05-01T12:00:00Z",
                "updated_at": "2023-05-02T12:00:00Z",
                "user": {"login": "testuser"},
            },
            ["Updated PR Title", "Updated PR body"],
        ),
        (
            list_pull_request_commits,
            ("owner", "repo", 1),
            [
                {
                    "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e",
                    "commit": {
                        "author": {
                            "name": "Test Author",
                            "email": "author@example.com",
                            "date": "2023-05-01T12:00:00Z",
                        },
                        "message": "Test commit message",
                    },
                }
            ],
            ["6dcb09b5b57875f334f61aebed695e2e4193db5e", "Test commit message"],
        ),
        (
            create_reply_for_review_comment,
            ("owner", "repo", 1, 42, "Thanks for the suggestion."),
            {
                "id": 123,
                "body": "Thanks for the suggestion.",
                "user": {"login": "testuser"},
                "created_at": "2023-05-02T12:00:00Z",
                "updated_at": "2023-05-02T12:00:00Z",
            },
            ["Thanks for the suggestion.", "testuser"],
        ),
        (
            list_review_comments_on_pull_request,
            ("owner", "repo", 1),
            [
                {
                    "id": 1,
                    "body": "Great changes!",
                    "user": {"login": "reviewer1"},
                    "created_at": "2023-05-01T12:00:00Z",
                    "updated_at": "2023-05-01T12:00:00Z",
                    "path": "file1.txt",
                    "line": 5,
                }
            ],
            ["Great changes!", "reviewer1", "file1.txt"],
        ),
        (
            get_pull_request,
            ("owner", "repo", 1, False, False),
            {
                "number": 1,
                "title": "Test PR",
                "body": "This is a test PR",
                "state": "open",
                "html_url": "https://github.com/owner/repo/pull/1",
                "created_at": "2023-05-01T12:00:00Z",
                "updated_at": "2023-05-01T12:00:00Z",
                "user": {"login": "testuser"},
                "base": {"ref": "main"},
                "head": {"ref": "feature-branch"},
            },
            ["Test PR", "https://github.com/owner/repo/pull/1"],
        ),
        (
            get_pull_request,
            ("owner", "repo", 1, True, False),
            {
                "number": 1,
                "title": "Test PR",
                "body": "This is a test PR",
                "state": "open",
                "html_url": "https://github.com/owner/repo/pull/1",
                "created_at": "2023-05-01T12:00:00Z",
                "updated_at": "2023-05-01T12:00:00Z",
                "user": {"login": "testuser"},
                "base": {"ref": "main"},
                "head": {"ref": "feature-branch"},
                "diff_content": "Sample diff content",
            },
            ["Test PR", "https://github.com/owner/repo/pull/1", "diff_content"],
        ),
        (
            create_review_comment,
            (
                "owner",
                "repo",
                1,
                "Great changes!",
                "file1.txt",
                "6dcb09b5b57875f334f61aebed695e2e4193db5e",
                1,
                2,
                DiffSide.RIGHT,
                None,
                ReviewCommentSubjectType.LINE,
            ),
            {
                "id": 1,
                "body": "Great changes!",
                "path": "file1.txt",
                "line": 2,
                "side": "RIGHT",
                "commit_id": "6dcb09b5b57875f334f61aebed695e2e4193db5e",
                "user": {"login": "testuser"},
                "created_at": "2023-05-01T12:00:00Z",
                "updated_at": "2023-05-01T12:00:00Z",
                "html_url": "https://github.com/owner/repo/pull/1#discussion_r1",
            },
            ["Great changes!", "file1.txt", "6dcb09b5b57875f334f61aebed695e2e4193db5e"],
        ),
    ],
)
async def test_pull_request_functions_success(
    mock_context, mock_client, func, args, json_response, expected_assertions
):
    mock_client.get.return_value = mock_client.post.return_value = (
        mock_client.patch.return_value
    ) = Response(200, json=json_response)

    result = await func(mock_context, *args)
    for assertion in expected_assertions:
        assert assertion in result


@pytest.mark.asyncio
async def test_create_review_comment_file_subject_type(mock_context, mock_client):
    mock_client.post.return_value = Response(
        200,
        json={
            "id": 1,
            "body": "File comment",
            "path": "file1.txt",
            "commit_id": "6dcb09b5b57875f334f61aebed695e2e4193db5e",
            "user": {"login": "testuser"},
            "created_at": "2023-05-01T12:00:00Z",
            "updated_at": "2023-05-01T12:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/1#discussion_r1",
        },
    )

    result = await create_review_comment(
        mock_context,
        "owner",
        "repo",
        1,
        "File comment",
        "file1.txt",
        "6dcb09b5b57875f334f61aebed695e2e4193db5e",
        subject_type=ReviewCommentSubjectType.FILE,
    )

    assert "File comment" in result
    assert "file1.txt" in result
    assert "6dcb09b5b57875f334f61aebed695e2e4193db5e" in result
    assert "start_line" not in mock_client.post.call_args[1]["json"]
    assert "end_line" not in mock_client.post.call_args[1]["json"]


@pytest.mark.asyncio
async def test_create_review_comment_missing_commit_id(mock_context, mock_client):
    mock_client.get.return_value = Response(
        200,
        json=[{"sha": "latest_commit_sha"}],
    )
    mock_client.post.return_value = Response(
        200,
        json={
            "id": 1,
            "body": "Comment with auto-fetched commit ID",
            "path": "file1.txt",
            "commit_id": "latest_commit_sha",
            "user": {"login": "testuser"},
            "created_at": "2023-05-01T12:00:00Z",
            "updated_at": "2023-05-01T12:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/1#discussion_r1",
        },
    )

    result = await create_review_comment(
        mock_context,
        "owner",
        "repo",
        1,
        "Comment with auto-fetched commit ID",
        "file1.txt",
        start_line=1,
        end_line=2,
    )

    assert "Comment with auto-fetched commit ID" in result
    assert "latest_commit_sha" in result
    assert mock_client.get.called
    assert mock_client.post.called


@pytest.mark.asyncio
async def test_create_review_comment_invalid_input(mock_context, mock_client):
    with pytest.raises(
        RetryableToolError, match="'start_line' and 'end_line' parameters are required"
    ):
        await create_review_comment(
            mock_context,
            "owner",
            "repo",
            1,
            "Invalid comment",
            "file1.txt",
            subject_type=ReviewCommentSubjectType.LINE,
        )


@pytest.mark.asyncio
async def test_create_review_comment_no_commits(mock_context, mock_client):
    mock_client.get.return_value = Response(200, json=[])

    with pytest.raises(RetryableToolError, match="Failed to get the latest commit SHA"):
        await create_review_comment(
            mock_context,
            "owner",
            "repo",
            1,
            "Comment with no commits",
            "file1.txt",
            start_line=1,
            end_line=2,
        )
