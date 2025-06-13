from unittest.mock import patch

import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_confluence.client import ConfluenceClientV1


@pytest.fixture
def client_v1() -> ConfluenceClientV1:
    """Fixture that provides a ConfluenceClientV1 instance with mocked cloud_id."""
    with patch("arcade_confluence.client.ConfluenceClient._get_cloud_id", return_value=None):
        return ConfluenceClientV1("fake-token")


@pytest.mark.parametrize(
    "query, enable_fuzzy, expected_cql",
    [
        ("foo", False, '(text ~ "foo" OR title ~ "foo" OR space.title ~ "foo")'),
        ("foo bar", False, '(text ~ "foo bar" OR title ~ "foo bar" OR space.title ~ "foo bar")'),
        ("foo", True, '(text ~ "foo~" OR title ~ "foo~" OR space.title ~ "foo~")'),
        ("foo bar", True, '(text ~ "foo bar" OR title ~ "foo bar" OR space.title ~ "foo bar")'),
    ],
)
def test_build_query_cql(client_v1: ConfluenceClientV1, query, enable_fuzzy, expected_cql) -> None:
    cql = client_v1._build_query_cql(query, enable_fuzzy)
    assert cql == expected_cql


@pytest.mark.parametrize(
    "queries, enable_fuzzy, expected_cql",
    [
        (
            ["foo", "foo bar"],
            False,
            '((text ~ "foo" OR title ~ "foo" OR space.title ~ "foo") AND (text ~ "foo bar" OR title ~ "foo bar" OR space.title ~ "foo bar"))',  # noqa: E501
        ),
        (
            ["foo", "foo bar"],
            True,
            '((text ~ "foo~" OR title ~ "foo~" OR space.title ~ "foo~") AND (text ~ "foo bar" OR title ~ "foo bar" OR space.title ~ "foo bar"))',  # noqa: E501
        ),
    ],
)
def test_build_and_cql(client_v1: ConfluenceClientV1, queries, enable_fuzzy, expected_cql) -> None:
    cql = client_v1._build_and_cql(queries, enable_fuzzy)
    assert cql == expected_cql


@pytest.mark.parametrize(
    "queries, enable_fuzzy, expected_cql",
    [
        (
            ["foo", "foo bar"],
            False,
            '((text ~ "foo" OR title ~ "foo" OR space.title ~ "foo") OR (text ~ "foo bar" OR title ~ "foo bar" OR space.title ~ "foo bar"))',  # noqa: E501
        ),
        (
            ["foo", "foo bar"],
            True,
            '((text ~ "foo~" OR title ~ "foo~" OR space.title ~ "foo~") OR (text ~ "foo bar" OR title ~ "foo bar" OR space.title ~ "foo bar"))',  # noqa: E501
        ),
    ],
)
def test_build_or_cql(client_v1: ConfluenceClientV1, queries, enable_fuzzy, expected_cql) -> None:
    cql = client_v1._build_or_cql(queries, enable_fuzzy)
    assert cql == expected_cql


@pytest.mark.parametrize(
    "must_contain_all, can_contain_any, enable_fuzzy, expected_cql",
    [
        (None, None, False, ""),
        (
            ["foo", "foo bar"],
            None,
            False,
            '((text ~ "foo" OR title ~ "foo" OR space.title ~ "foo") AND (text ~ "foo bar" OR title ~ "foo bar" OR space.title ~ "foo bar"))',  # noqa: E501
        ),
        (
            ["foo", "foo bar"],
            None,
            True,
            '((text ~ "foo~" OR title ~ "foo~" OR space.title ~ "foo~") AND (text ~ "foo bar" OR title ~ "foo bar" OR space.title ~ "foo bar"))',  # noqa: E501
        ),
        (
            None,
            ["foo", "foo bar"],
            False,
            '((text ~ "foo" OR title ~ "foo" OR space.title ~ "foo") OR (text ~ "foo bar" OR title ~ "foo bar" OR space.title ~ "foo bar"))',  # noqa: E501
        ),
        (
            None,
            ["foo", "foo bar"],
            True,
            '((text ~ "foo~" OR title ~ "foo~" OR space.title ~ "foo~") OR (text ~ "foo bar" OR title ~ "foo bar" OR space.title ~ "foo bar"))',  # noqa: E501
        ),
        (
            ["foo", "foo bar"],
            ["foo", "foo bar"],
            False,
            '(((text ~ "foo" OR title ~ "foo" OR space.title ~ "foo") AND (text ~ "foo bar" OR title ~ "foo bar" OR space.title ~ "foo bar")) AND ((text ~ "foo" OR title ~ "foo" OR space.title ~ "foo") OR (text ~ "foo bar" OR title ~ "foo bar" OR space.title ~ "foo bar")))',  # noqa: E501
        ),
        (
            ["foo", "foo bar"],
            ["foo", "foo bar"],
            True,
            '(((text ~ "foo~" OR title ~ "foo~" OR space.title ~ "foo~") AND (text ~ "foo bar" OR title ~ "foo bar" OR space.title ~ "foo bar")) AND ((text ~ "foo~" OR title ~ "foo~" OR space.title ~ "foo~") OR (text ~ "foo bar" OR title ~ "foo bar" OR space.title ~ "foo bar")))',  # noqa: E501
        ),
    ],
)
def test_construct_cql(
    client_v1: ConfluenceClientV1, must_contain_all, can_contain_any, enable_fuzzy, expected_cql
) -> None:
    if not expected_cql:
        with pytest.raises(ToolExecutionError):
            client_v1.construct_cql(must_contain_all, can_contain_any, enable_fuzzy)
    else:
        cql = client_v1.construct_cql(must_contain_all, can_contain_any, enable_fuzzy)
        assert cql == expected_cql
