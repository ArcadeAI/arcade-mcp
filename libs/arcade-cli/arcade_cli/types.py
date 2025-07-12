"""
Type generation commands for the Arcade CLI.
"""

import json
from pathlib import Path
from typing import Any, Optional  # Optional needed for Typer compatibility

import typer
from arcade_core.schema import ToolDefinition, ValueSchema
from rich.console import Console
from rich.syntax import Syntax

from arcade_cli.utils import OrderCommands, create_cli_catalog, get_tools_from_engine

console = Console()

app = typer.Typer(
    cls=OrderCommands,
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=True,
    rich_markup_mode="markdown",
)


@app.command("generate", help="Generate types from tool definitions")
def generate_types(
    toolkit: Optional[str] = typer.Argument(None, help="Toolkit name to generate types for"),
    tool: Optional[str] = typer.Option(None, "--tool", "-t", help="Specific tool name"),
    output: str = typer.Option("./types", "--output", "-o", help="Output directory"),
    lang: str = typer.Option(
        "typescript", "--lang", "-l", help="Target language (typescript, python)"
    ),
    host: Optional[str] = typer.Option(None, "--host", "-h", help="Arcade Engine host"),
    local: bool = typer.Option(False, "--local", help="Use local catalog instead of engine"),
) -> None:
    """Generate type definitions from tool schemas."""

    # Get tools from either local catalog or engine
    if local:
        catalog = create_cli_catalog(toolkit=toolkit)
        tools = [t.definition for t in list(catalog)]
    else:
        # Use engine if host is provided
        if host:
            tools = get_tools_from_engine(host, toolkit=toolkit)
        else:
            # Default to local if no host specified
            catalog = create_cli_catalog(toolkit=toolkit)
            tools = [t.definition for t in list(catalog)]

    # Filter by specific tool if requested
    if tool:
        tools = [t for t in tools if t.name.lower() == tool.lower()]
        if not tools:
            console.print(f"❌ Tool '{tool}' not found", style="bold red")
            return

    # Create output directory
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate types for each tool
    generated_files = []
    for tool_def in tools:
        if lang == "typescript":
            file_path = output_path / f"{tool_def.name.lower()}.d.ts"
            content = _generate_typescript(tool_def)
        elif lang == "python":
            file_path = output_path / f"{tool_def.name.lower()}.py"
            content = _generate_python_stub(tool_def)
        else:
            console.print(f"❌ Unsupported language: {lang}", style="bold red")
            return

        file_path.write_text(content)
        generated_files.append(file_path)

    # Summary
    console.print(f"✅ Generated {len(generated_files)} type files:", style="bold green")
    for file in generated_files:
        console.print(f"  - {file}")


@app.command("show", help="Show tool schema")
def show_schema(
    tool_name: str,
    format_type: str = typer.Option(
        "json", "--format", "-f", help="Output format (json, typescript)"
    ),
    host: Optional[str] = typer.Option(None, "--host", "-h", help="Arcade Engine host"),
    local: bool = typer.Option(False, "--local", help="Use local catalog"),
) -> None:
    """Display the schema for a specific tool."""

    # Get tool definition
    if local or not host:
        catalog = create_cli_catalog()
        tool = catalog.get_tool_by_name(tool_name)
        tool_def = tool.definition
    else:
        tools = get_tools_from_engine(host)
        tool_def = next((t for t in tools if t.name.lower() == tool_name.lower()), None)
        if not tool_def:
            console.print(f"❌ Tool '{tool_name}' not found", style="bold red")
            return

    # Format output
    if format_type == "typescript":
        output = _generate_typescript(tool_def)
        syntax = Syntax(output, "typescript")
    else:
        # Generate JSON Schema
        schema = {
            "input": _value_schema_to_json_schema(tool_def.input),
            "output": _value_schema_to_json_schema(tool_def.output),
        }
        output = json.dumps(schema, indent=2)
        syntax = Syntax(output, "json")

    console.print(syntax)


def _generate_typescript(tool_def: ToolDefinition) -> str:
    """Generate TypeScript interface definitions for a tool."""
    output = f"// Auto-generated types for {tool_def.name}\n\n"

    # Generate input interface
    output += f"export interface {tool_def.name}Input {{\n"
    for param in tool_def.input.parameters:
        ts_type = _value_schema_to_ts_type(param.value_schema)
        optional = "" if param.required else "?"
        comment = f"  // {param.description}" if param.description else ""
        output += f"  {param.name}{optional}: {ts_type};{comment}\n"
    output += "}\n\n"

    # Generate output interface
    output += f"export interface {tool_def.name}Output {{\n"
    if tool_def.output.value_schema:
        output += _generate_ts_output_fields(tool_def.output.value_schema)
    else:
        output += "  // No output schema defined\n"
    output += "}\n"

    return output


def _generate_python_stub(tool_def: ToolDefinition) -> str:
    """Generate Python type stub for a tool."""
    output = f'"""Auto-generated types for {tool_def.name}"""\n'
    output += "from typing import TypedDict, Optional\n\n"

    # Generate input TypedDict
    output += f"class {tool_def.name}Input(TypedDict):\n"
    for param in tool_def.input.parameters:
        py_type = _value_schema_to_py_type(param.value_schema)
        if not param.required:
            py_type = f"Optional[{py_type}]"
        comment = f'    """{param.description}"""' if param.description else ""
        if comment:
            output += f"{comment}\n"
        output += f"    {param.name}: {py_type}\n"
    output += "\n"

    # Generate output TypedDict
    output += f"class {tool_def.name}Output(TypedDict):\n"
    if tool_def.output.value_schema:
        output += "    result: " + _value_schema_to_py_type(tool_def.output.value_schema)
    else:
        output += "    pass  # No output schema defined"
    output += "\n"

    return output


def _value_schema_to_ts_type(schema: ValueSchema) -> str:
    """Convert ValueSchema to TypeScript type."""
    if schema.enum:
        return " | ".join(f'"{val}"' for val in schema.enum)

    mapping = {
        "string": "string",
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "json": "Record<string, any>",
        "array": "any[]",
    }

    if schema.val_type == "array" and schema.inner_val_type:
        inner = mapping.get(schema.inner_val_type, "any")
        return f"{inner}[]"

    return mapping.get(schema.val_type, "any")


def _value_schema_to_py_type(schema: ValueSchema) -> str:
    """Convert ValueSchema to Python type."""
    if schema.enum:
        return "Literal[" + ", ".join(f'"{val}"' for val in schema.enum) + "]"

    mapping = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "json": "dict[str, Any]",
        "array": "list[Any]",
    }

    if schema.val_type == "array" and schema.inner_val_type:
        inner = mapping.get(schema.inner_val_type, "Any")
        return f"list[{inner}]"

    return mapping.get(schema.val_type, "Any")


def _generate_ts_output_fields(schema: ValueSchema) -> str:
    """Generate TypeScript fields for output schema."""
    if schema.val_type == "json":
        return "  [key: string]: any;\n"
    elif schema.val_type == "array":
        inner_type = _value_schema_to_ts_type(schema)
        return f"  result: {inner_type};\n"
    else:
        ts_type = _value_schema_to_ts_type(schema)
        return f"  result: {ts_type};\n"


def _value_schema_to_json_schema(schema: Any) -> dict[str, Any]:
    """Convert ValueSchema or ToolInput/ToolOutput to JSON Schema."""
    if hasattr(schema, "parameters"):  # ToolInput
        properties = {}
        required = []
        for param in schema.parameters:
            properties[param.name] = _value_schema_to_json_schema(param.value_schema)
            if param.required:
                required.append(param.name)
        return {"type": "object", "properties": properties, "required": required}
    elif hasattr(schema, "value_schema"):  # ToolOutput
        if schema.value_schema:
            return _value_schema_to_json_schema(schema.value_schema)
        return {"type": "null"}
    elif hasattr(schema, "val_type"):  # ValueSchema
        result: dict[str, Any] = {"type": _arcade_to_json_type(schema.val_type)}
        if schema.enum:
            result["enum"] = schema.enum
        if schema.val_type == "array" and schema.inner_val_type:
            result["items"] = {"type": _arcade_to_json_type(schema.inner_val_type)}
        return result
    return {}


def _arcade_to_json_type(arcade_type: str) -> str:
    """Map Arcade types to JSON Schema types."""
    mapping = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "json": "object",
        "array": "array",
    }
    return mapping.get(arcade_type, "object")
