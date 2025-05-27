from typing import Optional, Union

import pytest
from arcade_core.utils import is_strict_optional


@pytest.mark.parametrize(
    "type_input, expected",
    [
        (Union[int, None], True),
        (Union[int, str, None], False),
        (Union[int, str], False),
        (Optional[int], True),
        (int | None, True),
        (None | int, True),
        (int | str, False),
        (int | str | None, False),
        (int, False),
        (str, False),
        (list, False),
        (dict, False),
    ],
)
def test_is_optional_type(type_input, expected):
    assert is_strict_optional(type_input) == expected
