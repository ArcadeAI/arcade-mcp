import pytest

from arcade.cli.utils import compute_base_url

DEFAULT_HOST = "api.arcade-ai.com"
LOCALHOST = "localhost"
DEFAULT_PORT = None
DEFAULT_VERSION = "v1"


@pytest.mark.parametrize(
    "inputs, expected_outputs",
    [
        pytest.param(
            {
                "host_input": DEFAULT_HOST,
                "port_input": None,
                "force_tls": False,
                "force_no_tls": False,
                "api_version": DEFAULT_VERSION,
            },
            {
                "base_url": f"http://{DEFAULT_HOST}/{DEFAULT_VERSION}",
            },
            id="noop",
        ),
        pytest.param(
            {
                "host_input": "api2.arcade-ai.com",
                "port_input": None,
                "force_tls": False,
                "force_no_tls": False,
                "api_version": DEFAULT_VERSION,
            },
            {
                "base_url": f"https://api2.arcade-ai.com/{DEFAULT_VERSION}",
            },
            id="set host",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_HOST,
                "port_input": 6789,
                "force_tls": False,
                "force_no_tls": False,
                "api_version": DEFAULT_VERSION,
            },
            {
                "base_url": f"https://{DEFAULT_HOST}:6789/{DEFAULT_VERSION}",
            },
            id="set port",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_HOST,
                "port_input": None,
                "force_tls": False,
                "force_no_tls": True,
                "api_version": DEFAULT_VERSION,
            },
            {
                "base_url": f"http://{DEFAULT_HOST}/{DEFAULT_VERSION}",
            },
            id="force no TLS",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_HOST,
                "port_input": None,
                "force_tls": True,
                "force_no_tls": False,
                "api_version": DEFAULT_VERSION,
            },
            {
                "base_url": f"https://{DEFAULT_HOST}/{DEFAULT_VERSION}",
            },
            id="force TLS",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": None,
                "force_tls": False,
                "force_no_tls": False,
                "api_version": DEFAULT_VERSION,
            },
            {
                "base_url": f"http://{LOCALHOST}:9099",
            },
            id="localhost and no port or TLS specified",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": 1234,
                "force_tls": False,
                "force_no_tls": False,
                "api_version": DEFAULT_VERSION,
            },
            {
                "base_url": f"http://{LOCALHOST}:1234",
            },
            id="localhost and port specified",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": None,
                "force_tls": True,
                "force_no_tls": False,
                "api_version": DEFAULT_VERSION,
            },
            {
                "base_url": f"https://{LOCALHOST}:9099",
            },
            id="localhost and force TLS",
        ),
    ],
)
def test_compute_base_url(inputs: dict, expected_outputs: dict):
    base_url = compute_base_url(
        inputs["force_tls"],
        inputs["force_no_tls"],
        inputs["host_input"],
        inputs["port_input"],
        inputs["api_version"],
    )

    assert base_url == expected_outputs["base_url"]
