import sys

from arcade_cli.main import cli

if __name__ == "__main__":
    # Supports attaching debugger to cli. Run from ../.vscode/launch.json.
    if len(sys.argv) < 2:
        raise ValueError("At least one argument is required.")
    args = sys.argv[1:]
    cli(args)
