from arcade_slack.models import FindMultipleUsersByUsernameSentinel, FindUserByUsernameSentinel


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
