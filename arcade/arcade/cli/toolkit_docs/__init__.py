import importlib
import inspect
import json
import os
import re
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Callable

import httpx
import openai
from arcadepy import Arcade
from rich.console import Console

from arcade.cli.toolkit_docs.templates import (
    ENUM_ITEM,
    ENUM_MDX,
    ENUM_VALUE,
    GENERIC_PROVIDER_CONFIG,
    TABBED_EXAMPLES_LIST,
    TABLE_OF_CONTENTS,
    TABLE_OF_CONTENTS_ITEM,
    TOOL_CALL_EXAMPLE_JS,
    TOOL_CALL_EXAMPLE_PY,
    TOOL_PARAMETER,
    TOOL_SPEC,
    TOOL_SPEC_SECRETS,
    TOOLKIT_FOOTER,
    TOOLKIT_FOOTER_OAUTH2,
    TOOLKIT_HEADER,
    TOOLKIT_PAGE,
    WELL_KNOWN_PROVIDER_CONFIG,
)
from arcade.core.schema import ToolAuthRequirement, ToolDefinition, ToolInput, ToolSecretRequirement


def print_debug_func(debug: bool, console: Console, message: str, style: str = "dim"):
    if not debug:
        return
    console.print(message, style=style)


def generate_toolkit_docs(
    console: Console,
    toolkit_name: str,
    toolkit_dir: str,
    docs_section: str,
    docs_dir: str,
    engine_base_url: str | httpx.URL,
    arcade_api_key: str | None = None,
    openai_api_key: str | None = None,
    tool_call_examples: bool = True,
    debug: bool = False,
):
    openai.api_key = resolve_api_key(console, "openai-api-key", openai_api_key, "OPENAI_API_KEY")
    arcade_api_key = resolve_api_key(console, "arcade-api-key", arcade_api_key, "ARCADE_API_KEY")

    print_debug = partial(print_debug_func, debug, console)

    docs_dir = os.path.expanduser(docs_dir)
    toolkit_dir = os.path.expanduser(toolkit_dir)

    print_debug("Reading toolkit metadata")
    pip_package_name = read_toolkit_metadata(toolkit_dir)

    print_debug(f"Getting list of tools for {toolkit_name} from {engine_base_url}")

    client = Arcade(base_url=engine_base_url, api_key=arcade_api_key)
    tools = get_list_of_tools(client, toolkit_name)

    print_debug(f"Found {len(tools)} tools")

    print_debug("Getting all enumerations potentially used in tool argument specs")
    enums = get_all_enumerations(toolkit_dir)

    print_debug(f"Building /{toolkit_name.lower()}.mdx file")
    reference_mdx, toolkit_mdx = build_toolkit_mdx(tools, docs_section, enums, pip_package_name)
    toolkit_mdx_path = build_toolkit_mdx_path(docs_section, docs_dir, toolkit_name)
    write_file(toolkit_mdx_path, toolkit_mdx)

    if reference_mdx:
        print_debug(f"Building /{toolkit_name.lower()}/reference.mdx file")
        reference_mdx_path = build_reference_mdx_path(docs_section, docs_dir, toolkit_name)
        write_file(reference_mdx_path, reference_mdx)
    else:
        print_debug("No Enums referenced by tool interfaces. Skipping reference.mdx file")

    if tool_call_examples:
        print_debug("Building tool-call examples in Python and JavaScript")
        examples = build_examples(print_debug, tools)

        for filename, example in examples:
            example_path = build_example_path(filename, docs_dir, toolkit_name)
            write_file(example_path, example)

    print_debug(f"Done generating docs for {toolkit_name}")


def read_toolkit_metadata(toolkit_dir: str) -> str:
    pyproject_path = os.path.join(toolkit_dir, "pyproject.toml")
    with open(pyproject_path) as f:
        content = f.read()
        pkg_name = re.search(
            r'\[tool\.poetry\].*?name\s*=\s*["\']([^"\']+)["\']', content, re.DOTALL
        )
        if pkg_name:
            return pkg_name.group(1)

    raise ValueError(f"Could not find package name in '{pyproject_path}'")


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


def get_all_enumerations(toolkit_root_dir: str) -> dict[str, Enum]:
    enums = {}
    toolkit_path = Path(toolkit_root_dir)

    for py_file in toolkit_path.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        module_name = py_file.stem
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, Enum) and obj is not Enum:
                enums[name] = obj

    return enums


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


def build_reference_mdx_path(docs_section: str, docs_root_dir: str, toolkit_name: str) -> str:
    return os.path.join(
        docs_root_dir,
        "pages",
        "toolkits",
        docs_section,
        toolkit_name.lower(),
        "reference.mdx",
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


def build_toolkit_mdx(
    tools: list[ToolDefinition],
    docs_section: str,
    enums: dict[str, Enum],
    pip_package_name: str,
) -> tuple[str, str]:
    sample_tool = tools[0]
    toolkit_name = sample_tool.toolkit.name
    toolkit_version = sample_tool.toolkit.version
    auth_type = get_toolkit_auth_type(sample_tool.requirements.authorization)

    header = TOOLKIT_HEADER.format(
        toolkit_title=toolkit_name,
        description=generate_toolkit_description(
            toolkit_name,
            [(tool.name, tool.description) for tool in tools],
        ),
        pip_package_name=pip_package_name,
        auth_type=auth_type,
        version=toolkit_version,
    )
    table_of_contents = build_table_of_contents(tools)
    footer = build_footer(toolkit_name, pip_package_name, sample_tool.requirements.authorization)
    referenced_enums, tools_specs = build_tools_specs(tools, docs_section, enums)
    reference_mdx = build_reference_mdx(toolkit_name, referenced_enums) if referenced_enums else ""

    return reference_mdx, TOOLKIT_PAGE.format(
        header=header,
        table_of_contents=table_of_contents,
        tools_specs=tools_specs,
        footer=footer,
    )


def build_reference_mdx(toolkit_name: str, referenced_enums: list[tuple[str, Enum]]) -> str:
    enum_items = ""

    for enum_name, enum_class in referenced_enums:
        enum_items += ENUM_ITEM.format(
            enum_name=enum_name,
            enum_values=build_enum_values(enum_class),
        )

    return ENUM_MDX.format(
        toolkit_name=toolkit_name,
        enum_items=enum_items,
    )


def build_enum_values(enum_class: Enum) -> str:
    enum_values = ""
    for enum_member in enum_class:
        enum_values += (
            ENUM_VALUE.format(
                enum_option_name=enum_member.name,
                enum_option_value=enum_member.value,
            )
            + "\n"
        )
    return enum_values


def build_table_of_contents(tools: list[ToolDefinition]) -> str:
    tools_items = ""

    for tool in tools:
        tools_items += TABLE_OF_CONTENTS_ITEM.format(
            tool_name=tool.name,
            description=tool.description.split("\n")[0],
        )

    return TABLE_OF_CONTENTS.format(tool_items=tools_items)


def build_footer(
    toolkit_name: str, pip_package_name: str, authorization: ToolAuthRequirement
) -> str:
    if authorization.provider_type == "oauth2":
        is_well_known = is_well_known_provider(authorization.provider_id)
        config_template = WELL_KNOWN_PROVIDER_CONFIG if is_well_known else GENERIC_PROVIDER_CONFIG
        provider_configuration = config_template.format(
            toolkit_name=toolkit_name,
            provider_id=authorization.provider_id,
            provider_name=authorization.provider_id.capitalize(),
            pip_package_name=pip_package_name,
        )

        return TOOLKIT_FOOTER_OAUTH2.format(
            toolkit_name=toolkit_name,
            toolkit_name_lower=toolkit_name.lower(),
            provider_configuration=provider_configuration,
        )
    return TOOLKIT_FOOTER.format(toolkit_name=toolkit_name, pip_package_name=pip_package_name)


def build_tools_specs(
    tools: list[ToolDefinition],
    docs_section: str,
    enums: dict[str, Enum],
) -> tuple[list[tuple[str, Enum]], str]:
    tools_specs = ""
    referenced_enums = []
    for tool in tools:
        tool_referenced_enums, tool_spec = build_tool_spec(tool, docs_section, enums)
        tools_specs += tool_spec
        referenced_enums.extend(tool_referenced_enums)

    return referenced_enums, tools_specs


def build_tool_spec(
    tool: ToolDefinition, docs_section: str, enums: dict[str, Enum]
) -> tuple[list[tuple[str, Enum]], str]:
    tabbed_examples_list = TABBED_EXAMPLES_LIST.format(
        toolkit_name=tool.toolkit.name.lower(),
        tool_name=pascal_to_snake_case(tool.name),
    )
    referenced_enums, parameters = build_tool_parameters(
        tool.input,
        docs_section,
        tool.toolkit.name.lower(),
        enums,
    )

    secrets = build_tool_secrets(tool.requirements.secrets)

    return referenced_enums, TOOL_SPEC.format(
        tool_name=tool.name,
        tabbed_examples_list=tabbed_examples_list,
        description=tool.description.split("\n")[0],
        parameters=parameters,
        secrets=secrets,
    )


def build_tool_secrets(secrets: list[ToolSecretRequirement]) -> str:
    if not secrets:
        return ""
    secret_keys_str = "`, `".join([secret.key for secret in secrets])
    return TOOL_SPEC_SECRETS.format(secrets=f"`{secret_keys_str}`")


def build_tool_parameters(
    tool_input: ToolInput,
    docs_section: str,
    toolkit_name: str,
    enums: dict[str, Enum],
) -> tuple[list[tuple[str, Enum]], str]:
    referenced_enums = []
    parameters = ""
    for parameter in tool_input.parameters:
        if parameter.value_schema.enum:
            enum_name, enum_class = find_enum_by_options(enums, parameter.value_schema.enum)
            referenced_enums.append((enum_name, enum_class))
            param_definition = (
                f"Enum [{enum_name}](/toolkits/{docs_section}/{toolkit_name}/reference#{enum_name})"
            )
        else:
            param_definition = parameter.value_schema.val_type

        if parameter.required:
            param_definition += ", required"
        else:
            param_definition += ", optional"

        parameters += (
            TOOL_PARAMETER.format(
                param_name=parameter.name,
                definition=param_definition,
                description=parameter.description,
            )
            + "\n"
        )

    return referenced_enums, parameters


def build_examples(print_debug: Callable, tools: list[ToolDefinition]) -> list[tuple[str, str]]:
    examples = []
    for tool in tools:
        print_debug(f"Generating tool-call examples for {tool.name}")
        input_map = generate_tool_input_map(tool)
        fully_qualified_name = tool.fully_qualified_name.split("@")[0]
        examples.append((
            f"{pascal_to_snake_case(tool.name)}_example_call_tool.py",
            build_python_example(fully_qualified_name, input_map),
        ))
        examples.append((
            f"{pascal_to_snake_case(tool.name)}_example_call_tool.js",
            build_javascript_example(fully_qualified_name, input_map),
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


def generate_toolkit_description(toolkit_name: str, tools: list[tuple[str, str]]) -> str:
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. "
                    "When given a toolkit name and a list of tools, you will generate a "
                    "short, yet descriptive of the toolkit and the main actions a user "
                    "or LLM can perform with it.\n\n"
                    "As an example, here is the Asana toolkit description:\n\n"
                    "The Arcade Asana toolkit provides a pre-built set of tools for "
                    "interacting with Asana. These tools make it easy to build agents "
                    "and AI apps that can:\n\n"
                    "- Manage teams, projects, and workspaces.\n"
                    "- Create, update, and search for tasks.\n"
                    "- Retrieve data about tasks, projects, workspaces, users, etc.\n"
                    "- Manage task attachments.\n\n"
                    "And here is a JSON string with the list of tools in the Asana toolkit:\n\n"
                    "```json\n\n"
                    '[["AttachFileToTask", "Attaches a file to an Asana task\n\nProvide exactly '
                    "one of file_content_str, file_content_base64, or file_content_url, never "
                    "more\nthan one.\n\n- Use file_content_str for text files (will be encoded "
                    "using file_encoding)\n- Use file_content_base64 for binary files like images, "
                    'PDFs, etc.\n- Use file_content_url if the file is hosted on an external URL"], '
                    '["CreateTag", "Create a tag in Asana"], ["CreateTask", "Creates a task in '
                    "Asana\n\nThe task must be associated to at least one of the following: "
                    "parent_task_id, project, or\nworkspace_id. If none of these are provided and "
                    "the account has only one workspace, the task\nwill be associated to that "
                    "workspace. If the account has multiple workspaces, an error will\nbe raised "
                    'with a list of available workspaces."], ["GetProjectById", "Get an Asana '
                    'project by its ID"], ["GetSubtasksFromATask", "Get the subtasks of a task"], '
                    '["GetTagById", "Get an Asana tag by its ID"], ["GetTaskById", "Get a task by '
                    'its ID"], ["GetTasksWithoutId", "Search for tasks"], ["GetTeamById", "Get an '
                    'Asana team by its ID"], ["GetUserById", "Get a user by ID"], ["GetWorkspaceById", '
                    '"Get an Asana workspace by its ID"], ["ListProjects", "List projects in Asana"], '
                    '["ListTags", "List tags in an Asana workspace"], ["ListTeams", "List teams in '
                    'an Asana workspace"], ["ListTeamsTheCurrentUserIsAMemberOf", "List teams in '
                    'Asana that the current user is a member of"], ["ListUsers", "List users in '
                    'Asana"], ["ListWorkspaces", "List workspaces in Asana that are visible to the '
                    'authenticated user"], ["MarkTaskAsCompleted", "Mark a task in Asana as '
                    'completed"], ["UpdateTask", "Updates a task in Asana"]]\n\n```\n\n'
                    "Keep the description concise and to the point. The user will provide you with "
                    "the toolkit name and the list of tools. Generate the description according to "
                    "the instructions above."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"The toolkit name is {toolkit_name} and the list of tools is:\n\n"
                    "```json\n\n"
                    f"{json.dumps(tools, ensure_ascii=False)}\n\n"
                    "```\n\n"
                    "Please generate a description for the toolkit."
                ),
            },
        ],
        temperature=0.0,
        max_tokens=2048,
    )

    return response.choices[0].message.content.strip()


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
                    "Keep argument values as short as possible. Values don't have to always "
                    "be valid. For instance, for file content base64-encoded arguments, "
                    "you can use a short text or a placeholder like `[file_content]`.\n\n"
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


def find_enum_by_options(enums: dict[str, Enum], options: list[str]) -> tuple[str, Enum]:
    for enum_name, enum_class in enums.items():
        enum_member_values = [member.value for member in enum_class]
        if set(enum_member_values) == set(options):
            return enum_name, enum_class
    print("\n\n\nenums", enums)
    print("\n\n\noptions", options, "\n\n\n")
    raise ValueError(f"No enum found for options: {options}")


def is_well_known_provider(provider_id: str) -> bool:
    import inspect

    from arcade.core import auth

    for _, obj in inspect.getmembers(auth, inspect.isclass):
        if not issubclass(obj, auth.OAuth2) or obj is auth.OAuth2:
            continue
        instance = obj()
        provider_id_matches = (
            hasattr(instance, "provider_id") and instance.provider_id == provider_id
        )
        if provider_id_matches:
            return True

    return False
