import httpx
import typer
from arcade_core.constants import PROD_ENGINE_HOST
from rich.console import Console
from rich.table import Table

from arcade_cli.usage.command_tracker import TrackedTyper, TrackedTyperGroup
from arcade_cli.utils import (
    compute_base_url,
    get_auth_headers,
    get_org_scoped_url,
)

console = Console()


app = TrackedTyper(
    cls=TrackedTyperGroup,
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=True,
)

state = {
    "engine_url": compute_base_url(
        host=PROD_ENGINE_HOST, port=None, force_tls=False, force_no_tls=False
    )
}


@app.callback()
def main(
    host: str = typer.Option(
        PROD_ENGINE_HOST,
        "--host",
        "-h",
        help="The Arcade Engine host.",
    ),
    port: int = typer.Option(
        None,
        "--port",
        "-p",
        help="The port of the Arcade Engine host.",
    ),
    force_tls: bool = typer.Option(
        False,
        "--tls",
        help="Whether to force TLS for the connection to the Arcade Engine.",
    ),
    force_no_tls: bool = typer.Option(
        False,
        "--no-tls",
        help="Whether to disable TLS for the connection to the Arcade Engine.",
    ),
) -> None:
    """
    Manage tool secrets in Arcade Cloud.

    Usage:
        arcade secret set KEY1=value1 KEY2="value 2"
        arcade secret set --from-env
        arcade secret set -from-env --env-file /path/to/.env
        arcade secret list
        arcade secret unset KEY1 KEY2 KEY3
    """
    engine_url = compute_base_url(force_tls, force_no_tls, host, port)
    state["engine_url"] = engine_url


@app.command("set", help="Set tool secret(s) using KEY=VALUE pairs or from .env file")
def set_secret(
    key_value_pairs: list[str] = typer.Argument(
        None,
        help="Key-value pairs in the format KEY=VALUE",
    ),
    from_env: bool = typer.Option(
        False,
        "--from-env",
        help="Load all secrets from local .env file",
    ),
    env_file: str = typer.Option(
        ".env",
        "--env-file",
        "-f",
        help="Path to .env file (default: .env)",
    ),
) -> None:
    """Set secrets either from .env file or KEY=VALUE pairs."""
    if not from_env and not key_value_pairs:
        raise typer.BadParameter(
            "Either provide KEY=VALUE pairs or use --from-env to load from .env file."
        )
    if from_env and key_value_pairs:
        raise typer.BadParameter("Cannot use both KEY=VALUE pairs and --from-env at the same time.")

    if from_env:
        secrets = load_env_file(env_file)
    else:
        secrets = {}
        for pair in key_value_pairs:
            if (
                "=" not in pair
                or pair.split("=", 1)[0].strip() == ""
                or pair.split("=", 1)[1].strip() == ""
            ):
                raise typer.BadParameter(f"Invalid format '{pair}'. Expected KEY=VALUE")
            key, value = pair.split("=", 1)
            key = key.strip()
            if " " in key:
                raise typer.BadParameter(f"Secret key '{key}' cannot contain spaces")
            value = value  # keep the value as is, including the whitespace
            secrets[key] = value

    for secret_key, secret_value in secrets.items():
        try:
            _upsert_secret(secret_key, secret_value)
        except Exception as e:
            console.print(f"Error setting secret '{secret_key}': {e}", style="bold red")
            continue
        console.print(
            f"Secret '{secret_key}' with value ending in ...{secret_value[-4:]} set successfully"
        )


@app.command("list", help="List all tool secrets in Arcade")
def list_secrets() -> None:
    """List all secrets (keys only, values are masked)."""
    secrets = _get_secrets()
    print_secret_table(secrets)


@app.command("unset", help="Delete tool secret(s) by key names")
def unset_secret(
    keys: list[str] = typer.Argument(
        ...,
        help="Secret keys to delete",
    ),
) -> None:
    """Delete tool secrets."""
    secrets = _get_secrets()

    key_to_id = {secret["key"]: secret["id"] for secret in secrets}

    for key in set(keys):
        secret_id = key_to_id.get(key)
        if not secret_id:
            console.print(f"Warning: Secret with key '{key}' not found, skipping", style="yellow")
            continue

        try:
            _delete_secret(secret_id)
            console.print(f"Secret '{key}' deleted successfully")
        except Exception:
            console.print(
                f"Failed to delete secret '{key}'. Do you have permission to delete this secret?",
                style="bold red",
            )
            continue


def print_secret_table(secrets: list[dict]) -> None:
    """Print a table of tool secrets (with masked values)."""
    table = Table(title="Tool Secrets")
    table.add_column("Key", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Description", style="green")
    table.add_column("Hint", style="green")
    table.add_column("Last Accessed", style="green")
    table.add_column("Created At", style="green")
    for secret in secrets:
        table.add_row(
            secret["key"],
            secret["binding"]["type"],
            secret["description"],
            "..." + secret["hint"] if secret["hint"] else "-",
            secret["last_accessed_at"] if secret["last_accessed_at"] else "Never",
            secret["created_at"],
        )
    console.print(table)


def load_env_file(env_file_path: str) -> dict[str, str]:
    """Load tool secrets from a .env file."""
    secrets = {}
    with open(env_file_path) as file:
        for line in file:
            line = line.strip()
            if line.startswith("#") or not line:
                continue

            # Split on first '=' to handle values that contain '='
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()

            # Remove inline comments, but respect quoted values
            value = _remove_inline_comment(value)
            value = value.strip()

            # Skip entries with empty keys or empty values
            if not key or not value:
                continue

            secrets[key] = value
    return secrets


def _remove_inline_comment(value: str) -> str:
    """Remove inline comments from env value, respecting quoted strings."""
    value = value.strip()

    # Check if value starts with a quote
    if value.startswith('"') or value.startswith("'"):
        quote_char = value[0]

        # Find the matching closing quote (not escaped)
        i = 1
        while i < len(value):
            if value[i] == quote_char:
                # Found potential closing quote
                # Check if there's anything after it
                remaining = value[i + 1 :]
                comment_idx = remaining.find(" #")
                if comment_idx != -1:
                    # Remove the comment part and strip quotes
                    quoted_value = value[: i + 1]
                    return quoted_value[1:-1]  # Remove surrounding quotes
                else:
                    # No comment after closing quote, strip quotes
                    quoted_value = value[: i + 1]
                    return quoted_value[1:-1]  # Remove surrounding quotes
            i += 1

        # No closing quote, treat as unquoted
        comment_idx = value.find(" #")
        if comment_idx != -1:
            return value[:comment_idx]
        return value
    else:
        # For unquoted values, remove everything after ' #'
        comment_idx = value.find(" #")
        if comment_idx != -1:
            return value[:comment_idx]
        return value


def _upsert_secret(secret_key: str, secret_value: str) -> None:
    """Upsert a secret to the engine."""
    engine_url = state["engine_url"]
    url = get_org_scoped_url(engine_url, f"/secrets/{secret_key}")
    response = httpx.put(
        url,
        headers=get_auth_headers(),
        json={"description": "Secret set via CLI", "value": secret_value},
    )
    response.raise_for_status()


def _get_secrets() -> list[dict]:
    """Get all secrets from the engine."""
    engine_url = state["engine_url"]
    url = get_org_scoped_url(engine_url, "/secrets")
    response = httpx.get(url, headers=get_auth_headers())
    response.raise_for_status()
    return response.json()["items"]  # type: ignore[no-any-return]


def _delete_secret(secret_id: str) -> None:
    """Delete a secret from the engine."""
    engine_url = state["engine_url"]
    url = get_org_scoped_url(engine_url, f"/secrets/{secret_id}")
    response = httpx.delete(url, headers=get_auth_headers())
    response.raise_for_status()
