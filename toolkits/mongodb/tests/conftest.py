import os
import shutil
import subprocess
from os import environ

import pytest_asyncio
from arcade_mongodb.database_engine import DatabaseEngine

TEST_MONGODB_CONNECTION_STRING = (
    environ.get("TEST_MONGODB_CONNECTION_STRING") or "mongodb://localhost:27017"
)


@pytest_asyncio.fixture(autouse=True)
async def restore_database():
    """Restore the database from the dump before each test."""

    dump_file = f"{os.path.dirname(__file__)}/dump.js"

    # Execute the MongoDB dump script to restore test data
    mongosh_path = shutil.which("mongosh")
    if not mongosh_path:
        raise RuntimeError("mongosh executable not found in PATH")

    result = subprocess.run(
        [mongosh_path, TEST_MONGODB_CONNECTION_STRING, dump_file],
        check=True,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error loading test data: {result.stderr}")
        raise RuntimeError(f"Failed to load test data: {result.stderr}")

    yield  # This allows tests to run

    # Optional cleanup could go here if needed


@pytest_asyncio.fixture(autouse=True)
async def cleanup_engines():
    """Clean up database engines after each test to prevent connection leaks."""
    yield
    await DatabaseEngine.cleanup()
