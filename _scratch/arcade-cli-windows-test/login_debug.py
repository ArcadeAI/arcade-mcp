import uuid
import webbrowser

from arcade_cli.authn import (
    build_coordinator_url,
    create_oauth_client,
    exchange_code_for_tokens,
    fetch_cli_config,
    fetch_whoami,
    generate_authorization_url,
    oauth_callback_server,
    save_credentials_from_whoami,
)


def main() -> None:
    coordinator_url = build_coordinator_url("cloud.arcade.dev", None)
    cli_config = fetch_cli_config(coordinator_url)
    oauth_client = create_oauth_client(cli_config)
    state = str(uuid.uuid4())

    with oauth_callback_server(state) as server:
        redirect_uri = server.get_redirect_uri()
        auth_url, code_verifier = generate_authorization_url(
            oauth_client, cli_config, redirect_uri, state
        )

        print(f"AUTH_URL={auth_url}")
        print(f"REDIRECT_URI={redirect_uri}")
        print(f"STATE={state}")

        try:
            opened = webbrowser.open(auth_url)
            print(f"BROWSER_OPENED={opened}")
        except Exception as exc:
            print(f"BROWSER_OPEN_ERROR={exc}")

    print(f"CALLBACK_RESULT={server.result}")

    if "code" not in server.result:
        print("No authorization code received; exiting.")
        return

    code = server.result["code"]
    tokens = exchange_code_for_tokens(oauth_client, code, redirect_uri, code_verifier)
    whoami = fetch_whoami(coordinator_url, tokens.access_token)
    save_credentials_from_whoami(tokens, whoami, coordinator_url)
    print(f"Saved credentials for {whoami.email}.")


if __name__ == "__main__":
    main()
