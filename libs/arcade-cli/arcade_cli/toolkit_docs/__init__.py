from functools import partial

import openai
from rich.console import Console

from arcade_cli.toolkit_docs.docs_builder import (
    build_example_path,
    build_examples,
    build_toolkit_mdx,
    build_toolkit_mdx_path,
)
from arcade_cli.toolkit_docs.utils import (
    get_all_enumerations,
    get_list_of_tools,
    print_debug_func,
    read_toolkit_metadata,
    resolve_api_key,
    standardize_dir_path,
    write_file,
)


def generate_toolkit_docs(
    console: Console,
    toolkit_name: str,
    toolkit_dir: str,
    docs_section: str,
    docs_dir: str,
    openai_model: str,
    openai_api_key: str | None = None,
    tool_call_examples: bool = True,
    debug: bool = False,
) -> bool:
    openai.api_key = resolve_api_key(openai_api_key, "OPENAI_API_KEY")

    if not openai.api_key:
        console.print(
            "❌ Provide --openai-api-key argument or set the OPENAI_API_KEY environment variable",
            style="red",
        )
        return False

    print_debug = partial(print_debug_func, debug, console)

    docs_dir = standardize_dir_path(docs_dir)
    toolkit_dir = standardize_dir_path(toolkit_dir)

    print_debug("Reading toolkit metadata")
    pip_package_name = read_toolkit_metadata(toolkit_dir)

    print_debug(f"Getting list of tools for {toolkit_name} from the local Python environment")
    tools = get_list_of_tools(toolkit_name)

    print_debug(f"Found {len(tools)} tools")

    print_debug("Getting all enumerations potentially used in tool argument specs")
    enums = get_all_enumerations(toolkit_dir)

    print_debug(f"Building /{toolkit_name.lower()}.mdx file")
    toolkit_mdx = build_toolkit_mdx(
        tools=tools,
        docs_section=docs_section,
        enums=enums,
        pip_package_name=pip_package_name,
        openai_model=openai_model,
    )
    toolkit_mdx_path = build_toolkit_mdx_path(docs_section, docs_dir, toolkit_name)
    write_file(toolkit_mdx_path, toolkit_mdx)

    if tool_call_examples:
        print_debug("Building tool-call examples in Python and JavaScript")
        examples = build_examples(print_debug, tools, openai_model)

        for filename, example in examples:
            example_path = build_example_path(filename, docs_dir, toolkit_name)
            write_file(example_path, example)

    print_debug(f"Done generating docs for {toolkit_name}")

    return True
