import pytest
from arcade_cli import context as context_module


@pytest.fixture(autouse=True)
def ci_environment_unpinned():
    context_module._pinned_ci_environment = None
    yield
    context_module._pinned_ci_environment = None
