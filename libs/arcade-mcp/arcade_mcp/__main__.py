"""Enable running arcade-mcp as a module: python -m arcade_mcp"""

import sys
from pathlib import Path

# Default behavior when run as a module is to look for server.py in current directory
if __name__ == "__main__":
    server_file = Path.cwd() / "server.py"
    
    if not server_file.exists():
        print("Error: No server.py found in current directory", file=sys.stderr)
        print("Create a server.py file or run from a directory containing one", file=sys.stderr)
        sys.exit(1)
    
    # Import and run the server
    import importlib.util
    spec = importlib.util.spec_from_file_location("server", server_file)
    if spec and spec.loader:
        server = importlib.util.module_from_spec(spec)
        sys.modules["server"] = server
        spec.loader.exec_module(server)
    else:
        print("Error: Failed to load server.py", file=sys.stderr)
        sys.exit(1)