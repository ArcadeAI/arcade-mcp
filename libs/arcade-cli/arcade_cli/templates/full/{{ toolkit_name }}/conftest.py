from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_context():
    context = AsyncMock()
    context.authorization.token = "fake-token"  # noqa: S105
    context.get_auth_token_or_empty = MagicMock(return_value="fake-token")
    return context
