from unittest.mock import patch

import pytest

from arcade_confluence.client import ConfluenceClientV1


@pytest.mark.parametrize(
    "terms, phrases, enable_fuzzy, expected_cql",
    [
        (
            None,
            None,
            False,
            "",
        ),
        (
            ["foo", "bar"],
            None,
            False,
            '((text ~ "foo" OR title ~ "foo" OR space.title ~ "foo") OR (text ~ "bar" OR title ~ "bar" OR space.title ~ "bar"))',  # noqa: E501
        ),
        (
            ["foo"],
            ["man cho"],
            True,
            '((text ~ "foo~" OR title ~ "foo~" OR space.title ~ "foo~")) OR ((text ~ "man cho" OR title ~ "man cho" OR space.title ~ "man cho"))',  # noqa: E501
        ),
    ],
)
def test_construct_cql(terms, phrases, enable_fuzzy, expected_cql) -> None:
    with patch("arcade_confluence.client.ConfluenceClient._get_cloud_id", return_value=None):
        client_v1 = ConfluenceClientV1("fake-token")
        cql = client_v1.construct_cql(terms, phrases, enable_fuzzy)
        assert cql == expected_cql
