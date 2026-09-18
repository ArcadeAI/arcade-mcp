import pytest
from arcade_cli import _startup_environment


@pytest.fixture(autouse=True)
def startup_environment_forgotten():
    _startup_environment.forget()
    yield
    _startup_environment.forget()
