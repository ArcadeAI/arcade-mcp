import pytest

from arcade.cli.utils import apply_config_overrides
from arcade.core.config_model import ApiConfig, Config, EngineConfig

DEFAULT_HOST = "api.arcade-ai.com"
DEFAULT_PORT = None
DEFAULT_TLS = True


@pytest.mark.parametrize(
    "inputs, expected_outputs",
    [
        pytest.param(
            {
                "host_input": None,
                "port_input": None,
                "tls_input": None,
            },
            {
                "host": DEFAULT_HOST,
                "port": DEFAULT_PORT,
                "tls": DEFAULT_TLS,
            },
            id="noop",
        ),
        pytest.param(
            {
                "host_input": "api2.arcade-ai.com",
                "port_input": None,
                "tls_input": None,
            },
            {
                "host": "api2.arcade-ai.com",
                "port": DEFAULT_PORT,
                "tls": DEFAULT_TLS,
            },
            id="set host",
        ),
        pytest.param(
            {
                "host_input": None,
                "port_input": 6789,
                "tls_input": None,
            },
            {
                "host": DEFAULT_HOST,
                "port": 6789,
                "tls": DEFAULT_TLS,
            },
            id="set port",
        ),
        pytest.param(
            {
                "host_input": None,
                "port_input": None,
                "tls_input": False,
            },
            {
                "host": DEFAULT_HOST,
                "port": DEFAULT_PORT,
                "tls": False,
            },
            id="set TLS to False",
        ),
        pytest.param(
            {
                "host_input": None,
                "port_input": None,
                "tls_input": True,
            },
            {
                "host": DEFAULT_HOST,
                "port": DEFAULT_PORT,
                "tls": True,
            },
            id="set TLS to True",
        ),
        pytest.param(
            {
                "host_input": "localhost",
                "port_input": None,
                "tls_input": None,
            },
            {
                "host": "localhost",
                "port": 9099,
                "tls": False,
            },
            id="localhost and no port or TLS specified",
        ),
        pytest.param(
            {
                "host_input": "localhost",
                "port_input": 1234,
                "tls_input": None,
            },
            {
                "host": "localhost",
                "port": 1234,
                "tls": False,
            },
            id="localhost and port specified",
        ),
        pytest.param(
            {
                "host_input": "localhost",
                "port_input": None,
                "tls_input": True,
            },
            {
                "host": "localhost",
                "port": 9099,
                "tls": True,
            },
            id="localhost and TLS specified",
        ),
    ],
)
def test_apply_config_overrides(inputs: dict, expected_outputs: dict):
    # Set fake default values for testing
    config = Config(
        api=ApiConfig(key="fake_api_key"),
        engine=EngineConfig(
            host=DEFAULT_HOST,
            port=DEFAULT_PORT,
            tls=DEFAULT_TLS,
        ),
    )

    apply_config_overrides(config, inputs["host_input"], inputs["port_input"], inputs["tls_input"])

    assert config.engine.host == expected_outputs["host"]
    assert config.engine.port == expected_outputs["port"]
    assert config.engine.tls == expected_outputs["tls"]
