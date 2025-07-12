import json

import pytest

from arcade_teams.exceptions import MultipleItemsFoundError
from arcade_teams.serializers import short_person
from arcade_teams.utils import build_people_by_name, get_person_match


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

    people = [
        person_dict_factory(first_name="John", last_name="Smith"),
        person_dict_factory(first_name="Jane", last_name="Foo"),
        person_dict_factory(first_name="John", last_name="Bar"),
        person_dict_factory(first_name="Jenifer", last_name="Smith"),
    ]

    people_by_last = build_people_by_name(people, "last")

    assert len(people_by_last) == 3
    assert people_by_last["smith"] == [people[0], people[3]]
    assert people_by_last["foo"] == [people[1]]
    assert people_by_last["bar"] == [people[2]]


def test_get_person_match(person_dict_factory):
    people = [
        person_dict_factory(first_name="John", last_name="Smith"),
        person_dict_factory(first_name="Jane", last_name="Foo"),
        person_dict_factory(first_name="John", last_name="Bar"),
        person_dict_factory(first_name="Jenifer", last_name="Smith"),
        person_dict_factory(first_name="Jane", last_name="Foo"),
    ]

    people_by_display = build_people_by_name(people, "display")

    assert get_person_match(people, people_by_display, "John Smith") == people[0]
    assert get_person_match(people, people_by_display, "John Bar") == people[2]
    assert get_person_match(people, people_by_display, "Jenifer Smith") == people[3]

    with pytest.raises(MultipleItemsFoundError) as error:
        get_person_match(people, people_by_display, "Jane Foo")

    assert "Multiple people found" in error.value.message
    assert "Jane Foo" in error.value.message
    assert json.dumps(short_person(people[1])) in error.value.additional_prompt_content
    assert json.dumps(short_person(people[4])) in error.value.additional_prompt_content
