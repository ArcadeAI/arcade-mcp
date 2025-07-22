import json
from collections.abc import Callable
from typing import cast
from unittest.mock import Mock

import pytest
from arcade_tdk import ToolContext

from arcade_teams.exceptions import MatchHumansByNameRetryableError
from arcade_teams.serializers import serialize_person, serialize_user, short_human
from arcade_teams.utils import (
    deduplicate_names,
    find_humans_by_name,
)


def test_deduplicate_names() -> None:
    names = ["John", "Jane", "John", "Jenifer"]
    assert deduplicate_names(names) == ["John", "Jane", "Jenifer"]

    names = ["John", "Jane", "JOHn", "Jenifer", "jane"]
    assert deduplicate_names(names) == ["John", "Jane", "Jenifer"]


class TestFindPeopleByName:
    @pytest.mark.asyncio
    async def test_unique_exact_matches(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        person_factory: Callable,
        response_factory: Callable,
    ) -> None:
        people = [
            person_factory(first_name="John", last_name="Smith"),
            person_factory(first_name="John", last_name="Smitho"),
            person_factory(first_name="Jane", last_name="Foo"),
            person_factory(first_name="Jane", last_name="Foobar"),
        ]

        mock_client.users.get.return_value = response_factory(value=[])
        mock_client.me.people.get.return_value = response_factory(value=people)

        result = await find_humans_by_name(
            context=mock_context,
            names=["John Smith", "Jane Foo"],
        )

        assert result == [
            serialize_person(people[0]),
            serialize_person(people[2]),
        ]

    @pytest.mark.asyncio
    async def test_multiple_exact_matches(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        person_factory: Callable,
        response_factory: Callable,
    ) -> None:
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

        assert "John Smith" in cast(str, error.value.message)
        assert john_smith1_match in cast(str, error.value.additional_prompt_content)
        assert john_smith2_match in cast(str, error.value.additional_prompt_content)
        assert "Jane" not in cast(str, error.value.message)
        assert "Jane" not in cast(str, error.value.additional_prompt_content)

    @pytest.mark.asyncio
    async def test_multiple_exact_matches_and_partial_matches(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        person_factory: Callable,
        response_factory: Callable,
    ) -> None:
        john_smith1 = person_factory(first_name="John", last_name="Smith")
        john_smith2 = person_factory(first_name="John", last_name="Smith")
        hello_world = person_factory(first_name="Hello", last_name="World")
        people = [
            john_smith1,
            person_factory(first_name="Jane", last_name="Foo"),
            john_smith2,
            person_factory(first_name="Jane", last_name="Bar"),
            hello_world,
        ]

        mock_client.users.get.return_value = response_factory(value=[])
        mock_client.me.people.get.return_value = response_factory(value=people)

        with pytest.raises(MatchHumansByNameRetryableError) as error:
            await find_humans_by_name(
                context=mock_context,
                names=["John Smith", "Jane Foo", "Hello"],
            )

        john_smith1_match = json.dumps(short_human(serialize_person(john_smith1), with_email=True))
        john_smith2_match = json.dumps(short_human(serialize_person(john_smith2), with_email=True))
        hello_world_match = json.dumps(short_human(serialize_person(hello_world), with_email=True))

        assert "John Smith" in cast(str, error.value.message)
        assert john_smith1_match in cast(str, error.value.additional_prompt_content)
        assert john_smith2_match in cast(str, error.value.additional_prompt_content)

        assert "Jane" not in cast(str, error.value.message)
        assert "Jane" not in cast(str, error.value.additional_prompt_content)

        assert "Hello" in cast(str, error.value.message)
        assert hello_world_match in cast(str, error.value.additional_prompt_content)

    @pytest.mark.asyncio
    async def test_one_partial_match(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        person_factory: Callable,
        response_factory: Callable,
    ) -> None:
        hello_world = person_factory(first_name="Hello", last_name="World")
        people = [
            person_factory(first_name="John", last_name="Smith"),
            person_factory(first_name="Jack", last_name="Smith"),
            person_factory(first_name="Jane", last_name="Foo"),
            person_factory(first_name="Jane", last_name="Bar"),
            hello_world,
        ]

        mock_client.users.get.return_value = response_factory(value=[])
        mock_client.me.people.get.return_value = response_factory(value=people)

        with pytest.raises(MatchHumansByNameRetryableError) as error:
            await find_humans_by_name(
                context=mock_context,
                names=["John Smith", "Jane Foo", "Hello"],
            )

        hello_world_match = json.dumps(short_human(serialize_person(hello_world), with_email=True))

        assert "John" not in cast(str, error.value.message)
        assert "Jane" not in cast(str, error.value.message)
        assert "Jane" not in cast(str, error.value.additional_prompt_content)

        assert "Hello" in cast(str, error.value.message)
        assert hello_world_match in cast(str, error.value.additional_prompt_content)

    @pytest.mark.asyncio
    async def test_multiple_partial_matches(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        person_factory: Callable,
        response_factory: Callable,
    ) -> None:
        jane_foo = person_factory(first_name="Jane", last_name="Foo")
        jane_bar = person_factory(first_name="Jane", last_name="Bar")
        hello_world = person_factory(first_name="Hello", last_name="World")
        people = [
            person_factory(first_name="John", last_name="Smith"),
            person_factory(first_name="Jack", last_name="Smith"),
            jane_foo,
            jane_bar,
            hello_world,
        ]

        mock_client.users.get.return_value = response_factory(value=[])
        mock_client.me.people.get.return_value = response_factory(value=people)

        with pytest.raises(MatchHumansByNameRetryableError) as error:
            await find_humans_by_name(
                context=mock_context,
                names=["John Smith", "Jane", "Hello"],
            )

        hello_world_match = json.dumps(short_human(serialize_person(hello_world), with_email=True))
        jane_foo_match = json.dumps(short_human(serialize_person(jane_foo), with_email=True))
        jane_bar_match = json.dumps(short_human(serialize_person(jane_bar), with_email=True))

        assert "John" not in cast(str, error.value.message)
        assert "Smith" not in cast(str, error.value.message)

        assert "Jane" in cast(str, error.value.message)
        assert jane_foo_match in cast(str, error.value.additional_prompt_content)
        assert jane_bar_match in cast(str, error.value.additional_prompt_content)

        assert "Hello" in cast(str, error.value.message)
        assert hello_world_match in cast(str, error.value.additional_prompt_content)

    @pytest.mark.asyncio
    async def test_zero_matches(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        person_factory: Callable,
        response_factory: Callable,
    ) -> None:
        people = [
            person_factory(first_name="John", last_name="Smith"),
            person_factory(first_name="Jane", last_name="Foo"),
        ]

        mock_client.users.get.return_value = response_factory(value=[])
        mock_client.me.people.get.return_value = response_factory(value=people)

        with pytest.raises(MatchHumansByNameRetryableError) as error:
            await find_humans_by_name(
                context=mock_context,
                names=["Whatever", "Does Not Exist"],
            )

        assert "Whatever" in cast(str, error.value.message)
        assert "Does Not Exist" in cast(str, error.value.message)
        # Since there are no matches, there should be no additional prompt
        assert error.value.additional_prompt_content is None


class TestFindUsersByName:
    @pytest.mark.asyncio
    async def test_unique_exact_matches(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        user_factory: Callable,
        response_factory: Callable,
    ) -> None:
        users = [
            user_factory(first_name="John", last_name="Smith"),
            user_factory(first_name="John", last_name="Smitho"),
            user_factory(first_name="Jane", last_name="Foo"),
            user_factory(first_name="Jane", last_name="Foobar"),
        ]

        mock_client.users.get.return_value = response_factory(value=users)
        mock_client.me.people.get.return_value = response_factory(value=[])

        result = await find_humans_by_name(
            context=mock_context,
            names=["John Smith", "Jane Foo"],
        )

        assert result == [
            serialize_user(users[0]),
            serialize_user(users[2]),
        ]

    @pytest.mark.asyncio
    async def test_multiple_exact_matches(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        user_factory: Callable,
        response_factory: Callable,
    ) -> None:
        john_smith1 = user_factory(first_name="John", last_name="Smith")
        john_smith2 = user_factory(first_name="John", last_name="Smith")
        users = [
            john_smith1,
            user_factory(first_name="Jane", last_name="Foo"),
            john_smith2,
            user_factory(first_name="Jane", last_name="Bar"),
        ]

        mock_client.users.get.return_value = response_factory(value=users)
        mock_client.me.people.get.return_value = response_factory(value=[])

        with pytest.raises(MatchHumansByNameRetryableError) as error:
            await find_humans_by_name(
                context=mock_context,
                names=["John Smith", "Jane Foo"],
            )

        john_smith1_match = json.dumps(short_human(serialize_user(john_smith1), with_email=True))
        john_smith2_match = json.dumps(short_human(serialize_user(john_smith2), with_email=True))

        assert "John Smith" in cast(str, error.value.message)
        assert john_smith1_match in cast(str, error.value.additional_prompt_content)
        assert john_smith2_match in cast(str, error.value.additional_prompt_content)
        assert "Jane" not in cast(str, error.value.message)
        assert "Jane" not in cast(str, error.value.additional_prompt_content)

    @pytest.mark.asyncio
    async def test_multiple_exact_matches_and_partial_matches(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        user_factory: Callable,
        response_factory: Callable,
    ) -> None:
        john_smith1 = user_factory(first_name="John", last_name="Smith")
        john_smith2 = user_factory(first_name="John", last_name="Smith")
        hello_world = user_factory(first_name="Hello", last_name="World")
        users = [
            john_smith1,
            user_factory(first_name="Jane", last_name="Foo"),
            john_smith2,
            user_factory(first_name="Jane", last_name="Bar"),
            hello_world,
        ]

        mock_client.users.get.return_value = response_factory(value=users)
        mock_client.me.people.get.return_value = response_factory(value=[])

        with pytest.raises(MatchHumansByNameRetryableError) as error:
            await find_humans_by_name(
                context=mock_context,
                names=["John Smith", "Jane Foo", "Hello"],
            )

        john_smith1_match = json.dumps(short_human(serialize_user(john_smith1), with_email=True))
        john_smith2_match = json.dumps(short_human(serialize_user(john_smith2), with_email=True))
        hello_world_match = json.dumps(short_human(serialize_user(hello_world), with_email=True))

        assert "John Smith" in cast(str, error.value.message)
        assert john_smith1_match in cast(str, error.value.additional_prompt_content)
        assert john_smith2_match in cast(str, error.value.additional_prompt_content)

        assert "Jane" not in cast(str, error.value.message)
        assert "Jane" not in cast(str, error.value.additional_prompt_content)

        assert "Hello" in cast(str, error.value.message)
        assert hello_world_match in cast(str, error.value.additional_prompt_content)

    @pytest.mark.asyncio
    async def test_one_partial_match(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        user_factory: Callable,
        response_factory: Callable,
    ) -> None:
        hello_world = user_factory(first_name="Hello", last_name="World")
        users = [
            user_factory(first_name="John", last_name="Smith"),
            user_factory(first_name="Jack", last_name="Smith"),
            user_factory(first_name="Jane", last_name="Foo"),
            user_factory(first_name="Jane", last_name="Bar"),
            hello_world,
        ]

        mock_client.users.get.return_value = response_factory(value=users)
        mock_client.me.people.get.return_value = response_factory(value=[])

        with pytest.raises(MatchHumansByNameRetryableError) as error:
            await find_humans_by_name(
                context=mock_context,
                names=["John Smith", "Jane Foo", "Hello"],
            )

        hello_world_match = json.dumps(short_human(serialize_user(hello_world), with_email=True))

        assert "John" not in cast(str, error.value.message)
        assert "Jane" not in cast(str, error.value.message)
        assert "Jane" not in cast(str, error.value.additional_prompt_content)

        assert "Hello" in cast(str, error.value.message)
        assert hello_world_match in cast(str, error.value.additional_prompt_content)

    @pytest.mark.asyncio
    async def test_multiple_partial_matches(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        user_factory: Callable,
        response_factory: Callable,
    ) -> None:
        jane_foo = user_factory(first_name="Jane", last_name="Foo")
        jane_bar = user_factory(first_name="Jane", last_name="Bar")
        hello_world = user_factory(first_name="Hello", last_name="World")
        users = [
            user_factory(first_name="John", last_name="Smith"),
            user_factory(first_name="Jack", last_name="Smith"),
            jane_foo,
            jane_bar,
            hello_world,
        ]

        mock_client.users.get.return_value = response_factory(value=users)
        mock_client.me.people.get.return_value = response_factory(value=[])

        with pytest.raises(MatchHumansByNameRetryableError) as error:
            await find_humans_by_name(
                context=mock_context,
                names=["John Smith", "Jane", "Hello"],
            )

        hello_world_match = json.dumps(short_human(serialize_user(hello_world), with_email=True))
        jane_foo_match = json.dumps(short_human(serialize_user(jane_foo), with_email=True))
        jane_bar_match = json.dumps(short_human(serialize_user(jane_bar), with_email=True))

        assert "John" not in cast(str, error.value.message)
        assert "Smith" not in cast(str, error.value.message)

        assert "Jane" in cast(str, error.value.message)
        assert jane_foo_match in cast(str, error.value.additional_prompt_content)
        assert jane_bar_match in cast(str, error.value.additional_prompt_content)

        assert "Hello" in cast(str, error.value.message)
        assert hello_world_match in cast(str, error.value.additional_prompt_content)

    @pytest.mark.asyncio
    async def test_zero_matches(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        user_factory: Callable,
        response_factory: Callable,
    ) -> None:
        users = [
            user_factory(first_name="John", last_name="Smith"),
            user_factory(first_name="Jane", last_name="Foo"),
        ]

        mock_client.users.get.return_value = response_factory(value=users)
        mock_client.me.people.get.return_value = response_factory(value=[])

        with pytest.raises(MatchHumansByNameRetryableError) as error:
            await find_humans_by_name(
                context=mock_context,
                names=["Whatever", "Does Not Exist"],
            )

        assert "Whatever" in cast(str, error.value.message)
        assert "Does Not Exist" in cast(str, error.value.message)
        # Since there are no matches, there should be no additional prompt
        assert error.value.additional_prompt_content is None


class TestFindPeopleAndUsersByName:
    @pytest.mark.asyncio
    async def test_unique_exact_matches(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        person_factory: Callable,
        user_factory: Callable,
        response_factory: Callable,
    ) -> None:
        people = [
            person_factory(first_name="John", last_name="Smith"),
            person_factory(first_name="Jane", last_name="Foo"),
        ]

        users = [
            user_factory(first_name="Foo", last_name="Bar"),
            user_factory(first_name="Hello", last_name="World"),
        ]

        mock_client.users.get.return_value = response_factory(value=users)
        mock_client.me.people.get.return_value = response_factory(value=people)

        result = await find_humans_by_name(
            context=mock_context,
            names=["John Smith", "Foo Bar"],
        )

        assert result == [
            serialize_person(people[0]),
            serialize_user(users[0]),
        ]

    @pytest.mark.asyncio
    async def test_conflicting_exact_matches(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        person_factory: Callable,
        user_factory: Callable,
        response_factory: Callable,
    ) -> None:
        john_smith_person = person_factory(first_name="John", last_name="Smith")
        john_smith_user = user_factory(first_name="John", last_name="Smith")
        people = [
            john_smith_person,
            person_factory(first_name="Jane", last_name="Foo"),
        ]

        users = [
            user_factory(first_name="Foo", last_name="Bar"),
            john_smith_user,
        ]

        mock_client.users.get.return_value = response_factory(value=users)
        mock_client.me.people.get.return_value = response_factory(value=people)

        with pytest.raises(MatchHumansByNameRetryableError) as error:
            await find_humans_by_name(
                context=mock_context,
                names=["John Smith", "Foo Bar"],
            )

        smith_person_match = json.dumps(
            short_human(serialize_person(john_smith_person), with_email=True)
        )
        smith_user_match = json.dumps(short_human(serialize_user(john_smith_user), with_email=True))

        assert "John Smith" in cast(str, error.value.message)
        assert smith_person_match in cast(str, error.value.additional_prompt_content)
        assert smith_user_match in cast(str, error.value.additional_prompt_content)

        assert "Foo" not in cast(str, error.value.message)
        assert "Foo" not in cast(str, error.value.additional_prompt_content)
        assert "Jane" not in cast(str, error.value.message)
        assert "Jane" not in cast(str, error.value.additional_prompt_content)

    @pytest.mark.asyncio
    async def test_unique_exact_person_match_and_partial_user_match(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        person_factory: Callable,
        user_factory: Callable,
        response_factory: Callable,
    ) -> None:
        people = [
            person_factory(first_name="John", last_name="Smith"),
            person_factory(first_name="Jane", last_name="Foo"),
        ]

        users = [
            user_factory(first_name="Foo", last_name="Baron"),
            user_factory(first_name="Hello", last_name="World"),
        ]

        mock_client.users.get.return_value = response_factory(value=users)
        mock_client.me.people.get.return_value = response_factory(value=people)

        with pytest.raises(MatchHumansByNameRetryableError) as error:
            await find_humans_by_name(
                context=mock_context,
                names=["John Smith", "Foo Bar"],
            )

        foo_baron_match = json.dumps(short_human(serialize_user(users[0]), with_email=True))

        assert "Foo Bar" in cast(str, error.value.message)
        assert foo_baron_match in cast(str, error.value.additional_prompt_content)

        assert "John Smith" not in cast(str, error.value.message)
        assert "John Smith" not in cast(str, error.value.additional_prompt_content)
        assert "Jane Foo" not in cast(str, error.value.message)
        assert "Jane Foo" not in cast(str, error.value.additional_prompt_content)
        assert "Hello World" not in cast(str, error.value.message)
        assert "Hello World" not in cast(str, error.value.additional_prompt_content)

    @pytest.mark.asyncio
    async def test_unique_exact_user_match_and_partial_person_match(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        person_factory: Callable,
        user_factory: Callable,
        response_factory: Callable,
    ) -> None:
        people = [
            person_factory(first_name="John", last_name="Smitho"),
            person_factory(first_name="Jane", last_name="Foo"),
        ]

        users = [
            user_factory(first_name="Foo", last_name="Bar"),
            user_factory(first_name="Hello", last_name="World"),
        ]

        mock_client.users.get.return_value = response_factory(value=users)
        mock_client.me.people.get.return_value = response_factory(value=people)

        with pytest.raises(MatchHumansByNameRetryableError) as error:
            await find_humans_by_name(
                context=mock_context,
                names=["John Smith", "Foo Bar"],
            )

        john_smith_match = json.dumps(short_human(serialize_person(people[0]), with_email=True))

        assert "John Smith" in cast(str, error.value.message)
        assert john_smith_match in cast(str, error.value.additional_prompt_content)

        assert "Foo Bar" not in cast(str, error.value.message)
        assert "Foo Bar" not in cast(str, error.value.additional_prompt_content)
        assert "Jane Foo" not in cast(str, error.value.message)
        assert "Jane Foo" not in cast(str, error.value.additional_prompt_content)
        assert "Hello World" not in cast(str, error.value.message)
        assert "Hello World" not in cast(str, error.value.additional_prompt_content)

    @pytest.mark.asyncio
    async def test_zero_matches(
        self,
        mock_context: ToolContext,
        mock_client: Mock,
        person_factory: Callable,
        user_factory: Callable,
        response_factory: Callable,
    ) -> None:
        people = [
            person_factory(first_name="John", last_name="Smith"),
            person_factory(first_name="Jane", last_name="Foo"),
        ]

        users = [
            user_factory(first_name="Foo", last_name="Bar"),
            user_factory(first_name="Hello", last_name="World"),
        ]

        mock_client.users.get.return_value = response_factory(value=users)
        mock_client.me.people.get.return_value = response_factory(value=people)

        with pytest.raises(MatchHumansByNameRetryableError) as error:
            await find_humans_by_name(
                context=mock_context,
                names=["Whatever", "Does Not Exist"],
            )

        assert "Whatever" in error.value.message
        assert "Does Not Exist" in error.value.message
        # Since there are no matches, there should be no additional prompt
        assert error.value.additional_prompt_content is None
