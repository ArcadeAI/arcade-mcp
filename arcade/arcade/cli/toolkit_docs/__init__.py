import json
import os
import re
from functools import partial

import httpx
from arcadepy import Arcade
from rich.console import Console

from arcade.cli.toolkit_docs.templates import (
    TABBED_EXAMPLES_LIST,
    TABLE_OF_CONTENTS,
    TABLE_OF_CONTENTS_ITEM,
    TOOL_CALL_EXAMPLE_JS,
    TOOL_CALL_EXAMPLE_PY,
    TOOL_PARAMETER,
    TOOL_SPEC,
    TOOLKIT_FOOTER,
    TOOLKIT_HEADER,
    TOOLKIT_PAGE,
)
from arcade.core.schema import ToolAuthRequirement, ToolDefinition, ToolInput


def print_debug_func(debug: bool, console: Console, message: str, style: str = "dim"):
    if not debug:
        return
    console.print(message, style=style)


def generate_toolkit_docs(
    console: Console,
    toolkit_name: str,
    docs_section: str,
    docs_root_dir: str,
    engine_base_url: str | httpx.URL,
    arcade_api_key: str | None = None,
    debug: bool = False,
):
    print_debug = partial(print_debug_func, debug=debug, console=console)
    docs_root_dir = os.path.expanduser(docs_root_dir)

    print_debug(f"Getting list of tools for {toolkit_name} from {engine_base_url}")
    client = Arcade(base_url=engine_base_url, api_key=arcade_api_key)
    tools = client.tools.list(include_format=["arcade"], toolkit=toolkit_name)

    print_debug(f"Found {len(tools)} tools")

    print_debug(f"Building {toolkit_name.lower()}.mdx file")
    toolkit_mdx = build_toolkit_mdx(tools)
    toolkit_mdx_path = build_toolkit_mdx_path(docs_section, docs_root_dir, toolkit_name)
    write_file(toolkit_mdx_path, toolkit_mdx)

    print_debug("Building tool-call examples in Python and JavaScript")
    examples = build_examples(tools)

    for filename, example in examples:
        example_path = build_example_path(filename, docs_root_dir, toolkit_name)
        write_file(example_path, example)

    print_debug(f"Done generating docs for {toolkit_name}")


def write_file(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def build_toolkit_mdx_path(docs_section: str, docs_root_dir: str, toolkit_name: str) -> str:
    return os.path.join(
        docs_root_dir,
        "pages",
        "toolkits",
        docs_section,
        f"{toolkit_name.lower()}.mdx",
    )


def build_example_path(example_filename: str, docs_root_dir: str, toolkit_name: str) -> str:
    return os.path.join(
        docs_root_dir,
        "public",
        "examples",
        "integrations",
        "toolkits",
        toolkit_name.lower(),
        example_filename,
    )


def get_toolkit_auth_type(requirement: ToolAuthRequirement) -> str:
    if requirement.provider_type == "oauth2":
        return 'authType="OAuth2"'
    elif requirement.provider_type:
        return f'authType="{requirement.provider_type}"'
    return ""


def build_toolkit_mdx(tools: list[ToolDefinition]) -> str:
    sample_tool = tools[0]
    toolkit_name = sample_tool.toolkit.name
    toolkit_version = sample_tool.toolkit.version
    auth_type = get_toolkit_auth_type(sample_tool.requirements.authorization)

    header = TOOLKIT_HEADER.format(
        toolkit_title=toolkit_name,
        description=sample_tool.toolkit.description,
        package_name=toolkit_name.lower(),
        auth_type=auth_type,
        version=toolkit_version,
    )
    table_of_contents = build_table_of_contents(tools)
    footer = TOOLKIT_FOOTER.format(toolkit_name=toolkit_name.lower())
    tools_specs = build_tools_specs(tools)

    return TOOLKIT_PAGE.format(
        header=header,
        table_of_contents=table_of_contents,
        tools_specs=tools_specs,
        footer=footer,
    )


def build_table_of_contents(tools: list[ToolDefinition]) -> str:
    tools_items = ""

    for tool in tools:
        tools_items += TABLE_OF_CONTENTS_ITEM.format(
            tool_name=tool.name,
            description=tool.description.split("\n")[0],
        )

    return TABLE_OF_CONTENTS.format(tool_items=tools_items)


def build_tools_specs(tools: list[ToolDefinition]) -> str:
    tools_specs = ""

    for tool in tools:
        tools_specs += build_tool_spec(tool)

    return tools_specs


def build_tool_spec(tool: ToolDefinition) -> str:
    tabbed_examples_list = TABBED_EXAMPLES_LIST.format(
        toolkit_name=tool.toolkit.name.lower(),
        tool_name=pascal_to_snake_case(tool.name),
    )
    return TOOL_SPEC.format(
        tool_name=tool.name,
        tabbed_examples_list=tabbed_examples_list,
        description=tool.description,
        parameters=build_tool_parameters(tool.input),
    )


def build_tool_parameters(tool_input: ToolInput) -> str:
    parameters = ""
    for parameter in tool_input.parameters:
        param_definition = parameter.value_schema.val_type
        if parameter.required:
            param_definition += ", required"
        parameters += TOOL_PARAMETER.format(
            param_name=parameter.name,
            definition=param_definition,
            description=parameter.description,
        )
    return parameters


def build_examples(tools: list[ToolDefinition]) -> list[tuple[str, str]]:
    examples = []
    for tool in tools:
        examples.append(pascal_to_snake_case(tool.name), build_python_example(tool))
        examples.append(pascal_to_snake_case(tool.name), build_javascript_example(tool))
    return examples


def build_python_example(tool: ToolDefinition) -> str:
    return TOOL_CALL_EXAMPLE_PY.format(
        tool_name_fully_qualified=tool.fully_qualified_name,
        input_map=json.dumps(build_tool_input_map(tool.input), indent=4),
    )


def build_javascript_example(tool: ToolDefinition) -> str:
    return TOOL_CALL_EXAMPLE_JS.format(
        tool_name_fully_qualified=tool.fully_qualified_name,
        input_map=json.dumps(build_tool_input_map(tool.input), indent=2),
    )


def build_tool_input_map(tool_input: ToolInput) -> dict:
    return {}


def pascal_to_snake_case(text: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", text).lower()
