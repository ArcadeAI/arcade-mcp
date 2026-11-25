import json
import secrets
from typing import Annotated

import jwt
from arcade_core import ToolResult
from arcade_serve.fastapi.worker import FastAPIWorker
from arcade_tdk import tool
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing_extensions import TypedDict

IMAGE_BLOCK = {"type": "image", "data": "aGVsbG8=", "mimeType": "image/png"}


class FileDetails(TypedDict):
    """A file's details."""

    name: str
    size: int


@tool
def get_picture() -> Annotated[ToolResult[FileDetails], "The file"]:
    """Return a file's details and its picture."""
    return ToolResult(FileDetails(name="cat.png", size=5), content=[IMAGE_BLOCK])


@tool
def get_broken_picture() -> Annotated[ToolResult[FileDetails], "The file"]:
    """Return a file's details and an image block with no data."""
    return ToolResult(FileDetails(name="cat.png", size=5), content=[{"type": "image"}])


def _invoke(func, name: str):
    app = FastAPI()
    worker = FastAPIWorker(app=app, secret=secrets.token_urlsafe(32))
    worker.register_tool(func, toolkit_name="Files")
    token = jwt.encode({"aud": "worker", "ver": "1"}, worker.secret, algorithm="HS256")

    with TestClient(app) as client:
        return client.post(
            "/worker/tools/invoke",
            json={"tool": {"toolkit": "Files", "name": name}, "inputs": {}},
            headers={"Authorization": f"Bearer {token}"},
        )


def test_worker_output_carries_value_and_picture_result():
    response = _invoke(get_picture, "GetPicture")

    value = {"name": "cat.png", "size": 5}
    output = response.json()["output"]
    assert response.json()["success"] is True
    assert output["value"] == value
    assert output["external"] == {
        "content": [IMAGE_BLOCK, {"type": "text", "text": json.dumps(value, ensure_ascii=False)}],
        "structuredContent": value,
        "isError": False,
    }


def test_worker_refuses_a_malformed_content_block():
    response = _invoke(get_broken_picture, "GetBrokenPicture")

    body = response.json()
    assert body["success"] is False
    assert body["output"].get("external") is None
    assert "Failed to serialize tool output" in body["output"]["error"]["message"]
