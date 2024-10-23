import io
import ipaddress
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable

from rich.console import Console

console = Console(highlight=False)
logger = logging.getLogger(__name__)

known_engine_config_locations = [
    "/etc/arcade-ai",
    "/etc/arcade-engine",
    "/opt/homebrew/etc/arcade-engine",
]

if os.environ.get("HOMEBREW_REPOSITORY") is not None:
    homebrew_home = os.path.join(os.environ["HOMEBREW_REPOSITORY"], "etc", "arcade-engine")
    known_engine_config_locations.append(homebrew_home)


def start_servers(
    host: str,
    port: int,
    engine_config: str | None,
    engine_env: str | None = None,
    debug: bool = False,
) -> None:
    """
    Start the actor and engine servers.

    Args:
        host: Host for the actor server.
        port: Port for the actor server.
        engine_config: Path to the engine configuration file.
        engine_env: Path to the engine environment file.
        debug: Whether to run in debug mode.
    """
    # Validate host and port
    host = _validate_host(host)
    port = _validate_port(port)

    # Ensure engine_config is provided and validated
    engine_config = _get_config_file(engine_config, default_filename="engine.yaml")

    # Ensure engine_env is provided or found and either way, validated
    env_file = _get_config_file(engine_env, default_filename="arcade.env", optional=True)

    # Prepare command-line arguments for the actor server and engine
    actor_cmd = _build_actor_command(host, port, debug)

    # even if the user didn't pass an env file we may have found it in the default locations
    engine_cmd = _build_engine_command(engine_config, engine_env=env_file if env_file else None)

    # Start and manage the processes
    _manage_processes(actor_cmd, engine_cmd, debug=debug)


def _validate_host(host: str) -> str:
    """
    Validates the host input.

    Args:
        host: Host for the actor server.

    Returns:
        The validated host as a string.

    Raises:
        ValueError: If the host is invalid.
    """
    try:
        # Validate IP address
        ipaddress.ip_address(host)
    except ValueError:
        # Optionally, validate hostname
        if not host.isalnum() and "-" not in host and "." not in host:
            console.print(f"❌ Invalid host: {host}", style="bold red")
            raise ValueError("Invalid host.")
    return host


def _validate_port(port: int) -> int:
    """
    Validates the port input.

    Args:
        port: Port for the actor server.

    Returns:
        The validated port as an integer.

    Raises:
        ValueError: If the port is out of the valid range.
    """
    if not (1 <= port <= 65535):
        console.print(f"❌ Invalid port: {port}", style="bold red")
        raise ValueError("Invalid port.")
    return port


def _get_config_file(
    file_path: str | None, default_filename: str = "engine.yaml", optional: bool = False
) -> str | None:
    """
    Determines and validates the config file path.

    Args:
        file_path: Optional path provided by the user.
        default_filename: The default filename to look for.
        optional: Whether the config file is optional.

    Returns:
        The resolved config file path. None if the file is optional and not found.

    Raises:
        RuntimeError: If the config file is not found and is not optional.
    """
    if file_path:
        config_path = Path(os.path.expanduser(file_path)).resolve()
        if not config_path.is_file():
            console.print(f"❌ Config file not found at {config_path}", style="bold red")
            raise RuntimeError(f"Config file not found at {config_path}")
        return str(config_path)

    # Look for the file in the current working directory
    config_path = Path(os.getcwd()) / default_filename
    if config_path.is_file():
        console.print(f"Using config file at {config_path}", style="bold green")
        return str(config_path)

    # Look for the file in the user's home directory under .arcade/
    home_config_path = Path.home() / ".arcade" / default_filename
    if home_config_path.is_file():
        console.print(f"Using config file at {home_config_path}", style="bold green")
        return str(home_config_path)

    # Look for known installation directories
    for path in known_engine_config_locations:
        etc_path = Path(path) / default_filename
        if etc_path.is_file():
            console.print(f"Using config file at {etc_path}", style="bold green")
            return str(etc_path)

    if optional:
        console.print(
            f"⚠️ Optional config file '{default_filename}' not found in either of the default locations: "
            f"1) current working directory: {Path.cwd() / default_filename}, or "
            f"2) user's home directory: {Path.home() / '.arcade' / default_filename}.",
            style="bold yellow",
        )
        return None

    console.print(
        f"❌ Config file '{default_filename}' not found in any of the default locations: "
        f"1) current working directory: {Path.cwd() / default_filename}, or "
        f"2) user's home directory: {Path.home() / '.arcade' / default_filename}.",
        style="bold red",
    )
    raise RuntimeError(f"Config file '{default_filename}' not found.")


def _build_actor_command(host: str, port: int, debug: bool) -> list[str]:
    """
    Builds the command to start the actor server.

    Args:
        host: Host for the actor server.
        port: Port for the actor server.
        debug: Whether to run in debug mode.

    Returns:
        The command as a list.
    """
    # Expand full path to "arcade" executable
    arcade_bin = shutil.which("arcade")
    if not arcade_bin:
        console.print(
            "❌ Arcade binary not found, please install with `pip install arcade-ai`",
            style="bold red",
        )
        sys.exit(1)
    cmd = [
        arcade_bin,
        "actorup",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if debug:
        cmd.append("--debug")
    return cmd


def _build_engine_command(engine_config: str | None, engine_env: str | None = None) -> list[str]:
    """
    Builds the command to start the engine.

    Args:
        engine_config: Path to the engine configuration file.
        engine_env: Path to the engine environment file.

    Returns:
        The command as a list.
    """
    # This should never happen, but we'll check regardless
    if not engine_config:
        console.print("❌ Engine configuration file not found", style="bold red")
        sys.exit(1)

    engine_bin = shutil.which("arcade-engine")
    if not engine_bin:
        console.print(
            "❌ Engine binary not found, refer to the installation guide at "
            "https://docs.arcade-ai.com/guides/installation for how to install the engine",
            style="bold red",
        )
        sys.exit(1)
    cmd = [
        engine_bin,
        "-c",
        engine_config,
    ]
    if engine_env:
        cmd.append("-e")
        cmd.append(engine_env)

    return cmd


def _manage_processes(
    actor_cmd: list[str],
    engine_cmd: list[str],
    engine_env: dict[str, str] | None = None,
    debug: bool = False,
) -> None:
    """
    Manages the lifecycle of the actor and engine processes.

    Args:
        actor_cmd: The command to start the actor server.
        engine_cmd: The command to start the engine.
        engine_env: Environment variables to set for the engine.
        debug: Whether to run in debug mode.
    """
    actor_process: subprocess.Popen | None = None
    engine_process: subprocess.Popen | None = None

    def terminate_processes(exit_program: bool = False) -> None:
        console.print("Terminating child processes...", style="bold yellow")
        _terminate_process(actor_process)
        _terminate_process(engine_process)
        if exit_program:
            sys.exit(0)

    _setup_signal_handlers(terminate_processes)

    retry_count = 0
    max_retries = 1  # Define the maximum number of retries

    while retry_count <= max_retries:
        try:
            # Start the actor server
            console.print("Starting actor server...", style="bold green")
            actor_process = _start_process("Actor", actor_cmd, debug=debug)

            # Wait a bit to ensure actor is up
            time.sleep(2)

            # Start the engine
            console.print("Starting engine...", style="bold green")
            engine_process = _start_process("Engine", engine_cmd, env=engine_env, debug=debug)

            # Monitor processes
            _monitor_processes(actor_process, engine_process)

            # If we reach here, one of the processes has exited
            retry_count += 1
            console.print(
                f"Processes exited. Retry {retry_count} of {max_retries}.", style="bold yellow"
            )

            if retry_count >= max_retries:
                console.print(f"❌ Exiting after {max_retries} retries", style="bold red")
                terminate_processes(exit_program=True)
                break  # Exit the loop

        except Exception as e:
            console.print(f"❌ Exception occurred: {e}", style="bold red")
            terminate_processes()
            retry_count += 1
            if retry_count > max_retries:
                console.print(
                    f"❌ Exiting after {retry_count - 1} retries due to exceptions",
                    style="bold red",
                )
                sys.exit(1)
                break  # Not strictly necessary, but good practice

    console.print("Exiting...", style="bold red")
    sys.exit(1)


def _start_process(
    name: str, cmd: list[str], env: dict[str, str] | None = None, debug: bool = False
) -> subprocess.Popen:
    """
    Starts a subprocess and begins streaming its output.

    Args:
        name: Name of the process.
        cmd: Command to execute.
        env: Environment variables to set for the process.
        debug: Whether to run in debug mode.
    Returns:
        The subprocess.Popen object.

    Raises:
        RuntimeError: If the process fails to start.
    """
    _env = os.environ.copy()
    if env:
        _env.update(env)

    if debug:
        _env["GIN_MODE"] = "debug"
    else:
        _env["GIN_MODE"] = "release"

    if name == "Actor":
        _env["PYTHONUNBUFFERED"] = "1"

    try:
        process = subprocess.Popen(  # noqa: S603, RUF100
            cmd,
            env=_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1,
            shell=False,
        )
        _stream_output(process, name)
        return process  # noqa: TRY300
    except Exception as e:
        console.print(f"❌ Failed to start {name}: {e}", style="bold red")
        raise RuntimeError(f"Failed to start {name}")


def _stream_output(process: subprocess.Popen, name: str) -> None:
    """
    Streams the output from a subprocess to the console.

    Args:
        process: The subprocess.Popen object.
        name: Name of the process.
    """
    stdout_style = "green" if name == "Actor" else "#87CEFA"

    def stream(pipe: io.TextIOWrapper | None, style: str) -> None:
        if pipe is None:
            return
        with pipe:
            for line in iter(pipe.readline, ""):
                line = line.rstrip()

                if "DEBUG" in line:
                    line = line.replace("DEBUG", "[#87CEFA]DEBUG[/#87CEFA]", 1)
                if "INFO" in line:
                    line = line.replace("INFO", "[#109a10]INFO[/#109a10]", 1)
                if "WARNING" in line:
                    line = line.replace("WARNING", "[#FFA500]WARNING[/#FFA500]", 1)
                if "ERROR" in line:
                    line = line.replace("ERROR", "[#FF0000]ERROR[/#FF0000]", 1)
                console.print(f"[{style}]{name}>[/{style}] {line}")

    threading.Thread(target=stream, args=(process.stdout, stdout_style), daemon=True).start()
    threading.Thread(target=stream, args=(process.stderr, "red"), daemon=True).start()


def _monitor_processes(actor_process: subprocess.Popen, engine_process: subprocess.Popen) -> None:
    """
    Monitors the actor and engine processes, restarts them if they exit.

    Args:
        actor_process: The actor subprocess.
        engine_process: The engine subprocess.
    """

    while True:
        actor_status = actor_process.poll()
        engine_status = engine_process.poll()

        if actor_status is not None or engine_status is not None:
            if actor_status is not None:
                console.print(
                    f"Actor process exited with code {actor_status}. Restarting both processes...",
                    style="bold red",
                )
            if engine_status is not None:
                console.print(
                    f"Engine process exited with code {engine_status}. Restarting both processes...",
                    style="bold red",
                )
            _terminate_process(actor_process)
            _terminate_process(engine_process)
            time.sleep(1)
            break  # Exit to restart both processes
        else:
            time.sleep(1)


def _terminate_process(process: subprocess.Popen | None) -> None:
    """
    Terminates a subprocess if it's running.

    Args:
        process: The subprocess.Popen object.
    """
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def _setup_signal_handlers(terminate_processes: Callable[[bool], None]) -> None:
    """
    Setup signal handlers to handle process termination signals.

    Args:
        terminate_processes: Function to call to terminate child processes.
    """
    signals_to_handle = ["SIGINT", "SIGTERM", "SIGQUIT", "SIGHUP"]

    for sig_name in signals_to_handle:
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue  # Signal not available on this platform
        try:
            # Use a lambda to pass the terminate_processes function
            signal.signal(
                sig,
                lambda signum, frame: _handle_signal(signum, terminate_processes),
            )
        except (ValueError, RuntimeError):
            # Signal handling not allowed in this thread or invalid signal
            console.print(f"Warning: Cannot set handler for {sig_name}", style="bold yellow")
            continue


def _handle_signal(signum: int, terminate_processes: Callable[[bool], None]) -> None:
    """
    Handle received signal and terminate child processes.

    Args:
        signum: The signal number received.
        terminate_processes: Function to call to terminate child processes.
    """
    signal_name = signal.Signals(signum).name
    console.print(f"Received {signal_name}. Shutting down...", style="bold yellow")
    terminate_processes(exit_program=True)  # type: ignore[call-arg]
