# Ignore hardcoded secret linting
# ruff: noqa: S105
# ruff: noqa: S106
import json
import os
from pathlib import Path

import pytest
from arcade_cli.deployment import (
    Config,
    Deployment,
    LocalPackages,
    Package,
    PackageRepository,
    Pypi,
    Secret,
    Worker,
)


@pytest.fixture
def test_dir():
    return Path(__file__).parent


def test_invalid_toml_path(test_dir):
    with pytest.raises(FileNotFoundError):
        Deployment.from_toml(test_dir / "test_files" / "invalid.toml")


def test_missing_fields(test_dir):
    with pytest.raises(ValueError):
        Deployment.from_toml(test_dir / "test_files" / "invalid.fields.worker.toml")


def test_deployment_parsing(test_dir):
    config_path = test_dir / "test_files" / "full.worker.toml"
    deployment = Deployment.from_toml(config_path)

    # Test config section
    assert deployment.worker[0].config.id == "test"
    assert deployment.worker[0].config.enabled is True
    assert deployment.worker[0].config.timeout == 10
    assert deployment.worker[0].config.retries == 3
    assert deployment.worker[0].config.secret == Secret(value="test-secret", pattern=None)

    # Test pypi section
    assert deployment.worker[0].pypi_source.packages == [Package(name="arcade-x")]

    # Test local_packages section
    assert deployment.worker[0].local_source.packages == ["./mock_toolkit"]

    # Test custom_repositories section
    repo = deployment.worker[0].custom_source[0]
    assert repo.index == "pypi"
    assert repo.index_url == "https://pypi.org/simple"
    assert repo.trusted_host == "pypi.org"
    assert repo.packages == [Package(name="arcade-ai", specifier=">=1.0.0")]

    repo = deployment.worker[0].custom_source[1]
    assert repo.index == "pypi2"
    assert repo.index_url == "https://pypi2.org/simple"
    assert repo.trusted_host == "pypi2.org"
    assert repo.packages == [Package(name="arcade-slack")]


def test_specifier():
    from packaging.requirements import Requirement

    req = Requirement("arcade-ai>=1.0.0")
    assert req.name == "arcade-ai"
    assert req.specifier == ">=1.0.0"


def test_deployment_dict(test_dir):
    config_path = test_dir / "test_files" / "full.worker.toml"
    deployment = Deployment.from_toml(config_path)
    expected = json.loads("""{
    "name": "test",
    "secret": "test-secret",
    "enabled": true,
    "timeout": 10,
    "retries": 3,
    "wait": false,
    "pypi": {
        "packages": [
            {
                "name": "arcade-x",
                "specifier": null
            }
        ],
        "index": "pypi",
        "index_url": "https://pypi.org/simple",
        "trusted_host": "pypi.org"
    },
    "custom_repositories": [
        {
            "packages": [
                {
                    "name": "arcade-ai",
                    "specifier": ">=1.0.0"
                }
            ],
            "index": "pypi",
            "index_url": "https://pypi.org/simple",
            "trusted_host": "pypi.org"
        },
        {
            "packages": [
                {
                    "name": "arcade-slack",
                    "specifier": null
                }
            ],
            "index": "pypi2",
            "index_url": "https://pypi2.org/simple",
            "trusted_host": "pypi2.org"
        }
    ],
    "local_packages": [
        {
            "name": "mock_toolkit",
            "content": "H4sIAOgdymcC/+2XwWuDMBTGPftXZDltMNIkJtrCOrpbL4PdSxmiKXNVIzHt6n+/OAvtNrqbMur7Xd7j5YGH5Ps+JBMyWbzEh6WKU2W8XqAdlyqlgTj17ZxRzriHDt4A7GobG/d5b5zwKSpsVqg5iwRjs6kMBJEzMYtC7nvA1VPoZPtqtc63mZ14/ek/krKrYVcp/655JtyLY4wHNHL6D5iMPCSH1H+dGtX84YBubbO5vvsn4P/g/+f+LyihPBSUSfD/sfl/EWclqZo+9B8Kcdn/eXTyf+bmTAjp9E+H1P9I/b8yWWlv8VLlub5HH9rk6Q2+A+mPhf+R/8Hv/GeQ/4Pkf/Qj/3lEpAgCOQUPGF3+V01l9LtKLLG6yAfLf07F2f9fq/+QhhTyfwhW7d2TSitrmrVfxoVCc4TPXwX298rUmS7bA0oYodhPVZ2YrLLH6bNbR8d1tNEGPZnExQn2451906Z2OyvczdBDqvaL+Ksnrn3EazAaAAAAAAAAAAAAAAAAAOiJT7MTVu0AKAAA"
        }
    ]
}""")
    got = deployment.worker[0].request().model_dump(mode="json")
    # Remove encoding part that contains the content
    got["local_packages"][0].pop("content")
    expected["local_packages"][0].pop("content")

    assert got == expected


def test_invalid_secret_parsing(test_dir):
    config_path = test_dir / "test_files" / "invalid.secret.worker.toml"
    with pytest.raises(ValueError):
        Deployment.from_toml(config_path)


def test_missing_local_package(test_dir):
    config_path = test_dir / "test_files" / "invalid.localfile.worker.toml"
    deployment = Deployment.from_toml(config_path)
    with pytest.raises(FileNotFoundError):
        deployment.worker[0].request()


def test_invalid_local_package(test_dir):
    config_path = test_dir / "test_files" / "invalid.localfile.worker.toml"
    deployment = Deployment.from_toml(config_path)
    with pytest.raises(FileNotFoundError):
        deployment.worker[1].request()


def test_unconfigured_local_package(test_dir):
    config_path = test_dir / "test_files" / "invalid.localfile.worker.toml"
    deployment = Deployment.from_toml(config_path)
    with pytest.raises(ValueError):
        deployment.worker[2].request()


def test_duplicate_pypi_packages():
    worker = Worker(
        toml_path=Path(__file__),
        config=Config(id="test", secret=Secret(value="test-secret", pattern=None)),
        pypi_source=Pypi(packages=["arcade-slack", "arcade-slack"]),
    )
    with pytest.raises(ValueError):
        worker.validate_packages()


def test_duplicate_custom_repository_packages():
    worker = Worker(
        toml_path=Path(__file__),
        config=Config(id="test", secret=Secret(value="test-secret", pattern=None)),
        custom_source=[
            PackageRepository(
                index="pypi",
                index_url="https://pypi.org/simple",
                trusted_host="pypi.org",
                packages=["arcade-slack", "arcade-slack"],
            )
        ],
    )
    with pytest.raises(ValueError):
        worker.validate_packages()


def test_duplicate_local_packages():
    worker = Worker(
        toml_path=Path(__file__),
        config=Config(id="test", secret=Secret(value="test-secret", pattern=None)),
        local_source=LocalPackages(packages=["./mock_toolkit", "./mock_toolkit"]),
    )
    with pytest.raises(ValueError):
        worker.validate_packages()


def test_duplicate_all_typed_packages():
    worker = Worker(
        toml_path=Path(__file__),
        config=Config(id="test", secret=Secret(value="test-secret", pattern=None)),
        pypi_source=Pypi(packages=["arcade-slack"]),
        custom_source=[
            PackageRepository(
                index="pypi",
                index_url="https://pypi.org/simple",
                trusted_host="pypi.org",
                packages=["arcade-slack", "arcade-x"],
            )
        ],
        local_source=LocalPackages(packages=["./arcade-x"]),
    )
    with pytest.raises(ValueError):
        worker.validate_packages()


def test_duplicate_worker_names():
    worker = Worker(
        toml_path=Path(__file__),
        config=Config(id="test", secret=Secret(value="test-secret", pattern=None)),
    )
    worker2 = Worker(
        toml_path=Path(__file__),
        config=Config(id="test", secret=Secret(value="test-secret", pattern=None)),
    )
    with pytest.raises(ValueError):
        Deployment(workers=[worker, worker2])


def test_secret_parsing(test_dir):
    os.environ["TEST_WORKER_SECRET"] = "test-secret"
    deployment = Deployment.from_toml(test_dir / "test_files" / "env.secret.worker.toml")
    assert deployment.worker[0].config.secret == Secret(
        value="test-secret", pattern="TEST_WORKER_SECRET"
    )
