from unittest.mock import patch

from arcade_cli.show import show_logic


def test_show_logic_local_false():
    with patch("arcade_cli.show.get_tools_from_engine") as mock_get_tools:
        mock_get_tools.return_value = []
        show_logic(
            toolkit=None,
            tool=None,
            host="localhost",
            local=False,
            port=None,
            force_tls=False,
            force_no_tls=False,
            debug=False,
        )

        # get_tools_from_engine should be called when local=False
        mock_get_tools.assert_called_once()


def test_show_logic_local_true():
    with patch("arcade_cli.show.create_cli_catalog") as mock_create_catalog:
        mock_create_catalog.return_value = []

        show_logic(
            toolkit=None,
            tool=None,
            host="localhost",
            local=True,
            port=None,
            force_tls=False,
            force_no_tls=False,
            debug=False,
        )

        # create_cli_catalog should be called when local=True
        mock_create_catalog.assert_called_once()
