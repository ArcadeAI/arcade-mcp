import base64
import io
import os
import re
import secrets
import tarfile
import time
from pathlib import Path
from typing import Any

import toml
from arcadepy import Arcade, NotFoundError
from httpx import Client, ConnectError, HTTPStatusError, TimeoutException
from packaging.requirements import Requirement
from pydantic import BaseModel, field_serializer, field_validator, model_validator
from rich.console import Console
from rich.table import Table

console = Console()


# Base class for versioned packages
class Package(BaseModel):
    name: str
    specifier: str | None = None

    @classmethod
    def from_requirement(cls, requirement_str: str) -> "Package":
        req = Requirement(requirement_str)
        return cls(name=req.name, specifier=str(req.specifier) if req.specifier else None)


# Base class for a list of packages
class Packages(BaseModel):
    packages: list[Package]

    # Convert string package i.e. "arcade>1.0.0" to a name and specifier
    # Specifiers are currently unused
    @field_validator("packages", mode="before")
    @classmethod
    def parse_package_requirements(cls, packages: list[str]) -> list[Package]:
        """Convert package requirement strings to Package objects."""
        return [Package.from_requirement(pkg) for pkg in packages]


# Base class for a local package
class LocalPackage(BaseModel):
    name: str
    content: str


# Base class for a list of local packages
class LocalPackages(BaseModel):
    packages: list[str]


# Custom repository configurations
class PackageRepository(Packages):
    index: str
    index_url: str
    trusted_host: str


# Pypi is a special case of a package repository
class Pypi(PackageRepository):
    index: str = "pypi"
    index_url: str = "https://pypi.org/simple"
    trusted_host: str = "pypi.org"


class Secret(BaseModel):
    value: str
    pattern: str | None = None


class Config(BaseModel):
    id: str
    enabled: bool = True
    timeout: int = 30
    retries: int = 3
    secret: Secret | None = None

    # Validate and parse the secret if required
    @field_validator("secret", mode="before")
    @classmethod
    def valid_secret(cls, v: str | Secret | None) -> Secret:
        # If the secret is a string, attempt to parse it as an environment variable or return the secret
        if isinstance(v, str):
            secret = get_env_secret(v)
        # If the secret has been manually set, return it
        elif isinstance(v, Secret):
            secret = v
        else:
            raise TypeError("Secret must be a string or a Secret object")
        # Check that the secret is not the default dev secret or empty
        if secret.value.strip() == "" or secret.value == "dev":
            raise ValueError("Secret must be a non-empty string and not 'dev'")
        return secret

    @field_serializer("secret")
    def serialize_secret(self, secret: Secret) -> str:
        if secret.pattern:
            return f"$env:{secret.pattern}"
        else:
            return secret.value


# Cloud request for deploying a worker
class Request(BaseModel):
    name: str
    secret: Secret
    enabled: bool
    timeout: int
    retries: int
    pypi: Pypi | None = None
    custom_repositories: list[PackageRepository] | None = None
    local_packages: list[LocalPackage] | None = None
    wait: bool = False

    @field_serializer("secret")
    def serialize_secret(self, secret: Secret) -> str:
        return secret.value

    def poll_worker_status(self, cloud_client: Client, worker_name: str) -> Any:
        while True:
            try:
                worker_resp = cloud_client.get(
                    f"{cloud_client.base_url}/api/v1/workers/{worker_name}?wait_for_completion=true",
                    timeout=10,
                )
                worker_resp.raise_for_status()
            except TimeoutException:
                time.sleep(1)
                continue
            except ConnectError as e:
                raise ValueError(f"Failed to connect to cloud: {e}")
            except HTTPStatusError as e:
                raise ValueError(f"Failed to start worker: {e.response.json()}")
            except Exception as e:
                raise ValueError(f"Failed to start worker: {e}")
            status = worker_resp.json()["data"]["status"]
            if status == "Running":
                return worker_resp.json()["data"]
            if status == "Failed":
                raise ValueError(f"Worker failed to start: {worker_resp.json()['data']['error']}")

    def execute(self, cloud_client: Client, engine_client: Arcade) -> Any:
        # Attempt to deploy worker to the cloud
        try:
            cloud_response = cloud_client.put(
                str(cloud_client.base_url) + "/api/v1/workers",
                json=self.model_dump(mode="json"),
                timeout=360,
            )
            cloud_response.raise_for_status()
        except ConnectError as e:
            raise ValueError(f"Failed to connect to cloud: {e}")
        except HTTPStatusError as e:
            raise ValueError(f"Failed to start worker: {e.response.json()}")
        except Exception as e:
            # change this so it handles errors that aren't just from cloud
            raise ValueError(f"Failed to start worker: {e}")

        parse_deployment_response(cloud_response.json())
        worker_data = self.poll_worker_status(cloud_client, self.name)

        try:
            # Check if worker already exists
            engine_client.workers.get(self.name)
            engine_client.workers.update(
                id=self.name,
                enabled=self.enabled,
                http={
                    "uri": worker_data["endpoint"],
                    "secret": self.secret.value,
                    "timeout": self.timeout,
                    "retry": self.retries,
                },
            )
        # If worker does not exist, create it
        except NotFoundError:
            engine_client.workers.create(
                id=self.name,
                enabled=self.enabled,
                http={
                    "uri": worker_data["endpoint"],
                    "secret": self.secret.value,
                    "timeout": self.timeout,
                    "retry": self.retries,
                },
            )

        except Exception as e:
            raise ValueError(f"Failed to add worker to engine: {e}")

        return cloud_response.json()


class Worker(BaseModel):
    toml_path: Path
    config: Config
    pypi_source: Pypi | None = None
    custom_source: list[PackageRepository] | None = None
    local_source: LocalPackages | None = None

    def request(self) -> Request:
        """Convert Deployment to a Request object."""
        self.validate_packages()
        self.compress_local_packages()
        if self.config.secret is None:
            raise ValueError("Secret is required")
        return Request(
            name=self.config.id,
            secret=self.config.secret,
            enabled=self.config.enabled,
            timeout=self.config.timeout,
            retries=self.config.retries,
            pypi=self.pypi_source,
            custom_repositories=self.custom_source,
            local_packages=self.compress_local_packages(),
        )

    # Search for local packages and compress the source code to send
    def compress_local_packages(self) -> list[LocalPackage] | None:
        """Compress local packages into a list of LocalPackage objects."""
        if self.local_source is None:
            return None

        def exclude_filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
            """Filter for files/directories to exclude from the compressed package"""
            basename = os.path.basename(tarinfo.name)

            # Exclude all hidden directories/files
            if basename.startswith("."):
                return None

            # Exclude specific directories/files
            if basename in {"dist", "build", "__pycache__", "venv", "coverage.xml"}:
                return None

            # Exclude lock files
            if basename.endswith(".lock"):
                return None

            return tarinfo

        # Compress local packages into a list of LocalPackage objects
        def process_package(package_path_str: str) -> LocalPackage:
            package_path = self.toml_path.parent / package_path_str

            if not package_path.exists():
                raise FileNotFoundError(f"Local package not found: {package_path}")
            if not package_path.is_dir():
                raise FileNotFoundError(f"Local package is not a directory: {package_path}")

            # Check that the package is a valid python package
            if (
                not (package_path / "pyproject.toml").is_file()
                and not (package_path / "setup.py").is_file()
            ):
                raise ValueError(
                    f"package '{package_path}' must contain a pyproject.toml or setup.py file"
                )

            # Compress the package into a byte stream and tar
            byte_stream = io.BytesIO()
            with tarfile.open(fileobj=byte_stream, mode="w:gz") as tar:
                tar.add(package_path, arcname=package_path.name, filter=exclude_filter)

            byte_stream.seek(0)
            package_bytes = byte_stream.read()
            package_bytes_b64 = base64.b64encode(package_bytes).decode("utf-8")

            return LocalPackage(name=package_path.name, content=package_bytes_b64)

        return list(map(process_package, self.local_source.packages))

    # Validate that there are no duplicate packages for each worker
    def validate_packages(self) -> None:
        """Validate packages."""
        packages: list[str] = []
        if self.pypi_source:
            for pypi_package in self.pypi_source.packages:
                packages.append(pypi_package.name)
        if self.custom_source:
            for repository in self.custom_source:
                for package in repository.packages:
                    packages.append(package.name)
        if self.local_source:
            for local_package in self.local_source.packages:
                packages.append(os.path.normpath(Path(local_package)))
        dupes = [x for n, x in enumerate(packages) if x in packages[:n]]
        if dupes:
            raise ValueError(f"Duplicate packages: {dupes}")


class Deployment(BaseModel):
    toml_path: Path
    worker: list[Worker]

    # Validate that there are no duplicate worker names
    @model_validator(mode="after")
    def validate_workers(self) -> "Deployment":
        for worker in self.worker:
            if sum(worker.config.id == w.config.id for w in self.worker) > 1:
                raise ValueError(f"Duplicate worker name: {worker.config.id}")
        return self

    # Load a deployment from a toml file
    @classmethod
    def from_toml(cls, toml_path: Path) -> "Deployment":
        try:
            with open(toml_path) as f:
                toml_data = toml.load(f)

            if not toml_data:
                raise ValueError(f"Empty TOML file: {toml_path}")

            # Add the toml path to each worker so relative packages can be found
            if "worker" in toml_data:
                for worker in toml_data["worker"]:
                    worker["toml_path"] = toml_path

            return cls(**toml_data, toml_path=toml_path)

        except toml.TomlDecodeError as e:
            raise ValueError(f"Invalid TOML format in {toml_path}: {e!s}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {toml_path}")

    # Save the deployment to a toml file
    def save(self) -> None:
        print("writing deployment file", self.toml_path)
        with open(self.toml_path, "w") as f:
            data = self.model_dump()
            # Remove the toml_path from the deployment file
            del data["toml_path"]
            for worker in data["worker"]:
                del worker["toml_path"]
            toml.dump(data, f)


# Create a demo deployment file with one worker
def create_demo_deployment(toml_path: Path, toolkit_name: str) -> None:
    """Create a deployment from a toml file."""
    deployment = Deployment(
        toml_path=toml_path,
        worker=[
            Worker(
                toml_path=toml_path,
                config=Config(
                    id="demo-worker",
                    enabled=True,
                    timeout=30,
                    retries=3,
                    secret=Secret(value=secrets.token_hex(16), pattern=None),
                ),
                local_source=LocalPackages(packages=[f"./{toolkit_name}"]),
            )
        ],
    )
    deployment.save()


# Get a currently existing deployment and add an additional local package
def update_deployment_with_local_packages(toml_path: Path, toolkit_name: str) -> None:
    """Update a deployment from a toml file."""
    deployment = Deployment.from_toml(toml_path)
    if deployment.worker[0].local_source is None:
        deployment.worker[0].local_source = LocalPackages(packages=[f"./{toolkit_name}"])
    else:
        deployment.worker[0].local_source.packages.append(f"./{toolkit_name}")
    deployment.save()


def get_env_secret(secret: str) -> Secret:
    """Parse a secret from an environment variable."""
    # Check if the secret contains the "${env:}" syntax
    pattern = r"\${env:([^}]+)}"
    matches = re.findall(pattern, secret)

    # Only allow a single match
    if matches and len(matches) == 1:
        match = matches[0].strip()
        # Attempt to lookup and create the secret
        print(f"Looking up secret: {match}")
        value = os.getenv(match)
        if value:
            return Secret(value=value, pattern=match)
        else:
            raise ValueError(f"Environment variable not found: {match}")
    elif matches and len(matches) > 1:
        raise ValueError(f"Multiple environment variables found in secret: {secret}")
    # If no matches are found, return the secret as is
    return Secret(value=secret, pattern=None)


def parse_deployment_response(response: dict) -> None:
    # Check what changes were made to the worker and display
    changes = response["data"]["changes"]
    additions = changes.get("additions", [])
    removals = changes.get("removals", [])
    updates = changes.get("updates", [])
    no_changes = changes.get("no_changes", [])
    print_deployment_table(additions, removals, updates, no_changes)


def print_deployment_table(
    additions: list, removals: list, updates: list, no_changes: list
) -> None:
    table = Table(title="Changed Packages")
    table.add_column("Adding", justify="right", style="green")
    table.add_column("Removing", justify="right", style="red")
    table.add_column("Updating", justify="right", style="yellow")
    table.add_column("No Changes", justify="right", style="dim")
    max_rows = max(len(additions), len(removals), len(updates), len(no_changes))

    # Add each row of worker package changes to the table
    for i in range(max_rows):
        addition = additions[i] if i < len(additions) else ""
        removal = removals[i] if i < len(removals) else ""
        update = updates[i] if i < len(updates) else ""
        no_change = no_changes[i] if i < len(no_changes) else ""
        table.add_row(addition, removal, update, no_change)
    console.print(table)
