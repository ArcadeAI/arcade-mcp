import asyncio
from unittest.mock import AsyncMock

import pytest
from arcade_tdk.errors import ToolExecutionError
from slack_sdk.errors import SlackApiError

from arcade_slack.models import (
    ConcurrencySafeCoroutineCaller,
    FindChannelByNameSentinel,
    FindMultipleUsersByUsernameSentinel,
    FindUserByUsernameSentinel,
    GetUserByEmailCaller,
)


def test_find_user_by_username_sentinel():
    sentinel = FindUserByUsernameSentinel(username="jenifer")
    assert sentinel(last_result=[{"name": "jack"}]) is False
    assert sentinel(last_result=[{"name": "john"}, {"name": "jack"}]) is False
    assert sentinel(last_result=[{"name": "hello"}, {"name": "jenifer"}]) is True
    assert sentinel(last_result=[{"name": "JENIFER"}]) is True


def test_find_multiple_users_by_username_sentinel():
    sentinel = FindMultipleUsersByUsernameSentinel(usernames=["jenifer", "jack"])
    assert sentinel(last_result=[{"name": "jack"}]) is False
    assert sentinel(last_result=[{"name": "john"}, {"name": "jack"}]) is False
    assert sentinel(last_result=[{"name": "hello"}, {"name": "JENIFER"}]) is True
    assert sentinel(last_result=[{"name": "world"}]) is True


def test_find_channel_by_name_sentinel():
    sentinel = FindChannelByNameSentinel(channel_name="foobar")
    assert sentinel(last_result=[{"name": "foo"}]) is False
    assert sentinel(last_result=[{"name": "foo"}, {"name": "bar"}]) is False
    assert sentinel(last_result=[{"name": "foo"}, {"name": "foobar"}]) is True
    assert sentinel(last_result=[{"name": "FOObar"}]) is True


@pytest.mark.asyncio
async def test_concurrency_safe_coroutine_caller():
    mock_func = AsyncMock()
    mock_semaphore = AsyncMock(spec=asyncio.Semaphore)

    caller = ConcurrencySafeCoroutineCaller(mock_func, "arg1", "arg2", kwarg1="kwarg1")
    response = await caller(semaphore=mock_semaphore)

    assert response == mock_func.return_value
    mock_func.assert_awaited_once_with("arg1", "arg2", kwarg1="kwarg1")
    mock_semaphore.__aenter__.assert_awaited_once()
    mock_semaphore.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_by_email_caller_success():
    mock_func = AsyncMock()
    mock_func.return_value = {"user": {"id": "U1234567890", "name": "John Doe"}}
    mock_semaphore = AsyncMock(spec=asyncio.Semaphore)

    caller = GetUserByEmailCaller(mock_func, "test@example.com")
    response = await caller(semaphore=mock_semaphore)

    assert response == {
        "user": {"id": "U1234567890", "name": "John Doe"},
        "email": "test@example.com",
    }
    mock_func.assert_awaited_once_with(email="test@example.com")
    mock_semaphore.__aenter__.assert_awaited_once()
    mock_semaphore.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_by_email_caller_not_found_error():
    mock_func = AsyncMock(
        side_effect=SlackApiError(message="User not found", response={"error": "user_not_found"})
    )
    mock_semaphore = AsyncMock(spec=asyncio.Semaphore)

    caller = GetUserByEmailCaller(mock_func, "test@example.com")
    response = await caller(semaphore=mock_semaphore)

    assert response == {
        "user": None,
        "email": "test@example.com",
    }
    mock_func.assert_awaited_once_with(email="test@example.com")
    mock_semaphore.__aenter__.assert_awaited_once()
    mock_semaphore.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_by_email_caller_unknown_slack_api_error():
    mock_func = AsyncMock(
        side_effect=SlackApiError(message="Unknown error", response={"error": "unknown_error"})
    )
    mock_semaphore = AsyncMock(spec=asyncio.Semaphore)

    caller = GetUserByEmailCaller(mock_func, "test@example.com")
    with pytest.raises(ToolExecutionError) as error:
        await caller(semaphore=mock_semaphore)

    assert error.value.message == "Error getting user by email"
    assert error.value.developer_message == "Error getting user by email: unknown_error"
    mock_func.assert_awaited_once_with(email="test@example.com")
    mock_semaphore.__aenter__.assert_awaited_once()
    mock_semaphore.__aexit__.assert_awaited_once()
