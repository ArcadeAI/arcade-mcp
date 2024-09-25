import importlib.metadata
import importlib.util
import logging
import os
import types
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

from arcade.core.errors import ToolkitLoadError
from arcade.core.parse import get_tools_from_file

logger = logging.getLogger(__name__)


class Toolkit(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    """Name of the toolkit"""

    package_name: str
    """Name of the package holding the toolkit"""

    tools: dict[str, list[str]] = defaultdict(list)
    """Mapping of module names to tools"""

    # Other python package metadata
    version: str
    description: str
    author: list[str] = []
    repository: str | None = None
    homepage: str | None = None

    @field_validator("name", mode="before")
    def strip_arcade_prefix(cls, value: str) -> str:
        """
        Validator to strip the 'arcade_' prefix from the name if it exists.
        """
        if value.startswith("arcade_"):
            return value[len("arcade_") :]
        return value

    @classmethod
    def from_module(cls, module: types.ModuleType) -> "Toolkit":
        """
        Load a toolkit from an imported python module

        >>> import arcade_math
        >>> toolkit = Toolkit.from_module(arcade_math)
        """
        return cls.from_package(module.__name__)

    @classmethod
    def from_package(cls, package: str) -> "Toolkit":
        """
        Load a Toolkit from a Python package
        """
        try:
            metadata = importlib.metadata.metadata(package)
            name = metadata["Name"]
            package_name = package
            version = metadata["Version"]
            description = metadata.get("Summary", "")  # type: ignore[attr-defined]
            author = metadata.get_all("Author-email")
            homepage = metadata.get("Home-page", None)  # type: ignore[attr-defined]
            repo = metadata.get("Repository", None)  # type: ignore[attr-defined]

        except importlib.metadata.PackageNotFoundError as e:
            raise ToolkitLoadError(f"Package {package} not found.") from e
        except KeyError as e:
            raise ToolkitLoadError(f"Metadata key error for package {package}.") from e
        except Exception as e:
            raise ToolkitLoadError(f"Failed to load metadata for package {package}.") from e

        # Get the package directory
        try:
            package_dir = Path(get_package_directory(package))
        except (ImportError, AttributeError) as e:
            raise ToolkitLoadError(f"Failed to locate package directory for {package}.") from e

        # Get all python files in the package directory
        try:
            modules = [f for f in package_dir.glob("**/*.py") if f.is_file()]
        except OSError as e:
            raise ToolkitLoadError(
                f"Failed to locate Python files in package directory for {package}."
            ) from e

        toolkit = cls(
            name=name,
            package_name=package_name,
            version=version,
            description=description,
            author=author if author else [],
            homepage=homepage,
            repository=repo,
        )

        for module_path in modules:
            relative_path = module_path.relative_to(package_dir)
            import_path = ".".join(relative_path.with_suffix("").parts)
            import_path = f"{package_name}.{import_path}"
            toolkit.tools[import_path] = get_tools_from_file(str(module_path))

        if not toolkit.tools:
            raise ToolkitLoadError(f"No tools found in package {package}")

        return toolkit

    @classmethod
    def find_all_arcade_toolkits(cls) -> list["Toolkit"]:
        """
        Find all installed packages prefixed with 'arcade_' in the current
        Python interpreter's environment and load them as Toolkits.

        Returns:
            List[Toolkit]: A list of Toolkit instances.
        """
        import sysconfig

        # Get the site-packages directory of the current interpreter
        site_packages_dir = sysconfig.get_paths()["purelib"]
        arcade_packages = [
            dist.metadata["Name"]
            for dist in importlib.metadata.distributions(path=[site_packages_dir])
            if dist.metadata["Name"].startswith("arcade_")
        ]
        toolkits = []
        for package in arcade_packages:
            try:
                toolkits.append(cls.from_package(package))
            except ToolkitLoadError as e:
                logger.warning(f"Warning: {e} Skipping toolkit {package}")
        return toolkits


def get_package_directory(package_name: str) -> str:
    """
    Get the directory of a Python package
    """

    spec = importlib.util.find_spec(package_name)
    if spec is None:
        raise ImportError(f"Cannot find package named {package_name}")

    if spec.origin:
        # If the package has an origin, return the directory of the origin
        return os.path.dirname(spec.origin)
    elif spec.submodule_search_locations:
        # If the package is a namespace package, return the first search location
        return spec.submodule_search_locations[0]
    else:
        raise ImportError(f"Package {package_name} does not have a file path associated with it")
