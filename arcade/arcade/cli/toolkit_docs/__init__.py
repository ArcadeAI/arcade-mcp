import json
import os
import re
from functools import partial
from typing import Callable

import httpx
import openai
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
    openai_api_key: str | None = None,
    debug: bool = False,
):
    openai.api_key = resolve_api_key(console, "openai-api-key", openai_api_key, "OPENAI_API_KEY")
    arcade_api_key = resolve_api_key(console, "arcade-api-key", arcade_api_key, "ARCADE_API_KEY")

    print_debug = partial(print_debug_func, debug, console)
    docs_root_dir = os.path.expanduser(docs_root_dir)

    print_debug(f"Getting list of tools for {toolkit_name} from {engine_base_url}")

    client = Arcade(base_url=engine_base_url, api_key=arcade_api_key)
    tools = get_list_of_tools(client, toolkit_name)

    print_debug(f"Found {len(tools)} tools")

    print_debug(f"Building {toolkit_name.lower()}.mdx file")
    toolkit_mdx = build_toolkit_mdx(tools, docs_section)
    toolkit_mdx_path = build_toolkit_mdx_path(docs_section, docs_root_dir, toolkit_name)
    write_file(toolkit_mdx_path, toolkit_mdx)

    print_debug("Building tool-call examples in Python and JavaScript")
    examples = build_examples(print_debug, tools)

    for filename, example in examples:
        example_path = build_example_path(filename, docs_root_dir, toolkit_name)
        write_file(example_path, example)

    print_debug(f"Done generating docs for {toolkit_name}")


def get_list_of_tools(client: Arcade, toolkit_name: str) -> list[ToolDefinition]:
    tools = []
    offset = 0
    keep_paginating = True

    while keep_paginating:
        response = client.tools.list(
            include_format=["arcade"],
            toolkit=toolkit_name,
            limit=100,
            offset=offset,
        )
        tools.extend(response.items)
        next_page_info = response.next_page_info()
        if next_page_info is None:
            keep_paginating = False
        else:
            offset = next_page_info.offset

    return tools


def resolve_api_key(
    console: Console, cli_arg_name: str, cli_input_value: str | None, env_var_name: str
) -> str:
    if cli_input_value:
        return cli_input_value
    elif os.getenv(env_var_name):
        return os.getenv(env_var_name)
    else:
        console.print(
            f"❌ Provide --{cli_arg_name} argument or set the {env_var_name} environment variable",
            style="red",
        )


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


def build_toolkit_mdx(tools: list[ToolDefinition], docs_section: str) -> str:
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
    tools_specs = build_tools_specs(tools, docs_section)

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


def build_tools_specs(tools: list[ToolDefinition], docs_section: str) -> str:
    tools_specs = ""

    for tool in tools:
        tools_specs += build_tool_spec(tool, docs_section)

    return tools_specs


def build_tool_spec(tool: ToolDefinition, docs_section: str) -> str:
    tabbed_examples_list = TABBED_EXAMPLES_LIST.format(
        toolkit_name=tool.toolkit.name.lower(),
        tool_name=pascal_to_snake_case(tool.name),
    )
    return TOOL_SPEC.format(
        tool_name=tool.name,
        tabbed_examples_list=tabbed_examples_list,
        description=tool.description,
        parameters=build_tool_parameters(tool.input, docs_section, tool.toolkit.name.lower()),
    )


def build_tool_parameters(tool_input: ToolInput, docs_section: str, toolkit_name: str) -> str:
    parameters = ""
    for parameter in tool_input.parameters:
        if parameter.value_schema.enum:
            param_definition = f"Enum [EnumName](/toolkits/{docs_section}/{toolkit_name}#EnumName)"
        else:
            param_definition = parameter.value_schema.val_type

        if parameter.required:
            param_definition += ", required"
        else:
            param_definition += ", optional"

        parameters += TOOL_PARAMETER.format(
            param_name=parameter.name,
            definition=param_definition,
            description=parameter.description,
        )
    return parameters


def build_examples(print_debug: Callable, tools: list[ToolDefinition]) -> list[tuple[str, str]]:
    examples = []
    for tool in tools:
        print_debug(f"Generating tool-call examples for {tool.name}")
        input_map = generate_tool_input_map(tool)
        examples.append((
            f"{pascal_to_snake_case(tool.name)}_example_call_tool.py",
            build_python_example(tool.fully_qualified_name, input_map),
        ))
        examples.append((
            f"{pascal_to_snake_case(tool.name)}_example_call_tool.js",
            build_javascript_example(tool.fully_qualified_name, input_map),
        ))
    return examples


def build_python_example(tool_fully_qualified_name: str, input_map: dict) -> str:
    input_map = json.dumps(input_map, indent=4, ensure_ascii=False)
    input_map = input_map.replace(": false", ": False").replace(": true", ": True")
    return TOOL_CALL_EXAMPLE_PY.format(
        tool_name_fully_qualified=tool_fully_qualified_name,
        input_map=input_map,
    )


def build_javascript_example(tool_fully_qualified_name: str, input_map: dict) -> str:
    return TOOL_CALL_EXAMPLE_JS.format(
        tool_name_fully_qualified=tool_fully_qualified_name,
        input_map=json.dumps(input_map, indent=2, ensure_ascii=False),
    )


def pascal_to_snake_case(text: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", text).lower()


def generate_tool_input_map(tool: ToolDefinition, retries: int = 0, max_retries: int = 3) -> dict:
    interface_description = build_tool_interface_description(tool)
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. "
                    "When given a function signature with typed arguments, "
                    "you must return exactly one JSON object (no markdown, no extra text) "
                    "where each key is an argument name, and each value is a logically valid "
                    "sample value for that argument, based on its name and description.\n\n"
                    "This will be used to generate example scripts in a documentation "
                    "that shows how to call the tool.\n\n"
                    "Not every single argument must always be present in the input map. "
                    "In some cases, the tool may require only one of two arguments to be "
                    "provided, for example. In such cases, an indication will be present "
                    "either/or in the tool description or the argument description. "
                    "Always follow such instructions when present in the tool interface.\n\n"
                    "Remember that you MUST RESPOND ONLY WITH A VALID JSON STRING, NO ADDED "
                    "TEXT. Your response will be `json.dumps`'d, so it must be a valid JSON "
                    "string."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Here is a tool interface:\n\n"
                    f"{interface_description}\n\n"
                    "Please provide a sample input map as a JSON object."
                ),
            },
        ],
        temperature=0.0,
        max_tokens=1024,
        stop=["\n\n"],
    )

    text = response.choices[0].message.content.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if retries < max_retries:
            return generate_tool_input_map(tool, retries + 1, max_retries)
        raise ValueError(f"Failed to generate input map for tool {tool.name}: {text}")


def build_tool_interface_description(tool: ToolDefinition) -> str:
    args = []
    for arg in tool.input.parameters:
        data = {
            "arg_name": arg.name,
            "arg_description": arg.description,
            "is_arg_required": arg.required,
            "arg_type": arg.value_schema.val_type,
        }

        if arg.value_schema.enum:
            data["enum"] = {
                "accepted_values": arg.value_schema.enum,
            }

        args.append(data)

    return json.dumps({
        "tool_name": tool.name,
        "tool_description": tool.description,
        "tool_args": args,
    })
