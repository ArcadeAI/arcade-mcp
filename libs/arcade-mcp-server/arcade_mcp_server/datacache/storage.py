from __future__ import annotations

import asyncio
import os
import shutil
from dataclasses import dataclass
from typing import Any, Protocol

try:
    import boto3  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    boto3 = None  # type: ignore[assignment]


class DatacacheStorageError(RuntimeError):
    pass


class DatacacheLocation(Protocol):
    """Marker protocol for storage-specific locations."""


class DatacacheStorage(Protocol):
    def location_for_digest(self, digest: str) -> DatacacheLocation: ...

    async def download_if_exists(self, loc: DatacacheLocation, local_path: str) -> bool: ...

    async def upload(self, loc: DatacacheLocation, local_path: str) -> None: ...


@dataclass(frozen=True)
class S3Location:
    bucket: str
    key: str


class S3DatacacheStorage:
    def __init__(
        self,
        *,
        bucket: str,
        prefix: str,
        endpoint_url: str | None = None,
        region_name: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
    ) -> None:
        if boto3 is None:
            raise DatacacheStorageError(
                "boto3 dependency not installed; required for datacache S3 sync"
            )
        self._bucket = bucket
        self._prefix = prefix.strip("/").strip()
        self._client_kwargs: dict[str, Any] = {}
        if endpoint_url:
            self._client_kwargs["endpoint_url"] = endpoint_url
        if region_name:
            self._client_kwargs["region_name"] = region_name
        if aws_access_key_id and aws_secret_access_key:
            self._client_kwargs["aws_access_key_id"] = aws_access_key_id
            self._client_kwargs["aws_secret_access_key"] = aws_secret_access_key
            if aws_session_token:
                self._client_kwargs["aws_session_token"] = aws_session_token

    def location_for_digest(self, digest: str) -> S3Location:
        key = f"{self._prefix}/{digest}.duckdb"
        return S3Location(bucket=self._bucket, key=key)

    async def download_if_exists(self, loc: DatacacheLocation, local_path: str) -> bool:
        loc = loc  # type: ignore[assignment]
        if not isinstance(loc, S3Location):
            raise DatacacheStorageError("Invalid S3 location type")
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        def _download() -> bool:
            s3 = boto3.client("s3", **self._client_kwargs)
            try:
                s3.head_object(Bucket=loc.bucket, Key=loc.key)
            except Exception:
                return False
            s3.download_file(loc.bucket, loc.key, local_path)
            return True

        return await asyncio.to_thread(_download)

    async def upload(self, loc: DatacacheLocation, local_path: str) -> None:
        loc = loc  # type: ignore[assignment]
        if not isinstance(loc, S3Location):
            raise DatacacheStorageError("Invalid S3 location type")
        if not os.path.exists(local_path):
            raise DatacacheStorageError(f"Local datacache file missing: {local_path}")

        def _upload() -> None:
            s3 = boto3.client("s3", **self._client_kwargs)
            s3.upload_file(local_path, loc.bucket, loc.key)

        await asyncio.to_thread(_upload)


@dataclass(frozen=True)
class LocalFileLocation:
    path: str


class LocalFileDatacacheStorage:
    """Local filesystem storage backend.

    This is useful for local-only MCP servers and tests. It stores a canonical file per digest
    under `storage_dir`, and each tool execution works on a separate `local_path` which is
    copied from/to the canonical location.
    """

    def __init__(self, *, storage_dir: str) -> None:
        self._storage_dir = storage_dir

    def location_for_digest(self, digest: str) -> LocalFileLocation:
        os.makedirs(self._storage_dir, exist_ok=True)
        return LocalFileLocation(path=os.path.join(self._storage_dir, f"{digest}.duckdb"))

    async def download_if_exists(self, loc: DatacacheLocation, local_path: str) -> bool:
        loc = loc  # type: ignore[assignment]
        if not isinstance(loc, LocalFileLocation):
            raise DatacacheStorageError("Invalid local file location type")
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        if not os.path.exists(loc.path):
            return False

        def _copy_in() -> None:
            shutil.copy2(loc.path, local_path)

        await asyncio.to_thread(_copy_in)
        return True

    async def upload(self, loc: DatacacheLocation, local_path: str) -> None:
        loc = loc  # type: ignore[assignment]
        if not isinstance(loc, LocalFileLocation):
            raise DatacacheStorageError("Invalid local file location type")
        if not os.path.exists(local_path):
            raise DatacacheStorageError(f"Local datacache file missing: {local_path}")

        os.makedirs(os.path.dirname(loc.path), exist_ok=True)

        def _copy_out() -> None:
            shutil.copy2(local_path, loc.path)

        await asyncio.to_thread(_copy_out)
