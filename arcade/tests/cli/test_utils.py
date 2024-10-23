import pytest

from arcade.cli.utils import compute_base_url

DEFAULT_HOST = "api.arcade-ai.com"
LOCALHOST = "localhost"
DEFAULT_PORT = None
DEFAULT_FORCE_TLS = False
DEFAULT_FORCE_NO_TLS = False


@pytest.mark.parametrize(
    "inputs, expected_output",
    [
        pytest.param(
            {
                "host_input": DEFAULT_HOST,
                "port_input": DEFAULT_PORT,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "https://api.arcade-ai.com",
            id="default",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": DEFAULT_PORT,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "http://localhost:9099",
            id="localhost",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_HOST,
                "port_input": 9099,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "https://api.arcade-ai.com:9099",
            id="custom port",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": 9099,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "http://localhost:9099",
            id="localhost with custom port",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_HOST,
                "port_input": DEFAULT_PORT,
                "force_tls": True,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "https://api.arcade-ai.com",
            id="force TLS",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": DEFAULT_PORT,
                "force_tls": True,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "https://localhost:9099",
            id="localhost with force TLS",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_HOST,
                "port_input": 9099,
                "force_tls": True,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "https://api.arcade-ai.com:9099",
            id="custom port with force TLS",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": 9099,
                "force_tls": True,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "https://localhost:9099",
            id="localhost with custom port and force TLS",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_HOST,
                "port_input": DEFAULT_PORT,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": True,
            },
            "http://api.arcade-ai.com",
            id="force no TLS",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": DEFAULT_PORT,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": True,
            },
            "http://localhost:9099",
            id="localhost with force no TLS",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_HOST,
                "port_input": 9099,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": True,
            },
            "http://api.arcade-ai.com:9099",
            id="custom port with force no TLS",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": 9099,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": True,
            },
            "http://localhost:9099",
            id="localhost with custom port and force no TLS",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_HOST,
                "port_input": DEFAULT_PORT,
                "force_tls": True,
                "force_no_tls": True,
            },
            "http://api.arcade-ai.com",
            id="force TLS and no TLS",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": DEFAULT_PORT,
                "force_tls": True,
                "force_no_tls": True,
            },
            "http://localhost:9099",
            id="localhost with force TLS and no TLS",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_HOST,
                "port_input": 9099,
                "force_tls": True,
                "force_no_tls": True,
            },
            "http://api.arcade-ai.com:9099",
            id="custom port with force TLS and no TLS",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": 9099,
                "force_tls": True,
                "force_no_tls": True,
            },
            "http://localhost:9099",
            id="localhost with custom port, force TLS and no TLS",
        ),
        pytest.param(
            {
                "host_input": "arandomhost.com",
                "port_input": DEFAULT_PORT,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "https://arandomhost.com",
            id="random host",
        ),
    ],
)
def test_compute_base_url(inputs: dict, expected_output: str):
    base_url = compute_base_url(
        inputs["force_tls"],
        inputs["force_no_tls"],
        inputs["host_input"],
        inputs["port_input"],
    )

    assert base_url == expected_output
