import json

import pytest

from arcade_teams.exceptions import MatchHumansByNameRetryableError
from arcade_teams.serializers import serialize_person, short_human
from arcade_teams.utils import (
    deduplicate_names,
    find_humans_by_name,
)


def test_deduplicate_names():
    names = ["John", "Jane", "John", "Jenifer"]
    assert deduplicate_names(names) == ["John", "Jane", "Jenifer"]

    names = ["John", "Jane", "JOHn", "Jenifer", "jane"]
    assert deduplicate_names(names) == ["John", "Jane", "Jenifer"]


class TestFindHumansByName:
    @pytest.mark.asyncio
    async def test_only_people_unique_exact_matches(
        self, mock_context, mock_client, person_factory, response_factory
    ):
        people = [
            person_factory(first_name="John", last_name="Smith"),
            person_factory(first_name="Jane", last_name="Foo"),
        ]

        mock_client.users.get.return_value = response_factory(value=[])
        mock_client.me.people.get.return_value = response_factory(value=people)

        result = await find_humans_by_name(
            context=mock_context,
            names=["John Smith", "Jane Foo"],
        )

        assert result == [
            serialize_person(people[0]),
            serialize_person(people[1]),
        ]

    @pytest.mark.asyncio
    async def test_only_people_multiple_exact_matches(
        self, mock_context, mock_client, person_factory, response_factory
    ):
        john_smith1 = person_factory(first_name="John", last_name="Smith")
        john_smith2 = person_factory(first_name="John", last_name="Smith")
        people = [
            john_smith1,
            person_factory(first_name="Jane", last_name="Foo"),
            john_smith2,
            person_factory(first_name="Jane", last_name="Bar"),
        ]

        mock_client.users.get.return_value = response_factory(value=[])
        mock_client.me.people.get.return_value = response_factory(value=people)

        with pytest.raises(MatchHumansByNameRetryableError) as error:
            await find_humans_by_name(
                context=mock_context,
                names=["John Smith", "Jane Foo"],
            )

        john_smith1_match = json.dumps(short_human(serialize_person(john_smith1), with_email=True))
        john_smith2_match = json.dumps(short_human(serialize_person(john_smith2), with_email=True))

        assert "John Smith" in error.value.message
        assert john_smith1_match in error.value.additional_prompt_content
        assert john_smith2_match in error.value.additional_prompt_content
        assert "Jane" not in error.value.message
        assert "Jane" not in error.value.additional_prompt_content
