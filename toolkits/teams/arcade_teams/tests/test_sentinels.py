from collections.abc import Callable

from arcade_teams.models import ChatMembershipMatchType, FindChatByMembersSentinel


def test_find_chat_by_members_sentinel_exact_match(
    chat_factory: Callable,
    member_factory: Callable,
) -> None:
    members = [
        member_factory(id_="1", display_name="John Doe"),
        member_factory(id_="2", display_name="Jane Smith"),
        member_factory(id_="3", display_name="John Smith"),
    ]
    chat = chat_factory(members=members)

    sentinel = FindChatByMembersSentinel(user_ids=["1", "2"], user_names=["John Smith"])

    assert sentinel([chat]) is True
    assert sentinel.matches[ChatMembershipMatchType.EXACT_MATCH] == [chat]
    assert len(sentinel.matches[ChatMembershipMatchType.PARTIAL_MATCH]) == 0


def test_find_chat_by_members_sentinel_partial_match(
    chat_factory: Callable,
    member_factory: Callable,
) -> None:
    members = [
        member_factory(id_="1", display_name="John Doe"),
        member_factory(id_="2", display_name="Jane Smith"),
        member_factory(id_="3", display_name="John Smith"),
    ]
    chat = chat_factory(members=members)

    sentinel = FindChatByMembersSentinel(user_ids=["1", "2"], user_names=["smith"])

    assert sentinel([chat]) is False
    assert sentinel.matches[ChatMembershipMatchType.PARTIAL_MATCH] == [chat]
    assert len(sentinel.matches[ChatMembershipMatchType.EXACT_MATCH]) == 0


def test_find_chat_by_members_sentinel_partial_match_mixed_order(
    chat_factory: Callable,
    member_factory: Callable,
) -> None:
    members = [
        member_factory(id_="1", display_name="John Doe"),
        member_factory(id_="2", display_name="Jane Smith"),
        member_factory(id_="3", display_name="Foo Bar"),
    ]
    chat = chat_factory(members=members)

    sentinel = FindChatByMembersSentinel(user_ids=["1"], user_names=["bar", "smith"])

    assert sentinel([chat]) is False
    assert sentinel.matches[ChatMembershipMatchType.PARTIAL_MATCH] == [chat]
    assert len(sentinel.matches[ChatMembershipMatchType.EXACT_MATCH]) == 0


def test_find_chat_by_members_sentinel_member_length_mismatch(
    chat_factory: Callable,
    member_factory: Callable,
) -> None:
    members = [
        member_factory(id_="1", display_name="John Doe"),
        member_factory(id_="2", display_name="Jane Smith"),
        member_factory(id_="3", display_name="John Smith"),
        member_factory(id_="4", display_name="Another Member"),
    ]
    chat = chat_factory(members=members)

    sentinel = FindChatByMembersSentinel(user_ids=["1", "2"], user_names=["John Smith"])

    assert sentinel([chat]) is False
    assert sentinel.matches[ChatMembershipMatchType.EXACT_MATCH] == []
    assert sentinel.matches[ChatMembershipMatchType.PARTIAL_MATCH] == []


def test_find_chat_by_members_sentinel_missing_user_id(
    chat_factory: Callable,
    member_factory: Callable,
) -> None:
    members = [
        member_factory(id_="1", display_name="John Doe"),
        member_factory(id_="3", display_name="John Smith"),
    ]
    chat = chat_factory(members=members)

    sentinel = FindChatByMembersSentinel(user_ids=["1", "2"], user_names=["John Smith"])

    assert sentinel([chat]) is False
    assert sentinel.matches[ChatMembershipMatchType.EXACT_MATCH] == []
    assert sentinel.matches[ChatMembershipMatchType.PARTIAL_MATCH] == []


def test_find_chat_by_members_sentinel_missing_user_name(
    chat_factory: Callable,
    member_factory: Callable,
) -> None:
    members = [
        member_factory(id_="1", display_name="John Doe"),
        member_factory(id_="2", display_name="Jane Smith"),
        member_factory(id_="3", display_name="John Smith"),
    ]
    chat = chat_factory(members=members)

    sentinel = FindChatByMembersSentinel(user_ids=["1", "2"], user_names=["foobar"])

    assert sentinel([chat]) is False
    assert sentinel.matches[ChatMembershipMatchType.PARTIAL_MATCH] == []
    assert sentinel.matches[ChatMembershipMatchType.EXACT_MATCH] == []


def test_find_chat_by_members_sentinel_exact_match_multiple_chats(
    chat_factory: Callable,
    member_factory: Callable,
) -> None:
    chat1 = chat_factory(
        members=[
            member_factory(id_="1", display_name="John Doe"),
            member_factory(id_="2", display_name="Jane Smith"),
            member_factory(id_="3", display_name="John Smith"),
        ]
    )

    chat2 = chat_factory(
        members=[
            member_factory(id_="1", display_name="John Doe"),
            member_factory(id_="2", display_name="Jane Smith"),
            member_factory(id_="4", display_name="John Stitch"),
        ]
    )

    sentinel = FindChatByMembersSentinel(user_ids=["1", "2"], user_names=["John Smith"])

    assert sentinel([chat1, chat2]) is True
    assert sentinel.matches[ChatMembershipMatchType.EXACT_MATCH] == [chat1]
    assert len(sentinel.matches[ChatMembershipMatchType.PARTIAL_MATCH]) == 0


def test_find_chat_by_members_sentinel_partial_match_multiple_chats(
    chat_factory: Callable,
    member_factory: Callable,
) -> None:
    chat1 = chat_factory(
        members=[
            member_factory(id_="1", display_name="John Doe"),
            member_factory(id_="2", display_name="Jane Smith"),
            member_factory(id_="3", display_name="John Smith"),
        ]
    )

    chat2 = chat_factory(
        members=[
            member_factory(id_="1", display_name="John Doe"),
            member_factory(id_="2", display_name="Jane Smith"),
            member_factory(id_="4", display_name="John Stitch"),
        ]
    )

    sentinel = FindChatByMembersSentinel(user_ids=["1", "2"], user_names=["SMITH"])

    assert sentinel([chat1, chat2]) is False
    assert sentinel.matches[ChatMembershipMatchType.PARTIAL_MATCH] == [chat1]
    assert len(sentinel.matches[ChatMembershipMatchType.EXACT_MATCH]) == 0


def test_find_chat_by_members_sentinel_multiple_matches_with_exact_match(
    chat_factory: Callable,
    member_factory: Callable,
) -> None:
    chat1 = chat_factory(
        members=[
            member_factory(id_="1", display_name="John Doe"),
            member_factory(id_="2", display_name="Jane Smith"),
            member_factory(id_="4", display_name="John"),
        ]
    )

    chat2 = chat_factory(
        members=[
            member_factory(id_="1", display_name="John Doe"),
            member_factory(id_="2", display_name="Jane Smith"),
            member_factory(id_="3", display_name="John Smith"),
        ]
    )

    chat3 = chat_factory(
        members=[
            member_factory(id_="2", display_name="Jane Smith"),
            member_factory(id_="3", display_name="John Smith"),
        ]
    )

    sentinel = FindChatByMembersSentinel(user_ids=["1", "2"], user_names=["John"])

    assert sentinel([chat1, chat2, chat3]) is True
    assert sentinel.matches[ChatMembershipMatchType.EXACT_MATCH] == [chat1]
    assert sentinel.matches[ChatMembershipMatchType.PARTIAL_MATCH] == [chat2]


def test_find_chat_by_members_sentinel_called_multiple_times(
    chat_factory: Callable,
    member_factory: Callable,
) -> None:
    members = [
        member_factory(id_="1", display_name="John Doe"),
        member_factory(id_="2", display_name="Jane Smith"),
        member_factory(id_="3", display_name="John Smith"),
    ]
    chat = chat_factory(members=members)

    sentinel = FindChatByMembersSentinel(user_ids=["1", "2"], user_names=["John Smith"])

    assert sentinel([chat]) is True
    assert sentinel.matches[ChatMembershipMatchType.EXACT_MATCH] == [chat]
    assert len(sentinel.matches[ChatMembershipMatchType.PARTIAL_MATCH]) == 0

    members2 = [
        member_factory(id_="1", display_name="John Doe"),
        member_factory(id_="2", display_name="Jane Smith"),
        member_factory(id_="3", display_name="John Smith"),
    ]
    chat2 = chat_factory(members=members2)

    assert sentinel([chat2]) is True
    assert sentinel.matches[ChatMembershipMatchType.EXACT_MATCH] == [chat]
    assert sentinel.matches[ChatMembershipMatchType.PARTIAL_MATCH] == []
