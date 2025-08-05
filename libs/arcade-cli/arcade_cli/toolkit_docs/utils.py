import importlib
import inspect
import os
import re
from enum import Enum
from pathlib import Path
from types import ModuleType

from arcade_core.auth import AuthProviderType
from arcade_core.catalog import ToolCatalog
from arcade_core.schema import ToolAuthRequirement, ToolDefinition
from rich.console import Console

from arcade_cli.utils import discover_toolkits


def print_debug_func(debug: bool, console: Console, message: str, style: str = "dim") -> None:
    if not debug:
        return
    console.print(message, style=style)


def standardize_dir_path(dir_path: str) -> str:
    dir_path = dir_path.rstrip("/") + "/"
    return os.path.expanduser(dir_path)


def resolve_api_key(cli_input_value: str | None, env_var_name: str) -> str | None:
    if cli_input_value:
        return cli_input_value
    elif os.getenv(env_var_name):
        return os.getenv(env_var_name)
    else:
        return None


def write_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def read_toolkit_metadata(toolkit_dir: str) -> str:
    pyproject_path = os.path.join(toolkit_dir, "pyproject.toml")
    with open(pyproject_path) as f:
        content = f.read()
        project_section_match = re.search(r"\[project\](.*?)(?=\n\[|$)", content, re.DOTALL)
        if project_section_match:
            project_content = project_section_match.group(1)
            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', project_content)
            if name_match:
                return name_match.group(1).strip()

    raise ValueError(f"Could not find package name in '{pyproject_path}'")


def pascal_to_snake_case(text: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", text).lower()


def get_list_of_tools(toolkit_name: str) -> list[ToolDefinition]:
    tools = []
    toolkits = discover_toolkits()

    for toolkit in toolkits:
        if toolkit.name.casefold() == toolkit_name.casefold():
            for module_name, module_tools in toolkit.tools.items():
                module = importlib.import_module(module_name)
                for tool_name in module_tools:
                    tool_func = getattr(module, tool_name)
                    tool = ToolCatalog.create_tool_definition(
                        tool_func, toolkit.name, toolkit.version, toolkit.description
                    )
                    tools.append(tool)

    if not tools:
        raise ValueError(
            f"Tools not found for the toolkit '{toolkit_name}'. Make sure to have the toolkit "
            "installed in your current Python environment."
        )

    return tools


def get_all_enumerations(toolkit_root_dir: str) -> dict[str, type[Enum]]:
    enums = {}
    toolkit_path = Path(toolkit_root_dir)

    for py_file in toolkit_path.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        if ".venv" in py_file.parts or "venv" in py_file.parts:
            continue

        module_name = py_file.stem
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for name, obj in inspect.getmembers(module):
            if (
                name not in enums
                and inspect.isclass(obj)
                and issubclass(obj, Enum)
                and obj is not Enum
            ):
                enums[name] = obj

    return enums


def get_toolkit_auth_type(requirement: ToolAuthRequirement | None) -> str:
    if requirement is None:
        return ""
    elif requirement.provider_type == AuthProviderType.oauth2.value:
        return 'authType="OAuth2"'
    elif requirement.provider_type:
        return f'authType="{requirement.provider_type}"'
    return ""


def find_enum_by_options(
    enums: dict[str, type[Enum]], options: list[str]
) -> tuple[str, type[Enum]]:
    options_set = set(options)
    for enum_name, enum_class in enums.items():
        enum_member_values = [member.value for member in enum_class]
        if set(enum_member_values) == options_set:
            return enum_name, enum_class
    raise ValueError(f"No enum found for options: {options_set}")


def is_well_known_provider(
    provider_id: str | None,
    auth_module: ModuleType,
) -> bool:
    if provider_id is None:
        return False

    for _, obj in inspect.getmembers(auth_module, inspect.isclass):
        if not issubclass(obj, auth_module.OAuth2) or obj is auth_module.OAuth2:
            continue
        try:
            instance = obj()
        except AttributeError:
            continue
        provider_id_matches = (
            hasattr(instance, "provider_id") and instance.provider_id == provider_id
        )
        if provider_id_matches:
            return True

    return False


def clean_fully_qualified_name(fully_qualified_name: str) -> str:
    return fully_qualified_name.split("@")[0]
