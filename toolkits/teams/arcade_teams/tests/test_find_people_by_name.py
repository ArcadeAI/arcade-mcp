import json

import pytest

from arcade_teams.exceptions import MultipleItemsFoundError
from arcade_teams.serializers import serialize_person
from arcade_teams.utils import (
    build_people_by_name,
    deduplicate_names,
    find_people_by_name,
    get_person_match,
)


def test_deduplicate_names():
    names = ["John", "Jane", "John", "Jenifer"]
    assert deduplicate_names(names) == ["John", "Jane", "Jenifer"]

    names = ["John", "Jane", "JOHn", "Jenifer", "jane"]
    assert deduplicate_names(names) == ["John", "Jane", "Jenifer"]


def test_build_people_by_name(person_dict_factory):
    people = [
        person_dict_factory(first_name="John", last_name="Doe"),
        person_dict_factory(first_name="Jane", last_name="Doe"),
        person_dict_factory(first_name="John", last_name="Doe"),
        person_dict_factory(first_name="Jenifer", last_name="Doe"),
    ]

    people_by_display = build_people_by_name(people, "display")

    assert len(people_by_display) == 3
    assert people_by_display["john doe"] == [people[0], people[2]]
    assert people_by_display["jane doe"] == [people[1]]
    assert people_by_display["jenifer doe"] == [people[3]]

    people_by_first = build_people_by_name(people, "first")

    assert len(people_by_first) == 3
    assert people_by_first["john"] == [people[0], people[2]]
    assert people_by_first["jane"] == [people[1]]
    assert people_by_first["jenifer"] == [people[3]]

    john_without_last_name = person_dict_factory(first_name="John", last_name="Bar")
    del john_without_last_name["name"]["last"]

    people = [
        person_dict_factory(first_name="John", last_name="Smith"),
        person_dict_factory(first_name="Jane", last_name="Foo"),
        person_dict_factory(first_name="Jenifer", last_name="Smith"),
        john_without_last_name,
    ]

    people_by_last = build_people_by_name(people, "last")

    assert len(people_by_last) == 2
    assert people_by_last["smith"] == [people[0], people[2]]
    assert people_by_last["foo"] == [people[1]]


def test_get_person_match(person_dict_factory):
    people = [
        person_dict_factory(first_name="John", last_name="Smith"),
        person_dict_factory(first_name="Jane", last_name="Foo"),
        person_dict_factory(first_name="John", last_name="Bar"),
        person_dict_factory(first_name="Jenifer", last_name="Smith"),
        person_dict_factory(first_name="Jane", last_name="Foo"),
    ]

    people_by_display = build_people_by_name(people, "display")

    assert get_person_match(people_by_display, "John Smith") == people[0]
    assert get_person_match(people_by_display, "John Bar") == people[2]
    assert get_person_match(people_by_display, "Jenifer Smith") == people[3]

    with pytest.raises(MultipleItemsFoundError) as error:
        get_person_match(people_by_display, "Jane Foo")

    assert "Multiple people found" in error.value.message
    assert "Jane Foo" in error.value.message
    assert json.dumps(people[1]) in error.value.additional_prompt_content
    assert json.dumps(people[4]) in error.value.additional_prompt_content


@pytest.mark.asyncio
async def test_find_people_by_name_success(
    mock_context, mock_client, person_factory, response_factory
):
    people = [
        person_factory(first_name="John", last_name="Smith"),
        person_factory(first_name="Jane", last_name="Foo"),
        person_factory(first_name="John", last_name="Bar"),
        person_factory(first_name="Jenifer", last_name="Smith"),
        person_factory(first_name="Jane", last_name="Foo"),
        person_factory(first_name="Hello", last_name="World"),
        person_factory(first_name="Brown", last_name="Fox"),
    ]

    mock_client.me.people.get.return_value = response_factory(value=people)

    result = await find_people_by_name(
        mock_context, ["John Smith", "Jenifer Smith", "Do Not Exist", "HELLO", "FOx"]
    )

    assert result == {
        "people": [
            serialize_person(people[0]),
            serialize_person(people[3]),
            serialize_person(people[5]),
            serialize_person(people[6]),
        ],
        "not_found": ["Do Not Exist"],
        "not_matched": [
            serialize_person(people[1]),
            serialize_person(people[2]),
            serialize_person(people[4]),
        ],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "names",
    [
        ["Jane Foo", "John Smith"],
        ["John", "Not Found"],
        ["Bar"],
        ["Jane"],
    ],
)
async def test_find_people_by_name_success_ambiguous_matches(
    names, mock_context, mock_client, person_factory, response_factory
):
    people = [
        person_factory(first_name="John", last_name="Smith"),
        person_factory(first_name="Jane", last_name="Foo"),
        person_factory(first_name="John", last_name="Bar"),
        person_factory(first_name="Jenifer", last_name="Smith"),
        person_factory(first_name="Jane", last_name="Foo"),
        person_factory(first_name="Jane", last_name="Bar"),
    ]

    mock_client.me.people.get.return_value = response_factory(value=people)

    with pytest.raises(MultipleItemsFoundError) as error:
        await find_people_by_name(mock_context, names)

    assert "Multiple people found" in error.value.message
    assert names[0] in error.value.message
    assert "Available people" in error.value.additional_prompt_content
