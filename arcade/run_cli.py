import sys

from arcade.cli.main import cli

if __name__ == "__main__":
    # Support attaching debugger to cli
    mode = sys.argv[1] if len(sys.argv) > 1 else "dev"
    cli([mode])
