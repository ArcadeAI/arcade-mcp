import httpx
import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_reddit.client import RedditClient
from arcade_reddit.utils import (
    create_fullname_for_comment,
    create_fullname_for_multiple_posts,
    create_fullname_for_post,
    create_path_for_post,
    parse_get_content_of_multiple_posts_response,
    parse_get_content_of_post_response,
    parse_get_posts_in_subreddit_response,
    parse_get_top_level_comments_response,
    parse_subreddit_rules_response,
    parse_user_posts_response,
    resolve_subreddit_access,
)


class DummyRedditClientResponse:
    def __init__(self, status_code):
        self.status_code = status_code


@pytest.mark.parametrize(
    "identifier, expected",
    [
        ("abcdef", "t1_abcdef"),
        ("https://www.reddit.com/r/test/comments/1234567890/comment/1abcdef/", "t1_1abcdef"),
        ("t1_abcdef", "t1_abcdef"),
        ("/r/test/comments/1234567890/comment/1abcdef/", "t1_1abcdef"),
        ("not-an-id", pytest.raises(ToolExecutionError)),
        # Fullname: Invalid (not a Reddit comment id, but a Reddit post id)
        ("t2_abcdef", pytest.raises(ToolExecutionError)),
        # URL: Invalid (not a Reddit url to a comment, but to a post)
        ("https://www.reddit.com/r/test/comments/1234567890", pytest.raises(ToolExecutionError)),
        # Permalink: Invalid (not a Reddit permalink to a comment, but to a post)
        ("/r/test/comments/1234567890", pytest.raises(ToolExecutionError)),
    ],
)
def test_create_fullname_for_comment(identifier, expected) -> None:
    if isinstance(expected, str):
        assert create_fullname_for_comment(identifier) == expected
    else:
        with expected:
            create_fullname_for_comment(identifier)


@pytest.mark.parametrize(
    "identifier, expected",
    [
        ("https://www.reddit.com/r/test/comments/1234abc/", "/r/test/comments/1234abc/"),
        ("1234abc", "/comments/1234abc"),
        ("/r/test/comments/1234abc/", "/r/test/comments/1234abc/"),
        ("t3_1234abc", "/comments/1234abc"),
        # URL: invalid (non-reddit domain)
        ("https://www.example.com/r/test/comments/1234abc/", pytest.raises(ToolExecutionError)),
        # Post ID: invalid (non-alphanumeric character)
        ("12!abc", pytest.raises(ToolExecutionError)),
        # Permalink: invalid (missing the leading "/" so not recognized as a proper permalink)
        ("r/test/comments/1234abc/", pytest.raises(ToolExecutionError)),
        # Fullname: invalid (contains an illegal character)
        ("t3_1234*abc", pytest.raises(ToolExecutionError)),
    ],
)
def test_create_path_for_post(identifier, expected):
    if isinstance(expected, str):
        result = create_path_for_post(identifier)
        assert result == expected
    else:
        with expected:
            create_path_for_post(identifier)


@pytest.mark.parametrize(
    "identifier, expected",
    [
        ("https://www.reddit.com/r/test/comments/1234abc/", "t3_1234abc"),
        ("1234abc", "t3_1234abc"),
        ("/r/test/comments/1234abc/", "t3_1234abc"),
        ("t3_1234abc", "t3_1234abc"),
        # URL: invalid (missing "/comments/" segment)
        ("https://www.reddit.com/r/test/1234abc/", pytest.raises(ToolExecutionError)),
        # Post ID: invalid (non-alphanumeric)
        ("12!abc", pytest.raises(ToolExecutionError)),
        # Permalink: invalid (missing "/comments/" segment)
        ("/r/test/1234abc/", pytest.raises(ToolExecutionError)),
        # Fullname: invalid (type prefix is for a message, not a post
        ("t4_1234abc", pytest.raises(ToolExecutionError)),
    ],
)
def test_create_fullname_for_post(identifier, expected):
    if isinstance(expected, str):
        result = create_fullname_for_post(identifier)
        assert result == expected
    else:
        with expected:
            create_fullname_for_post(identifier)


@pytest.mark.parametrize(
    "identifiers, expected_fullnames, expected_warnings",
    [
        ([], [], []),
        (
            ["t3_1234abc", "https://www.reddit.com/r/test/comments/1234abc/"],
            ["t3_1234abc", "t3_1234abc"],
            [],
        ),
        (
            ["t3_1234abc", "not-a-valid-identifier"],
            ["t3_1234abc"],
            [
                {
                    "message": "'not-a-valid-identifier' is not a valid Reddit post identifier.",
                    "identifier": "not-a-valid-identifier",
                }
            ],
        ),
        (
            ["inv@lid", "not-a-valid-identifier"],
            [],
            [
                {
                    "message": "'inv@lid' is not a valid Reddit post identifier.",
                    "identifier": "inv@lid",
                },
                {
                    "message": "'not-a-valid-identifier' is not a valid Reddit post identifier.",
                    "identifier": "not-a-valid-identifier",
                },
            ],
        ),
    ],
)
def test_create_fullname_for_multiple_posts(identifiers, expected_fullnames, expected_warnings):
    actual_fullnames, actual_warnings = create_fullname_for_multiple_posts(identifiers)
    assert actual_fullnames == expected_fullnames
    assert actual_warnings == expected_warnings


def test_parse_get_posts_in_subreddit_response_empty():
    data = {}
    expected = {"cursor": None, "posts": []}
    result = parse_get_posts_in_subreddit_response(data)
    assert result == expected


def test_parse_get_content_of_post_response_empty_and_malformed():
    data = []
    result = parse_get_content_of_post_response(data)
    assert result == {}

    data = None
    result = parse_get_content_of_post_response(data)
    assert result == {}

    # missing expected keys
    data = [{}]
    expected = {
        "id": None,
        "name": None,
        "title": None,
        "author": None,
        "subreddit": None,
        "created_utc": None,
        "num_comments": None,
        "score": None,
        "upvote_ratio": None,
        "upvotes": None,
        "permalink": None,
        "url": None,
        "is_video": None,
        "body": None,
    }
    result = parse_get_content_of_post_response(data)
    assert result == expected


def test_parse_get_content_of_multiple_posts_response_empty_and_malformed():
    expected = []

    data = {}
    result = parse_get_content_of_multiple_posts_response(data)
    assert result == expected

    data = None
    result = parse_get_content_of_multiple_posts_response(data)
    assert result == expected

    data = [{}]
    result = parse_get_content_of_multiple_posts_response(data)
    assert result == expected


def test_parse_get_top_level_comments_response_missing_data():
    data = [{}]
    expected = {"comments": [], "num_comments": 0}
    result = parse_get_top_level_comments_response(data)
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code, expected_result, expected_exception",
    [
        (None, {"exists": True, "accessible": True}, None),
        (404, {"exists": False, "accessible": False}, None),
        (302, {"exists": False, "accessible": False}, None),
        (403, {"exists": True, "accessible": False}, None),
        (500, None, httpx.HTTPStatusError),
    ],
)
async def test_resolve_subreddit_access(status_code, expected_result, expected_exception):
    class DummyRedditClient(RedditClient):
        async def get(self, path: str, **kwargs):
            if status_code is not None:
                raise httpx.HTTPStatusError(
                    "Error", request=None, response=DummyRedditClientResponse(status_code)
                )
            return "dummy_success"

    client = DummyRedditClient(token="dummy")  # noqa: S106
    if expected_exception:
        with pytest.raises(expected_exception):
            await resolve_subreddit_access(client, "testsub")
    else:
        result = await resolve_subreddit_access(client, "testsub")
        assert result == expected_result


@pytest.mark.parametrize(
    "data, expected",
    [
        (
            {
                "rules": [
                    {"priority": 1, "short_name": "Rule1", "description": "Desc1"},
                    {"priority": 2, "short_name": "Rule2", "description": "Desc2"},
                ]
            },
            {
                "rules": [
                    {"priority": 1, "title": "Rule1", "body": "Desc1"},
                    {"priority": 2, "title": "Rule2", "body": "Desc2"},
                ]
            },
        ),
        ({}, {"rules": []}),
    ],
)
def test_parse_subreddit_rules_response(data, expected):
    result = parse_subreddit_rules_response(data)
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "posts_data, expected_cursor, expected_posts",
    [
        (
            {
                "data": {
                    "after": "cursor123",
                    "children": [
                        {
                            "data": {
                                "id": "1",
                                "name": "t3_1",
                                "title": "Post 1",
                                "author": "user1",
                                "subreddit": "subreddit1",
                                "created_utc": 1712345678,
                                "num_comments": 10,
                                "score": 100,
                                "upvote_ratio": 0.5,
                                "ups": 50,
                                "permalink": "permalink1",
                                "url": "url1",
                                "is_video": False,
                                "selftext": "This is the body of post 1",
                                "all_awardings": [],
                                "allow_live_comments": False,
                                "approved": False,
                                "approved_at_utc": None,
                            }
                        },
                    ],
                }
            },
            "cursor123",
            [
                {
                    "id": "1",
                    "name": "t3_1",
                    "title": "Post 1",
                    "author": "user1",
                    "subreddit": "subreddit1",
                    "created_utc": 1712345678,
                    "num_comments": 10,
                    "score": 100,
                    "upvote_ratio": 0.5,
                    "upvotes": 50,
                    "permalink": "permalink1",
                    "url": "url1",
                    "is_video": False,
                },
            ],
        ),
        ({"data": {"after": None, "children": []}}, None, []),
    ],
)
async def test_parse_user_posts_response_without_body(posts_data, expected_cursor, expected_posts):
    dummy_context = object()
    result = await parse_user_posts_response(dummy_context, posts_data, include_body=False)

    if expected_cursor:
        expected = {"cursor": expected_cursor, "posts": expected_posts}
    else:
        expected = {"posts": expected_posts}

    assert result == expected
