import pytest
from arcade_tdk.errors import RetryableToolError
from slack_sdk.errors import SlackApiError

from arcade_slack.user_retrieval import (
    get_users_by_id_username_or_email,
)
from arcade_slack.utils import (
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
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()

    emails = [user1["profile"]["email"], "not_found@example.com"]

    mock_user_retrieval_slack_client.users_lookupByEmail.side_effect = [
        {"ok": True, "user": user1},
        SlackApiError(
            message="User not found",
            response={"error": "user_not_found"},
        ),
    ]
    mock_user_retrieval_slack_client.users_list.return_value = {
        "ok": True,
        "members": [user1, user2],
    }

    with pytest.raises(RetryableToolError) as error:
        await get_users_by_id_username_or_email(context=mock_context, emails=emails)

    assert "not_found@example.com" in error.value.message


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
    assert str(short_user_info(user1)) not in error.value.additional_prompt_content
    assert str(short_user_info(user2)) in error.value.additional_prompt_content
    assert str(short_user_info(user3)) in error.value.additional_prompt_content


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
