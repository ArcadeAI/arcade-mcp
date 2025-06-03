import httpx
import typer
from arcadepy import Arcade, NotFoundError
from rich.console import Console
from rich.table import Table

from arcade_cli.constants import (
    PROD_CLOUD_HOST,
    PROD_ENGINE_HOST,
)
from arcade_cli.utils import (
    OrderCommands,
    compute_base_url,
    validate_and_get_config,
)

console = Console()


app = typer.Typer(
    cls=OrderCommands,
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
    Manage users in the system.
    """
    engine_url = compute_base_url(force_tls, force_no_tls, host, port)
    state["engine_url"] = engine_url


@app.command("list", help="List all workers")
def list_workers(
    cloud_host: str = typer.Option(
        PROD_CLOUD_HOST,
        "--cloud-host",
        "-c",
        help="The Arcade Engine host.",
        hidden=True,
    ),
    cloud_port: int = typer.Option(
        None,
        "--cloud-port",
        "-cp",
        help="The port of the Arcade Engine host.",
        hidden=True,
    ),
    force_tls: bool = typer.Option(
        False,
        "--tls",
        help="Whether to force TLS for the connection to the Arcade Engine.",
        hidden=True,
    ),
    force_no_tls: bool = typer.Option(
        False,
        "--no-tls",
        help="Whether to disable TLS for the connection to the Arcade Engine.",
        hidden=True,
    ),
) -> None:
    config = validate_and_get_config()
    engine_url = state["engine_url"]
    client = Arcade(api_key=config.api.key, base_url=engine_url)
    deployments = []
    try:
        cloud_url = compute_base_url(force_tls, force_no_tls, cloud_host, cloud_port)
        cloud_client = httpx.Client(base_url=cloud_url)
        response = cloud_client.get(
            "/api/v1/workers", headers={"Authorization": f"Bearer {config.api.key}"}
        )
        response.raise_for_status()
        deployments = response.json()["data"]["workers"]
    except Exception as e:
        console.log(f"Failed to get cloud deployments: {e}")

    print_worker_table(client, deployments)


def print_worker_table(client: Arcade, deployments: list[dict]) -> None:
    workers = client.workers.list()
    if not workers.items:
        console.print("No workers found", style="bold red")
        return

    # Create and print a table of worker information
    table = Table(title="Workers")
    table.add_column("ID")
    table.add_column("Cloud Deployed")
    table.add_column("Engine Registered")
    table.add_column("Enabled")
    table.add_column("Host")
    table.add_column("Toolkits")

    # Track workers that are registered in the engine
    engine_workers = []
    for worker in workers.items:
        if worker.id is None:
            continue
        engine_workers.append(worker.id)
        # Check if the worker is deployed in the cloud
        is_deployed = is_cloud_deployment(worker.id, deployments)
        # Get the toolkits for the worker

        tools = get_toolkits(client, worker.id)
        uri = worker.http.uri if worker.http and worker.http.uri else ""
        table.add_row(
            worker.id,
            str(is_deployed),
            str(True),
            str(worker.enabled),
            compare_endpoints(worker.id, uri, deployments),
            "Could not fetch toolkits" if tools == "" else tools,
        )
    for deployment in deployments:
        if deployment["name"] not in engine_workers:
            table.add_row(deployment["name"], "True", "False", "False", deployment["endpoint"], "")
    console.print(table)


# Check if the worker is in the list of cloud deployments
def is_cloud_deployment(name: str, deployments: list[dict]) -> bool:
    return any(deployment["name"] == name for deployment in deployments)


# Compare the endpoint of the worker in the engine to the endpoint in the cloud
# Return a highlighted diff if the endpoint in the engine is different from the endpoint in the cloud
def compare_endpoints(worker_id: str, engine_endpoint: str, deployments: list[dict]) -> str:
    if is_cloud_deployment(worker_id, deployments):
        for deployment in deployments:
            deployment_endpoint = deployment["endpoint"]
            if deployment_endpoint == engine_endpoint:
                return engine_endpoint
            return f"[red]Endpoint Mismatch[/red]\n[yellow]Registered Endpoint: {engine_endpoint}[/yellow]\n[green]Actual Endpoint:     {deployment_endpoint}[/green]"
    return engine_endpoint


@app.command("enable", help="Enable a worker")
def enable_worker(
    worker_id: str,
) -> None:
    config = validate_and_get_config()
    engine_url = state["engine_url"]
    arcade = Arcade(api_key=config.api.key, base_url=engine_url)
    try:
        arcade.workers.update(worker_id, enabled=True)
    except Exception as e:
        console.print(f"Error enabling worker: {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command("disable", help="Disable a worker")
def disable_worker(
    worker_id: str,
) -> None:
    config = validate_and_get_config()
    engine_url = state["engine_url"]
    arcade = Arcade(api_key=config.api.key, base_url=engine_url)
    try:
        arcade.workers.update(worker_id, enabled=False)
    except Exception as e:
        console.print(f"Error disabling worker: {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command("rm", help="Remove a worker")
def rm_worker(
    worker_id: str,
    engine_only: bool = typer.Option(
        False,
        "--deregister",
        "-d",
        help="Deregister the worker from the engine",
    ),
    cloud_host: str = typer.Option(
        PROD_CLOUD_HOST,
        "--cloud-host",
        "-c",
        help="The Arcade Engine host.",
        hidden=True,
    ),
    cloud_port: int = typer.Option(
        None,
        "--cloud-port",
        "-cp",
        help="The port of the Arcade Engine host.",
        hidden=True,
    ),
    force_tls: bool = typer.Option(
        False,
        "--tls",
        help="Whether to force TLS for the connection to the Arcade Engine.",
        hidden=True,
    ),
    force_no_tls: bool = typer.Option(
        False,
        "--no-tls",
        help="Whether to disable TLS for the connection to the Arcade Engine.",
        hidden=True,
    ),
) -> None:
    config = validate_and_get_config()
    engine_url = state["engine_url"]
    cloud_url = compute_base_url(force_tls, force_no_tls, cloud_host, cloud_port)

    # First attempt to delete from the cloud
    if not engine_only:
        try:
            client = httpx.Client()
            response = client.delete(
                f"{cloud_url}/api/v1/workers/{worker_id}",
                headers={"Authorization": f"Bearer {config.api.key}"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                console.print(
                    "Deployment not found. To deregister the worker from the engine, use the --deregister flag.",
                    style="bold red",
                )
                raise typer.Exit(code=1)
            else:
                console.print(f"Error deleting deployment: {e}", style="bold red")
                raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"Error deleting deployment: {e}", style="bold red")
            raise typer.Exit(code=1)

    # Then try to delete from the engine
    try:
        arcade = Arcade(api_key=config.api.key, base_url=engine_url)
        arcade.workers.delete(worker_id)
    except NotFoundError:
        console.print("Worker not found", style="bold red")
    except Exception as e:
        console.print(f"Error deleting worker from engine: {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command("logs", help="Get logs for a worker")
def worker_logs(
    worker_id: str,
    cloud_host: str = typer.Option(
        PROD_CLOUD_HOST,
        "--cloud-host",
        "-c",
        help="The Arcade Engine host.",
        hidden=True,
    ),
    cloud_port: int = typer.Option(
        None,
        "--cloud-port",
        "-cp",
        help="The port of the Arcade Engine host.",
        hidden=True,
    ),
    force_tls: bool = typer.Option(
        False,
        "--tls",
        help="Whether to force TLS for the connection to the Arcade Engine.",
        hidden=True,
    ),
    force_no_tls: bool = typer.Option(
        False,
        "--no-tls",
        help="Whether to disable TLS for the connection to the Arcade Engine.",
        hidden=True,
    ),
) -> None:
    config = validate_and_get_config()
    cloud_url = compute_base_url(force_tls, force_no_tls, cloud_host, cloud_port)
    try:
        with httpx.stream(
            "GET",
            f"{cloud_url}/api/v1/workers/logs/{worker_id}",
            headers={"Authorization": f"Bearer {config.api.key}", "Accept": "text/event-stream"},
            # allow the connection to stay open indefinitely
            timeout=None,  # noqa: S113
        ) as s:
            for line in s.iter_lines():
                if not line or "[DONE]" in line:  # Skip empty lines
                    continue
                if "event: error" in line:
                    console.print("Could not stream logs", style="bold red")
                if line.startswith("data:"):
                    # Extract just the data portion after 'data:'
                    data = line[5:].strip()  # Remove 'data:' prefix and whitespace
                    console.print(data, markup=False)
    except Exception as e:
        console.print(f"Error connecting to log stream: {e}", style="bold red")
        raise typer.Exit(code=1)


def get_toolkits(client: Arcade, worker_id: str | None) -> str:
    if worker_id is None:
        return ""
    try:
        # Get tools for the given worker
        tools = client.workers.tools(worker_id)
        toolkits: list[str] = []
        if not tools.items:
            return ""

        # Get toolkit names
        for page in tools.iter_pages():
            for tool in page.items:
                if tool.toolkit.name not in toolkits:
                    toolkits.append(tool.toolkit.name)
        return ", ".join(toolkits)
    except NotFoundError:
        return ""
    except Exception as e:
        console.print(f"Error getting worker tools: {e}", style="bold red")
        raise typer.Exit(code=1)
