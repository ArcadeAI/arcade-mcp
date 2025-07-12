import random
import string

import pytest


@pytest.fixture
def random_str_factory():
    def random_str_factory(
        length: int = 10,
    ) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))  # noqa: S311

    return random_str_factory


@pytest.fixture
def person_dict_factory(random_str_factory):
    def person_dict_factory(
        id_: str | None = None,
        display_name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> dict:
        first_name = first_name or f"first_{random_str_factory(4)}"
        last_name = last_name or f"last_{random_str_factory(4)}"
        display_name = display_name or f"{first_name} {last_name}"
        return {
            "id": id_ or random_str_factory(10),
            "name": {
                "display": display_name,
                "first": first_name,
                "last": last_name,
            },
        }

    return person_dict_factory
