import importlib.util

# Flask is an optional dependency, so make sure it's installed
if importlib.util.find_spec("flask") is None:
    raise ImportError(
        "Flask is not installed. Please install it using `pip install arcade-ai[flask]`."
    )
