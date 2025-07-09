import json

import pytest
from arcade_tdk.errors import RetryableToolError, ToolExecutionError
from slack_sdk.errors import SlackApiError

from arcade_slack.user_retrieval import (
    get_single_user_by_id,
    get_users_by_id,
    get_users_by_id_username_or_email,
)
from arcade_slack.utils import (
    cast_user_dict,
    extract_basic_user_info,
    short_user_info,
)


@pytest.mark.asyncio
async def test_get_multiple_users_by_emails_success(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()

    emails = [user1["profile"]["email"], user2["profile"]["email"]]

    mock_user_retrieval_slack_client.users_lookupByEmail.side_effect = [
        {"ok": True, "user": user1},
        {"ok": True, "user": user2},
    ]

    response = await get_users_by_id_username_or_email(context=mock_context, emails=emails)

    assert response == [extract_basic_user_info(user1), extract_basic_user_info(user2)]


@pytest.mark.asyncio
async def test_get_multiple_users_by_usernames_or_emails_with_emails_not_found(
    mock_context,
    mock_user_retrieval_slack_client,
    mock_users_slack_client,
    dummy_user_factory,
):
    user1 = dummy_user_factory(email="user1@example.com")

    emails = [user1["profile"]["email"], "not_found@example.com"]

    async def lookup_by_email_side_effect(*, email):
        if email == "user1@example.com":
            return {"ok": True, "user": user1}
        raise SlackApiError(
            message="User not found",
            response={"error": "user_not_found"},
        )

    mock_user_retrieval_slack_client.users_lookupByEmail.side_effect = lookup_by_email_side_effect

    mock_users_slack_client.users_list.return_value = {
        "ok": True,
        "members": [user1],
    }

    with pytest.raises(RetryableToolError) as error:
        await get_users_by_id_username_or_email(context=mock_context, emails=emails)

    assert "not_found@example.com" in error.value.message
    assert json.dumps(short_user_info(user1)) in error.value.additional_prompt_content


@pytest.mark.asyncio
async def test_get_multiple_users_by_usernames_or_emails_with_usernames_success(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()

    usernames = [user1["name"], user2["name"]]

    mock_user_retrieval_slack_client.users_list.return_value = {
        "ok": True,
        "members": [user1, user2],
    }

    response = await get_users_by_id_username_or_email(context=mock_context, usernames=usernames)

    assert response == [extract_basic_user_info(user1), extract_basic_user_info(user2)]


@pytest.mark.asyncio
async def test_get_multiple_users_by_usernames_or_emails_with_usernames_not_found(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()
    user3 = dummy_user_factory()

    usernames = [user1["name"], "username_not_found"]

    mock_user_retrieval_slack_client.users_list.return_value = {
        "ok": True,
        "members": [user1, user2, user3],
    }

    with pytest.raises(RetryableToolError) as error:
        await get_users_by_id_username_or_email(context=mock_context, usernames=usernames)

    assert "username_not_found" in error.value.message
    assert json.dumps(short_user_info(user1)) in error.value.additional_prompt_content
    assert json.dumps(short_user_info(user2)) in error.value.additional_prompt_content
    assert json.dumps(short_user_info(user3)) in error.value.additional_prompt_content


@pytest.mark.asyncio
async def test_get_multiple_users_by_mixed_usernames_and_emails_success(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()
    user3 = dummy_user_factory()
    user4 = dummy_user_factory()

    mock_user_retrieval_slack_client.users_list.return_value = {
        "ok": True,
        "members": [user1, user2],
    }
    mock_user_retrieval_slack_client.users_lookupByEmail.side_effect = [
        {"ok": True, "user": user3},
        {"ok": True, "user": user4},
    ]

    response = await get_users_by_id_username_or_email(
        context=mock_context,
        usernames=[user1["name"], user2["name"]],
        emails=[user3["profile"]["email"], user4["profile"]["email"]],
    )

    assert response == [
        extract_basic_user_info(user1),
        extract_basic_user_info(user2),
        extract_basic_user_info(user3),
        extract_basic_user_info(user4),
    ]


@pytest.mark.asyncio
async def test_get_single_user_by_id_success(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user = dummy_user_factory()

    mock_user_retrieval_slack_client.users_info.return_value = {"ok": True, "user": user}

    response = await get_single_user_by_id(
        auth_token=mock_context.get_auth_token_or_empty(),
        user_id=user["id"],
    )

    assert response == cast_user_dict(user)


@pytest.mark.asyncio
async def test_get_single_user_by_id_not_found(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user = dummy_user_factory()

    mock_user_retrieval_slack_client.users_info.side_effect = SlackApiError(
        message="User not found",
        response={"error": "user_not_found"},
    )

    response = await get_single_user_by_id(
        auth_token=mock_context.get_auth_token_or_empty(),
        user_id=user["id"],
    )

    assert response is None


@pytest.mark.asyncio
async def test_get_single_user_by_id_not_ok(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user = dummy_user_factory()

    mock_user_retrieval_slack_client.users_info.return_value = {"ok": False, "error": "not_ok"}

    response = await get_single_user_by_id(
        auth_token=mock_context.get_auth_token_or_empty(),
        user_id=user["id"],
    )

    assert response is None


@pytest.mark.asyncio
async def test_get_single_user_by_id_unknown_error(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user = dummy_user_factory()

    mock_user_retrieval_slack_client.users_info.side_effect = SlackApiError(
        message="Unknown error",
        response={"error": "unknown_error_string"},
    )

    with pytest.raises(ToolExecutionError) as error:
        await get_single_user_by_id(
            auth_token=mock_context.get_auth_token_or_empty(),
            user_id=user["id"],
        )

    assert user["id"] in error.value.message
    assert "unknown_error_string" in error.value.developer_message


@pytest.mark.asyncio
async def test_get_users_by_id_with_one_user_id_success(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()

    mock_user_retrieval_slack_client.users_info.return_value = {"ok": True, "user": user1}

    response = await get_users_by_id(
        auth_token=mock_context.get_auth_token_or_empty(),
        user_ids=[user1["id"]],
    )

    assert response == {"users": [cast_user_dict(user1)], "not_found": []}

    mock_user_retrieval_slack_client.users_list.assert_not_called()


@pytest.mark.asyncio
async def test_get_users_by_id_with_one_user_id_not_found(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()

    mock_user_retrieval_slack_client.users_info.side_effect = SlackApiError(
        message="User not found",
        response={"error": "user_not_found"},
    )

    response = await get_users_by_id(
        auth_token=mock_context.get_auth_token_or_empty(),
        user_ids=[user1["id"]],
    )

    assert response == {"users": [], "not_found": [user1["id"]]}

    mock_user_retrieval_slack_client.users_list.assert_not_called()


@pytest.mark.asyncio
async def test_get_users_by_id_with_multiple_user_ids_success(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()
    user3 = dummy_user_factory()
    user4 = dummy_user_factory()

    mock_user_retrieval_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [user1, user2],
            "response_metadata": {"next_cursor": "next_cursor"},
        },
        {"ok": True, "members": [user3, user4]},
    ]

    response = await get_users_by_id(
        auth_token=mock_context.get_auth_token_or_empty(),
        user_ids=[user1["id"], user4["id"]],
    )

    assert response == {"users": [cast_user_dict(user1), cast_user_dict(user4)], "not_found": []}


@pytest.mark.asyncio
async def test_get_users_by_id_with_multiple_user_ids_some_not_found(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory(id_="U1")
    user2 = dummy_user_factory(id_="U2")
    user3 = dummy_user_factory(id_="U3")
    user4 = dummy_user_factory(id_="U4")

    mock_user_retrieval_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [user1, user2],
            "response_metadata": {"next_cursor": "next_cursor"},
        },
        {
            "ok": True,
            "members": [user3, user4],
            "response_metadata": {"next_cursor": None},
        },
    ]

    response = await get_users_by_id(
        auth_token=mock_context.get_auth_token_or_empty(),
        user_ids=[user1["id"], user4["id"], "user_not_exists"],
    )

    assert response == {
        "users": [cast_user_dict(user1), cast_user_dict(user4)],
        "not_found": ["user_not_exists"],
    }
