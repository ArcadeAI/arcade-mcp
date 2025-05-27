from typing import Optional, Union

import pytest
from arcade_core.utils import is_union


@pytest.mark.parametrize(
    "type_input, expected",
    [
        (Union[int, str], True),
        (Optional[int], True),  # Optional[int] is equivalent to Union[int, None]
        (int | str, True),
        (int | None, True),  # int | None is equivalent to Optional[int]
        (int, False),
        (str, False),
        (list, False),
        (dict, False),
    ],
)
def test_is_union(type_input, expected):
    assert is_union(type_input) == expected
