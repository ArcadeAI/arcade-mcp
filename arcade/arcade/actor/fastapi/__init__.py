import importlib.util

# FastAPI is an optional dependency, so make sure it's installed
if importlib.util.find_spec("fastapi") is None:
    raise ImportError(
        "FastAPI is not installed. Please install it using `pip install arcade-ai[fastapi]`."
    )
