import pytest
from arcade.sdk.errors import ToolExecutionError

from arcade_reddit.utils import (
    create_fullname_for_comment,
    create_fullname_for_post,
    create_path_for_post,
    parse_get_content_of_post_response,
    parse_get_posts_in_subreddit_response,
    parse_get_top_level_comments_response,
)


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
        "title": None,
        "body": None,
        "author": None,
        "url": None,
        "permalink": None,
        "id": None,
        "name": None,
    }
    result = parse_get_content_of_post_response(data)
    assert result == expected


def test_parse_get_top_level_comments_response_missing_data():
    data = [{}]
    expected = {"comments": [], "num_comments": 0}
    result = parse_get_top_level_comments_response(data)
    assert result == expected
