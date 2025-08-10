import json
import os
import pprint
from enum import Enum
from typing import Any, Callable, cast

import openai
from arcade_core import auth as auth_module
from arcade_core.schema import (
    ToolAuthRequirement,
    ToolDefinition,
    ToolInput,
    ToolSecretRequirement,
)
from rich.console import Console

from arcade_cli.toolkit_docs.templates import (
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
from arcade_cli.toolkit_docs.utils import (
    clean_fully_qualified_name,
    find_enum_by_options,
    get_toolkit_auth_type,
    is_well_known_provider,
    pascal_to_snake_case,
)

console = Console()


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


def build_toolkit_mdx(
    tools: list[ToolDefinition],
    docs_section: str,
    enums: dict[str, type[Enum]],
    pip_package_name: str,
    openai_model: str,
    toolkit_header_template: str = TOOLKIT_HEADER,
    toolkit_page_template: str = TOOLKIT_PAGE,
) -> tuple[str, str]:
    sample_tool = tools[0]
    toolkit_name = sample_tool.toolkit.name
    toolkit_version = sample_tool.toolkit.version
    auth_type = get_toolkit_auth_type(sample_tool.requirements.authorization)

    header = toolkit_header_template.format(
        toolkit_title=toolkit_name,
        description=generate_toolkit_description(
            toolkit_name,
            [(tool.name, tool.description) for tool in tools],
            openai_model,
        ),
        pip_package_name=pip_package_name,
        auth_type=auth_type,
        version=toolkit_version,
    )
    table_of_contents = build_table_of_contents(tools)
    footer = build_footer(toolkit_name, pip_package_name, sample_tool.requirements.authorization)

    referenced_enums, tools_specs = build_tools_specs(tools, docs_section, enums)
    reference_mdx = build_reference_mdx(toolkit_name, referenced_enums) if referenced_enums else ""

    toolkit_mdx = toolkit_page_template.format(
        header=header,
        table_of_contents=table_of_contents,
        tools_specs=tools_specs,
        reference_mdx=reference_mdx,
        footer=footer,
    )

    return toolkit_mdx.strip()


def build_reference_mdx(
    toolkit_name: str,
    referenced_enums: list[tuple[str, type[Enum]]],
    enum_item_template: str = ENUM_ITEM,
    enum_value_template: str = ENUM_VALUE,
    enum_mdx_template: str = ENUM_MDX,
) -> str:
    enum_items = ""
    enum_names_seen = set()

    for enum_name, enum_class in referenced_enums:
        if enum_name in enum_names_seen:
            continue
        enum_names_seen.add(enum_name)
        enum_items += enum_item_template.format(
            enum_name=enum_name,
            enum_values=build_enum_values(
                enum_class=enum_class,
                enum_value_template=enum_value_template,
            ),
        )

    return enum_mdx_template.format(
        toolkit_name=toolkit_name,
        enum_items=enum_items,
    )


def build_enum_values(
    enum_class: type[Enum],
    enum_value_template: str = ENUM_VALUE,
) -> str:
    enum_values = ""
    for enum_member in enum_class:
        enum_values += (
            enum_value_template.format(
                enum_option_name=enum_member.name,
                enum_option_value=enum_member.value,
            )
            + "\n"
        )
    return enum_values


def build_table_of_contents(
    tools: list[ToolDefinition],
    table_of_contents_item_template: str = TABLE_OF_CONTENTS_ITEM,
    table_of_contents_template: str = TABLE_OF_CONTENTS,
) -> str:
    tools_items = ""

    for tool in tools:
        tools_items += table_of_contents_item_template.format(
            tool_fully_qualified_name=clean_fully_qualified_name(tool.fully_qualified_name),
            description=tool.description.split("\n")[0],
        )

    return table_of_contents_template.format(tool_items=tools_items)


def build_footer(
    toolkit_name: str,
    pip_package_name: str,
    authorization: ToolAuthRequirement | None,
    footer_template: str = TOOLKIT_FOOTER,
    oauth2_footer_template: str = TOOLKIT_FOOTER_OAUTH2,
    well_known_provider_config_template: str = WELL_KNOWN_PROVIDER_CONFIG,
    generic_provider_config_template: str = GENERIC_PROVIDER_CONFIG,
) -> str:
    if authorization and authorization.provider_type == "oauth2" and authorization.provider_id:
        is_well_known = is_well_known_provider(
            provider_id=authorization.provider_id,
            auth_module=auth_module,
        )
        config_template = (
            well_known_provider_config_template
            if is_well_known
            else generic_provider_config_template
        )
        provider_configuration = config_template.format(
            toolkit_name=toolkit_name,
            provider_id=authorization.provider_id,
            provider_name=authorization.provider_id.capitalize(),
        )

        return oauth2_footer_template.format(
            pip_package_name=pip_package_name,
            provider_configuration=provider_configuration,
        )
    return footer_template.format(toolkit_name=toolkit_name, pip_package_name=pip_package_name)


def build_tools_specs(
    tools: list[ToolDefinition],
    docs_section: str,
    enums: dict[str, type[Enum]],
    tool_spec_template: str = TOOL_SPEC,
    tool_parameter_template: str = TOOL_PARAMETER,
    tool_spec_secrets_template: str = TOOL_SPEC_SECRETS,
) -> tuple[list[tuple[str, type[Enum]]], str]:
    tools_specs = ""
    referenced_enums = []
    for tool in tools:
        tool_referenced_enums, tool_spec = build_tool_spec(
            tool=tool,
            docs_section=docs_section,
            enums=enums,
            tool_spec_template=tool_spec_template,
            tool_parameter_template=tool_parameter_template,
            tool_spec_secrets_template=tool_spec_secrets_template,
        )
        tools_specs += tool_spec
        referenced_enums.extend(tool_referenced_enums)

    return referenced_enums, tools_specs


def build_tool_spec(
    tool: ToolDefinition,
    docs_section: str,
    enums: dict[str, type[Enum]],
    tool_spec_template: str = TOOL_SPEC,
    tool_parameter_template: str = TOOL_PARAMETER,
    tool_spec_secrets_template: str = TOOL_SPEC_SECRETS,
) -> tuple[list[tuple[str, type[Enum]]], str]:
    tabbed_examples_list = TABBED_EXAMPLES_LIST.format(
        toolkit_name=tool.toolkit.name.lower(),
        tool_name=pascal_to_snake_case(tool.name),
    )
    referenced_enums, parameters = build_tool_parameters(
        tool_input=tool.input,
        docs_section=docs_section,
        toolkit_name=tool.toolkit.name.lower(),
        enums=enums,
        tool_parameter_template=tool_parameter_template,
    )

    if not parameters:
        parameters = "This tool does not take any parameters."

    secrets = (
        build_tool_secrets(
            secrets=tool.requirements.secrets,
            template=tool_spec_secrets_template,
        )
        if tool.requirements.secrets
        else ""
    )

    return referenced_enums, tool_spec_template.format(
        tool_fully_qualified_name=clean_fully_qualified_name(tool.fully_qualified_name),
        tabbed_examples_list=tabbed_examples_list,
        description=tool.description.split("\n")[0],
        parameters=parameters,
        secrets=secrets,
    )


def build_tool_secrets(
    secrets: list[ToolSecretRequirement],
    template: str = TOOL_SPEC_SECRETS,
) -> str:
    if not secrets:
        return ""
    secret_keys_str = "`, `".join([secret.key for secret in secrets])
    return template.format(secrets=f"`{secret_keys_str}`")


def build_tool_parameters(
    tool_input: ToolInput,
    docs_section: str,
    toolkit_name: str,
    enums: dict[str, type[Enum]],
    tool_parameter_template: str = TOOL_PARAMETER,
) -> tuple[list[tuple[str, type[Enum]]], str]:
    referenced_enums = []
    parameters = ""
    for parameter in tool_input.parameters:
        schema = parameter.value_schema
        if schema.enum:
            enum_name, enum_class = find_enum_by_options(enums, schema.enum)
            referenced_enums.append((enum_name, enum_class))
            param_definition = f"`Enum` [{enum_name}](/toolkits/{docs_section}/{toolkit_name}/reference#{enum_name})"
        else:
            if schema.inner_val_type:
                param_definition = f"`{schema.val_type}[{schema.inner_val_type}]`"
            else:
                param_definition = f"`{schema.val_type}`"

        if parameter.required:
            param_definition += ", required"
        else:
            param_definition += ", optional"

        parameters += (
            tool_parameter_template.format(
                param_name=parameter.name,
                definition=param_definition,
                description=parameter.description,
            )
            + "\n"
        )

    return referenced_enums, parameters


def build_examples(
    print_debug: Callable,
    tools: list[ToolDefinition],
    openai_model: str,
) -> list[tuple[str, str]]:
    examples = []
    for tool in tools:
        print_debug(f"Generating tool-call examples for {tool.name}")
        interface_signature = build_tool_interface_signature(tool)
        input_map = generate_tool_input_map(interface_signature, openai_model)
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


def build_python_example(
    tool_fully_qualified_name: str,
    input_map: dict[str, Any],
    template: str = TOOL_CALL_EXAMPLE_PY,
) -> str:
    input_map_str = pprint.pformat(
        input_map,
        indent=4,
        width=100,
        compact=False,
        sort_dicts=False,
    )
    input_map_str = "{\n    " + input_map_str.lstrip("{   ").rstrip("}") + "\n}"  # noqa: B005
    return template.format(
        tool_fully_qualified_name=tool_fully_qualified_name,
        input_map=input_map_str,
    )


def build_javascript_example(
    tool_fully_qualified_name: str,
    input_map: dict,
    template: str = TOOL_CALL_EXAMPLE_JS,
) -> str:
    return template.format(
        tool_fully_qualified_name=tool_fully_qualified_name,
        input_map=json.dumps(input_map, indent=2, ensure_ascii=False),
    )


def generate_toolkit_description(
    toolkit_name: str,
    tools: list[tuple[str, str]],
    openai_model: str,
) -> str:
    messages = [
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
    ]

    return request_openai_generation(model=openai_model, max_tokens=512, messages=messages)


def generate_tool_input_map(
    interface_signature: dict[str, Any],
    openai_model: str,
    retries: int = 0,
    max_retries: int = 3,
) -> dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant expert in generating data for documenting "
                "sample scripts to calling tools. A tool is a function that is used in "
                "context of LLM tool-calling / function-calling.\n\n"
                "When given a tool signature with typed arguments, "
                "you must return exactly one JSON object (no markdown, no extra text) "
                "where each key is an argument name, and each value is a sample value "
                "for that argument that would make sense in a sample script to showcase "
                "human software engineers how the tool may be called. Generate the "
                "argument sample value based on its name and description\n\n"
                "Not every single argument must always be present in the input map. "
                "In some cases, the tool may require only one of two arguments to be "
                "provided, for example. In such cases, an indication will be present "
                "either/or in the tool description or the argument description. "
                "Always follow such instructions when present in the tool interface.\n\n"
                "Keep argument values as short as possible. Values don't have to always "
                "be valid. For instance, for file content base64-encoded arguments, "
                "you can use a short text or a placeholder like `[file_content]`, it is "
                "not necessary that the value is a valid base64-encoded string.\n\n"
                "Remember that you MUST RESPOND ONLY WITH A VALID JSON STRING, NO ADDED "
                "TEXT. Your response will be json.load'ed, so it must be a valid JSON "
                "string."
            ),
        },
        {
            "role": "user",
            "content": (
                "Here is a tool interface:\n\n"
                f"{json.dumps(interface_signature, ensure_ascii=False)}\n\n"
                "Please provide a sample input map as a JSON object."
            ),
        },
    ]

    text = request_openai_generation(model=openai_model, max_tokens=512, messages=messages)

    try:
        return cast(dict[str, Any], json.loads(text))
    except (json.JSONDecodeError, TypeError):
        if retries < max_retries:
            return generate_tool_input_map(
                interface_signature=interface_signature,
                openai_model=openai_model,
                retries=retries + 1,
                max_retries=max_retries,
            )
        tool_name = interface_signature["tool_name"]
        console.print(
            f"Attention: {openai_model} failed to generate a valid inputs JSON for the tool '{tool_name}'. "
            "Please check the Python & Javascript example scripts generated and enter a sample input manually.",
            style="red",
        )
        return {}


def build_tool_interface_signature(tool: ToolDefinition) -> dict[str, Any]:
    args = []
    for arg in tool.input.parameters:
        data: dict[str, Any] = {
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

    return {
        "tool_name": tool.name,
        "tool_description": tool.description,
        "tool_args": args,
    }


def request_openai_generation(
    model: str,
    max_tokens: int,
    messages: list[dict[str, Any]],
) -> str:
    if model.startswith("gpt-5"):
        response = openai.responses.create(
            model=model,
            input=messages,
            max_output_tokens=max_tokens,
            reasoning={
                "effort": "minimal",
            },
            text={
                "verbosity": "low",
            },
        )
        response_str = cast(str, response.output_text)

    elif model.startswith("gpt-4o"):
        response = openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,
            max_completion_tokens=max_tokens,
            stop=["\n\n"],
        )
        response_str = cast(str, response.choices[0].message.content)

    else:
        raise ValueError(
            f"Unsupported OpenAI model: {model}. Choose a model from the 'gpt-4o' or 'gpt-5' series."
        )

    return response_str.strip()
