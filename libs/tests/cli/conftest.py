import pytest
from arcade_core.config_model import select_context

from arcade_cli import _startup_environment


@pytest.fixture(autouse=True)
def startup_environment_forgotten():
    # Both are process-wide: the captured environment, and the context chosen
    # for one invocation. A test that sets either would otherwise decide what
    # the next one loads.
    _startup_environment.forget()
    select_context(None)
    yield
    _startup_environment.forget()
    select_context(None)
