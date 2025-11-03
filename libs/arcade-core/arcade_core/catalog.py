import asyncio
import inspect
import logging
import os
import re
import typing
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from importlib import import_module
from types import ModuleType
from typing import (
    Annotated,
    Any,
    Literal,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from arcade_core.annotations import Inferrable
from arcade_core.auth import OAuth2, ToolAuthorization
from arcade_core.errors import (
    ToolDefinitionError,
    ToolInputSchemaError,
    ToolkitLoadError,
    ToolOutputSchemaError,
)
from arcade_core.schema import (
    TOOL_NAME_SEPARATOR,
    FullyQualifiedName,
    InputParameter,
    OAuth2Requirement,
    ToolAuthRequirement,
    ToolContext,
    ToolDefinition,
    ToolInput,
    ToolkitDefinition,
    ToolMetadataKey,
    ToolMetadataRequirement,
    ToolOutput,
    ToolRequirements,
    ToolSecretRequirement,
    ValueSchema,
)
from arcade_core.toolkit import Toolkit
from arcade_core.utils import (
    does_function_return_value,
    first_or_none,
    is_strict_optional,
    is_string_literal,
    is_union,
    snake_to_pascal_case,
    space_to_snake_case,
)

logger = logging.getLogger(__name__)

InnerWireType = Literal["string", "integer", "number", "boolean", "json"]
WireType = Union[InnerWireType, Literal["array"]]


def is_typeddict(tp: type) -> bool:
    """
    Check if a type is a TypedDict.
    Works with both typing.TypedDict and typing_extensions.TypedDict.
    """
    try:
        # TypedDict creates classes that inherit from dict
        if not isinstance(tp, type) or not issubclass(tp, dict):
            return False

        # Check for TypedDict-specific attributes
        return (
            hasattr(tp, "__annotations__")
            and hasattr(tp, "__total__")
            and hasattr(tp, "__required_keys__")
            and hasattr(tp, "__optional_keys__")
        )
    except TypeError:
        # Some special forms raise TypeError when checking issubclass
        return False


@dataclass
class WireTypeInfo:
    """
    Represents the wire type information for a value, including its inner type if it's a list.
    """

    wire_type: WireType
    inner_wire_type: InnerWireType | None = None
    enum_values: list[str] | None = None
    properties: dict[str, "WireTypeInfo"] | None = None
    inner_properties: dict[str, "WireTypeInfo"] | None = None
    description: str | None = None


class ToolMeta(BaseModel):
    """
    Metadata for a tool once it's been materialized.
    """

    module: str
    toolkit: str | None = None
    package: str | None = None
    path: str | None = None
    date_added: datetime = Field(default_factory=datetime.now)
    date_updated: datetime = Field(default_factory=datetime.now)


class MaterializedTool(BaseModel):
    """
    Data structure that holds tool information while stored in the Catalog
    """

    tool: Callable
    definition: ToolDefinition
    meta: ToolMeta

    # Thought (Sam): Should generate create these from ToolDefinition?
    input_model: type[BaseModel]
    output_model: type[BaseModel]

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def version(self) -> str | None:
        return self.definition.toolkit.version

    @property
    def description(self) -> str:
        return self.definition.description

    @property
    def requires_auth(self) -> bool:
        return self.definition.requirements.authorization is not None


class ToolCatalog(BaseModel):
    """Singleton class that holds all tools for a given worker"""

    _tools: dict[FullyQualifiedName, MaterializedTool] = {}

    _disabled_tools: set[str] = set()
    _disabled_toolkits: set[str] = set()

    def __init__(self, **data) -> None:  # type: ignore[no-untyped-def]
        super().__init__(**data)
        self._load_disabled_tools()
        self._load_disabled_toolkits()

    def _load_disabled_tools(self) -> None:
        """Load disabled tools from the environment variable.

        The ARCADE_DISABLED_TOOLS environment variable should contain a
        comma-separated list of tools that are to be excluded from the
        catalog.

        The expected format for each disabled tool is:
        - [CamelCaseToolkitName][TOOL_NAME_SEPARATOR][CamelCaseToolName]
        """
        disabled_tools = os.getenv("ARCADE_DISABLED_TOOLS", "").strip().split(",")
        if not disabled_tools:
            return

        pattern = re.compile(rf"^[a-zA-Z]+{re.escape(TOOL_NAME_SEPARATOR)}[a-zA-Z]+$")

        for tool in disabled_tools:
            if not pattern.match(tool):
                continue

            self._disabled_tools.add(tool.lower())

    def _load_disabled_toolkits(self) -> None:
        """Load disabled toolkits from the environment variable.

        The ARCADE_DISABLED_TOOLKITS environment variable should contain a
        comma-separated list of toolkits that are to be excluded from the
        catalog.

        The expected format for each disabled toolkit is:
        - [CamelCaseToolkitName]
        """
        disabled_toolkits = os.getenv("ARCADE_DISABLED_TOOLKITS", "").strip().split(",")
        if not disabled_toolkits:
            return

        for toolkit in disabled_toolkits:
            self._disabled_toolkits.add(toolkit.lower())

    def add_tool(
        self,
        tool_func: Callable,
        toolkit_or_name: str | Toolkit,
        module: ModuleType | None = None,
        toolkit_version: str | None = None,
        toolkit_description: str | None = None,
    ) -> None:
        """
        Add a function to the catalog as a tool.

        Args:
            tool_func: The function to add to the catalog.
            toolkit_or_name: The toolkit or name of the toolkit.
            module: The module to add the tool from.
            toolkit_version: The version of the toolkit. Overrides the version of the toolkit if provided.
            toolkit_description: The description of the toolkit. Overrides the description of the toolkit if provided.
        """

        input_model, output_model = create_func_models(tool_func)

        if isinstance(toolkit_or_name, Toolkit):
            toolkit = toolkit_or_name
            toolkit_name = toolkit.name
            toolkit_version = toolkit_version or toolkit.version
            toolkit_description = toolkit_description or toolkit.description
        elif isinstance(toolkit_or_name, str):
            toolkit = None
            toolkit_name = toolkit_or_name

        if not toolkit_name:
            raise ValueError("A server name or server must be provided.")

        definition = ToolCatalog.create_tool_definition(
            tool_func,
            toolkit_name,
            toolkit_version,
            toolkit_description,
        )

        fully_qualified_name = definition.get_fully_qualified_name()

        if fully_qualified_name in self._tools:
            raise ToolkitLoadError(
                f"Tool '{definition.name}' in server '{toolkit_name}' already exists in the catalog."
            )

        if str(fully_qualified_name).lower() in self._disabled_tools:
            logger.info(f"Tool '{fully_qualified_name!s}' is disabled and will not be cataloged.")
            return

        if str(toolkit_name).lower() in self._disabled_toolkits:
            logger.info(f"Server '{toolkit_name!s}' is disabled and will not be cataloged.")
            return

        self._tools[fully_qualified_name] = MaterializedTool(
            definition=definition,
            tool=tool_func,
            meta=ToolMeta(
                module=module.__name__ if module else tool_func.__module__,
                toolkit=toolkit_name,
                package=toolkit.package_name if toolkit else None,
                path=module.__file__ if module else None,
            ),
            input_model=input_model,
            output_model=output_model,
        )

    def add_module(
        self,
        module: ModuleType,
        name: str | None = None,
        version: str | None = None,
        description: str | None = None,
    ) -> None:
        """
        Add all the tools in a module to the catalog.

        Args:
            module: The module to add.
            name: Optionally override the name of the toolkit with this parameter
            version: Optionally override the version of the toolkit with this parameter
            description: Optionally override the description of the toolkit with this parameter
        """
        toolkit = Toolkit.from_module(module)
        if name:
            toolkit.name = name
        self.add_toolkit(toolkit, version=version, description=description)

    def add_toolkit(
        self, toolkit: Toolkit, version: str | None = None, description: str | None = None
    ) -> None:
        """
        Add the tools from a loaded toolkit to the catalog.

        Args:
            toolkit: The toolkit to add.
            version: Optionally override the version of the toolkit with this parameter
            description: Optionally override the description of the toolkit with this parameter
        """

        if str(toolkit).lower() in self._disabled_toolkits:
            logger.info(f"Server '{toolkit.name!s}' is disabled and will not be cataloged.")
            return

        for module_name, tool_names in toolkit.tools.items():
            for tool_name in tool_names:
                try:
                    module = import_module(module_name)
                    tool_func = getattr(module, tool_name)
                    self.add_tool(
                        tool_func,
                        toolkit,
                        module,
                        toolkit_version=version,
                        toolkit_description=description,
                    )
                except ToolDefinitionError as e:
                    raise e.with_context(tool_name) from e
                except ToolkitLoadError as e:
                    raise e.with_context(toolkit.name) from e
                except ImportError as e:
                    raise ToolkitLoadError(
                        f"Could not import module {module_name}. Reason: {e}"
                    ).with_context(tool_name)
                except AttributeError as e:
                    raise ToolDefinitionError(
                        f"Could not import tool {tool_name} in module {module_name}. Reason: {e}"
                    ).with_context(tool_name)
                except TypeError as e:
                    raise ToolDefinitionError(
                        f"Type error encountered while adding tool {tool_name} from {module_name}. Reason: {e}"
                    ).with_context(tool_name)
                except Exception as e:
                    raise ToolDefinitionError(
                        f"Error encountered while adding tool {tool_name} from {module_name}. Reason: {e}"
                    ).with_context(tool_name)

    def __getitem__(self, name: FullyQualifiedName) -> MaterializedTool:
        return self.get_tool(name)

    def __contains__(self, name: FullyQualifiedName) -> bool:
        return name in self._tools

    def __iter__(self) -> Iterator[MaterializedTool]:  # type: ignore[override]
        yield from self._tools.values()

    def __len__(self) -> int:
        return len(self._tools)

    def is_empty(self) -> bool:
        return len(self._tools) == 0

    def get_tool_names(self) -> list[FullyQualifiedName]:
        return [tool.definition.get_fully_qualified_name() for tool in self._tools.values()]

    def find_tool_by_func(self, func: Callable) -> ToolDefinition:
        """
        Find a tool by its function.
        """
        for _, tool in self._tools.items():
            if tool.tool == func:
                return tool.definition
        raise ValueError(f"Tool {func} not found in the catalog.")

    def get_tool_by_name(
        self,
        name: str,
        version: str | None = None,
        separator: str = TOOL_NAME_SEPARATOR,
    ) -> MaterializedTool:
        """Get a tool from the catalog by name.

        Args:
            name: The name of the tool, potentially including the toolkit name separated by the `separator`.
            version: The version of the toolkit. Defaults to None.
            separator: The separator between toolkit and tool names. Defaults to `TOOL_NAME_SEPARATOR`.

        Returns:
            MaterializedTool: The matching tool from the catalog.

        Raises:
            ValueError: If the tool is not found in the catalog.
        """
        if separator in name:
            toolkit_name, tool_name = name.split(separator, 1)
            fq_name = FullyQualifiedName(
                name=tool_name, toolkit_name=toolkit_name, toolkit_version=version
            )
            return self.get_tool(fq_name)
        else:
            # No toolkit name provided, search tools with matching tool name
            matching_tools = [
                tool
                for fq_name, tool in self._tools.items()
                if fq_name.name.lower() == name.lower()
                and (
                    version is None
                    or (fq_name.toolkit_version or "").lower() == (version or "").lower()
                )
            ]
            if matching_tools:
                return matching_tools[0]

        raise ValueError(f"Tool {name} not found in the catalog.")

    def get_tool(self, name: FullyQualifiedName) -> MaterializedTool:
        """
        Get a tool from the catalog by fully-qualified name and version.
        If the version is not specified, the any version is returned.
        """
        if name.toolkit_version:
            try:
                return self._tools[name]
            except KeyError:
                raise ValueError(f"Tool {name}@{name.toolkit_version} not found in the catalog.")

        for key, tool in self._tools.items():
            if key.equals_ignoring_version(name):
                return tool

        raise ValueError(f"Tool {name} not found.")

    def get_tool_count(self) -> int:
        """
        Get the number of tools in the catalog.
        """
        return len(self._tools)

    @staticmethod
    def create_tool_definition(
        tool: Callable,
        toolkit_name: str,
        toolkit_version: str | None = None,
        toolkit_desc: str | None = None,
    ) -> ToolDefinition:
        """
        Given a tool function, create a ToolDefinition
        """

        raw_tool_name = getattr(tool, "__tool_name__", tool.__name__)

        # Hard requirement: tools must have descriptions
        tool_description = getattr(tool, "__tool_description__", None)
        if not tool_description:
            raise ToolDefinitionError(
                f"Tool '{raw_tool_name}' is missing a description. Tool descriptions are specified as docstrings for the tool function."
            )

        # If the function returns a value, it must have a type annotation
        if does_function_return_value(tool) and tool.__annotations__.get("return") is None:
            raise ToolOutputSchemaError(f"Tool '{raw_tool_name}' must have a return type")

        auth_requirement = create_auth_requirement(tool)
        secrets_requirement = create_secrets_requirement(tool)
        metadata_requirement = create_metadata_requirement(tool, auth_requirement)

        toolkit_definition = ToolkitDefinition(
            name=snake_to_pascal_case(space_to_snake_case(toolkit_name)),
            description=toolkit_desc,
            version=toolkit_version,
        )

        tool_name = snake_to_pascal_case(raw_tool_name)
        fully_qualified_name = FullyQualifiedName.from_toolkit(tool_name, toolkit_definition)
        deprecation_message = getattr(tool, "__tool_deprecation_message__", None)

        return ToolDefinition(
            name=tool_name,
            fully_qualified_name=str(fully_qualified_name),
            description=tool_description,
            toolkit=toolkit_definition,
            input=create_input_definition(tool),
            output=create_output_definition(tool),
            requirements=ToolRequirements(
                authorization=auth_requirement,
                secrets=secrets_requirement,
                metadata=metadata_requirement,
            ),
            deprecation_message=deprecation_message,
        )


def create_input_definition(func: Callable) -> ToolInput:
    """
    Create an input model for a function based on its parameters.
    """
    input_parameters = []
    tool_context_param_name: str | None = None

    for _, param in inspect.signature(func, follow_wrapped=True).parameters.items():
        ann = param.annotation
        if isinstance(ann, type) and issubclass(ann, ToolContext):
            # Soft guidance for developers using legacy ToolContext
            if tool_context_param_name is not None:
                raise ToolInputSchemaError(
                    f"Only one ToolContext parameter is supported, but tool {func.__name__} has multiple."
                )

            tool_context_param_name = param.name
            continue  # No further processing of this param (don't add it to the list of inputs)

        tool_field_info = extract_field_info(param)

        # If the field has a default value, it is not required
        # If the field is optional, it is not required
        has_default_value = tool_field_info.default is not None
        is_required = not tool_field_info.is_optional and not has_default_value

        input_parameters.append(
            InputParameter(
                name=tool_field_info.name,
                description=tool_field_info.description,
                required=is_required,
                inferrable=tool_field_info.is_inferrable,
                value_schema=wire_type_info_to_value_schema(tool_field_info.wire_type_info),
            )
        )

    return ToolInput(
        parameters=input_parameters,
        tool_context_parameter_name=tool_context_param_name,
    )


def create_output_definition(func: Callable) -> ToolOutput:
    """
    Create an output model for a function based on its return annotation.
    """
    return_type = inspect.signature(func, follow_wrapped=True).return_annotation
    description = "No description provided."

    if return_type is inspect.Signature.empty:
        return ToolOutput(
            value_schema=None,
            description="No description provided.",
            available_modes=["null"],
        )

    if hasattr(return_type, "__metadata__"):
        description = (
            return_type.__metadata__[0]
            if return_type.__metadata__
            else "No description provided for return type."
        )
        return_type = return_type.__origin__

    # Unwrap Optional types
    # Both Optional[T] and T | None are supported
    is_optional = is_strict_optional(return_type)
    if is_optional:
        return_type = next(arg for arg in get_args(return_type) if arg is not type(None))

    wire_type_info = get_wire_type_info(return_type)

    available_modes = ["value", "error"]

    if is_optional:
        available_modes.append("null")

    return ToolOutput(
        description=description,
        available_modes=available_modes,
        value_schema=wire_type_info_to_value_schema(wire_type_info),
    )


def create_auth_requirement(tool: Callable) -> ToolAuthRequirement | None:
    """
    Create an auth requirement for a tool.
    """
    auth_requirement = getattr(tool, "__tool_requires_auth__", None)
    if isinstance(auth_requirement, ToolAuthorization):
        new_auth_requirement = ToolAuthRequirement(
            provider_id=auth_requirement.provider_id,
            provider_type=auth_requirement.provider_type,
            id=auth_requirement.id,
        )
        if isinstance(auth_requirement, OAuth2):
            new_auth_requirement.oauth2 = OAuth2Requirement(**auth_requirement.model_dump())
        auth_requirement = new_auth_requirement

    return auth_requirement


def create_secrets_requirement(tool: Callable) -> list[ToolSecretRequirement] | None:
    """
    Create a secrets requirement for a tool.
    """
    raw_tool_name = getattr(tool, "__tool_name__", tool.__name__)
    secrets_requirement = getattr(tool, "__tool_requires_secrets__", None)
    if isinstance(secrets_requirement, list):
        if any(not isinstance(secret, str) for secret in secrets_requirement):
            raise ToolDefinitionError(
                f"Secret keys must be strings (error in tool {raw_tool_name})."
            )

        secrets_requirement = to_tool_secret_requirements(secrets_requirement)
        if any(secret.key is None or secret.key.strip() == "" for secret in secrets_requirement):
            raise ToolDefinitionError(
                f"Secrets must have a non-empty key (error in tool {raw_tool_name})."
            )

    return secrets_requirement


def create_metadata_requirement(
    tool: Callable, auth_requirement: ToolAuthRequirement | None
) -> list[ToolMetadataRequirement] | None:
    """
    Create a metadata requirement for a tool.
    """
    raw_tool_name = getattr(tool, "__tool_name__", tool.__name__)
    metadata_requirement = getattr(tool, "__tool_requires_metadata__", None)
    if isinstance(metadata_requirement, list):
        for metadata in metadata_requirement:
            if not isinstance(metadata, str):
                raise ToolDefinitionError(
                    f"Metadata must be strings (error in tool {raw_tool_name})."
                )
            if ToolMetadataKey.requires_auth(metadata) and auth_requirement is None:
                raise ToolDefinitionError(
                    f"Tool {raw_tool_name} declares metadata key '{metadata}', "
                    "which requires that the tool has an auth requirement, "
                    "but no auth requirement was provided. Please specify an auth requirement."
                )

        metadata_requirement = to_tool_metadata_requirements(metadata_requirement)
        if any(
            metadata.key is None or metadata.key.strip() == "" for metadata in metadata_requirement
        ):
            raise ToolDefinitionError(
                f"Metadata must have a non-empty key (error in tool {raw_tool_name})."
            )

    return metadata_requirement


@dataclass
class ParamInfo:
    """
    Information about a function parameter found through inspection.
    """

    name: str
    default: Any
    original_type: type
    field_type: type
    description: str | None = None
    is_optional: bool = True


@dataclass
class ToolParamInfo:
    """
    Information about a tool parameter, including computed values.
    """

    name: str
    default: Any
    original_type: type
    field_type: type
    wire_type_info: WireTypeInfo
    description: str | None = None
    is_optional: bool = True
    is_inferrable: bool = True

    @classmethod
    def from_param_info(
        cls,
        param_info: ParamInfo,
        wire_type_info: WireTypeInfo,
        is_inferrable: bool = True,
    ) -> "ToolParamInfo":
        return cls(
            name=param_info.name,
            default=param_info.default,
            original_type=param_info.original_type,
            field_type=param_info.field_type,
            description=param_info.description,
            is_optional=param_info.is_optional,
            wire_type_info=wire_type_info,
            is_inferrable=is_inferrable,
        )


def extract_field_info(param: inspect.Parameter) -> ToolParamInfo:
    """
    Extract type and field parameters from a function parameter.
    """
    annotation = param.annotation
    if annotation == inspect.Parameter.empty:
        raise ToolInputSchemaError(f"Parameter {param} has no type annotation.")

    # Get the majority of the param info from either the Pydantic Field() or regular inspection
    if isinstance(param.default, FieldInfo):
        param_info = extract_pydantic_param_info(param)
    else:
        param_info = extract_python_param_info(param)

    metadata = getattr(annotation, "__metadata__", [])
    str_annotations = [m for m in metadata if isinstance(m, str)]

    # Get the description from annotations, if present
    if len(str_annotations) == 0:
        pass
    elif len(str_annotations) == 1:
        param_info.description = str_annotations[0]
    elif len(str_annotations) == 2:
        new_name = str_annotations[0]
        if not new_name.isidentifier():
            raise ToolInputSchemaError(
                f"Invalid parameter name: '{new_name}' is not a valid identifier. "
                "Identifiers must start with a letter or underscore, "
                "and can only contain letters, digits, or underscores."
            )
        param_info.name = new_name
        param_info.description = str_annotations[1]
    else:
        raise ToolInputSchemaError(
            f"Parameter {param} has too many string annotations. Expected 0, 1, or 2, got {len(str_annotations)}."
        )

    # Get the Inferrable annotation, if it exists
    inferrable_annotation = first_or_none(Inferrable, get_args(annotation))

    # Params are inferrable by default
    is_inferrable = inferrable_annotation.value if inferrable_annotation else True

    # Get the wire (serialization) type information for the type
    wire_type_info = get_wire_type_info(param_info.field_type)

    # Final reality check
    if param_info.description is None:
        raise ToolInputSchemaError(
            f"Parameter '{param_info.name}' is missing a description. Parameter descriptions are specified as string annotations using the typing.Annotated class."
        )

    if wire_type_info.wire_type is None:
        raise ToolInputSchemaError(f"Unknown parameter type: {param_info.field_type}")

    return ToolParamInfo.from_param_info(param_info, wire_type_info, is_inferrable)


def get_wire_type_info(_type: type) -> WireTypeInfo:
    """
    Get the wire type information for a given type.
    """

    # Is this a list type?
    # If so, get the inner (enclosed) type
    is_list = get_origin(_type) is list
    inner_properties = None

    if is_list:
        inner_type = get_args(_type)[0]

        # Recursively get wire type info for inner type
        inner_info = get_wire_type_info(inner_type)
        inner_wire_type = cast(InnerWireType, inner_info.wire_type)

        # If inner type has properties (it's a complex object), propagate them
        if inner_info.properties:
            inner_properties = inner_info.properties
        # If inner type is array (nested arrays), propagate inner_properties
        elif inner_info.inner_properties:
            inner_properties = inner_info.inner_properties
    else:
        inner_wire_type = None

    # Get the outer wire type
    wire_type = get_wire_type(str) if is_string_literal(_type) else get_wire_type(_type)

    # Handle enums (known/fixed lists of values)
    is_enum = False
    enum_values: list[str] = []

    type_to_check = inner_type if is_list else _type

    # Strip generic parameters if type_to_check is a parameterized generic
    actual_type = get_origin(type_to_check) or type_to_check

    # Special case: Literal["string1", "string2"] can be enumerated on the wire
    if is_string_literal(type_to_check):
        is_enum = True
        enum_values = [str(e) for e in get_args(type_to_check)]

    # Special case: Enum can be enumerated on the wire
    elif isinstance(actual_type, type) and issubclass(actual_type, Enum):
        is_enum = True
        enum_values = [e.value for e in actual_type]

    # Extract properties for complex types
    properties = None
    if wire_type == "json" and not is_list:
        properties = extract_properties(type_to_check)

    return WireTypeInfo(
        wire_type,
        inner_wire_type,
        enum_values if is_enum else None,
        properties,
        inner_properties,
    )


def _extract_typeddict_field_descriptions(typeddict_class: type) -> dict[str, str]:
    """
    Extract field descriptions from TypedDict docstrings.

    TypedDict classes typically have field descriptions as docstrings after each field.
    This function attempts to parse the source code to extract these descriptions.
    """
    descriptions = {}

    try:
        source = inspect.getsource(typeddict_class)
        # Simple regex to match field: type pattern followed by a docstring
        # This is a simplified approach - a full AST parser would be more robust
        import re

        # Pattern to match field definition followed by docstring
        pattern = r'(\w+):\s*[^"\n]+\n\s*"""([^"]+)"""'
        matches = re.findall(pattern, source)

        for field_name, description in matches:
            descriptions[field_name] = description.strip()

    except (OSError, TypeError):
        # If we can't get the source, return empty descriptions
        pass

    return descriptions


def extract_properties(type_to_check: type) -> dict[str, WireTypeInfo] | None:
    """
    Extract properties from TypedDict, Pydantic models, or other structured types.
    """
    properties = {}

    # Handle Pydantic BaseModel
    if isinstance(type_to_check, type) and issubclass(type_to_check, BaseModel):
        for field_name, field_info in type_to_check.model_fields.items():
            # Get the field type
            field_type = field_info.annotation
            if field_type is None:
                continue

            # Handle Optional types (Union[T, None])
            if is_strict_optional(field_type):
                # Extract the non-None type from Optional
                field_type = next(arg for arg in get_args(field_type) if arg is not type(None))

            # Get wire type info recursively
            # field_type cannot be None here due to the check above
            wire_info = get_wire_type_info(field_type)
            properties[field_name] = wire_info

    # Handle TypedDict
    elif is_typeddict(type_to_check):
        # Get type hints for the TypedDict
        type_hints = get_type_hints(type_to_check, include_extras=True)

        # Try to extract field descriptions from the class source
        field_descriptions = _extract_typeddict_field_descriptions(type_to_check)

        for field_name, field_type in type_hints.items():
            # Handle Optional types (Union[T, None])
            if is_strict_optional(field_type):
                # Extract the non-None type from Optional
                field_type = next(arg for arg in get_args(field_type) if arg is not type(None))
            wire_info = get_wire_type_info(field_type)

            # Add description if available
            if field_name in field_descriptions:
                wire_info.description = field_descriptions[field_name]

            properties[field_name] = wire_info

    # Handle regular dict with type annotations (e.g., dict[str, Any])
    elif get_origin(type_to_check) is dict:
        # For generic dicts, we can't extract specific properties
        return None

    return properties if properties else None


def wire_type_info_to_value_schema(wire_info: WireTypeInfo) -> ValueSchema:
    """
    Convert WireTypeInfo to ValueSchema, including nested properties.
    """
    # Convert nested properties if they exist
    properties = None
    if wire_info.properties:
        properties = {
            name: wire_type_info_to_value_schema(nested_info)
            for name, nested_info in wire_info.properties.items()
        }

    # Convert inner properties for array items
    inner_properties = None
    if wire_info.inner_properties:
        inner_properties = {
            name: wire_type_info_to_value_schema(nested_info)
            for name, nested_info in wire_info.inner_properties.items()
        }

    return ValueSchema(
        val_type=wire_info.wire_type,
        inner_val_type=wire_info.inner_wire_type,
        enum=wire_info.enum_values,
        properties=properties,
        inner_properties=inner_properties,
        description=wire_info.description,
    )


def extract_python_param_info(param: inspect.Parameter) -> ParamInfo:
    # If the param is Annotated[], unwrap the annotation to get the "real" type
    # Otherwise, use the literal type
    annotation = param.annotation
    original_type = annotation.__args__[0] if get_origin(annotation) is Annotated else annotation
    field_type = original_type

    # Handle optional types
    # Both Optional[T] and T | None are supported
    is_optional = is_strict_optional(field_type)
    if is_optional:
        field_type = next(arg for arg in get_args(field_type) if arg is not type(None))

    # Union types are not currently supported
    # (other than optional, which is handled above)
    if is_union(field_type):
        raise ToolInputSchemaError(
            f"Parameter {param.name} is a union type. Only optional types are supported."
        )

    return ParamInfo(
        name=param.name,
        default=param.default if param.default is not inspect.Parameter.empty else None,
        is_optional=is_optional,
        original_type=original_type,
        field_type=field_type,
    )


def extract_pydantic_param_info(param: inspect.Parameter) -> ParamInfo:
    default_value = None if param.default.default is PydanticUndefined else param.default.default

    if param.default.default_factory is not None:
        if callable(param.default.default_factory):
            default_value = param.default.default_factory()
        else:
            raise ToolInputSchemaError(f"Default factory for parameter {param} is not callable.")

    # If the param is Annotated[], unwrap the annotation to get the "real" type
    # Otherwise, use the literal type
    original_type = (
        param.annotation.__args__[0]
        if get_origin(param.annotation) is Annotated
        else param.annotation
    )
    field_type = original_type

    # Unwrap Optional types
    # Both Optional[T] and T | None are supported
    is_optional = is_strict_optional(field_type)
    if is_optional:
        field_type = next(arg for arg in get_args(field_type) if arg is not type(None))

    return ParamInfo(
        name=param.name,
        description=param.default.description,
        default=default_value,
        is_optional=is_optional,
        original_type=original_type,
        field_type=field_type,
    )


def get_wire_type(
    _type: type,
) -> WireType:
    """
    Mapping between Python types and HTTP/JSON types
    """
    # TODO ensure Any is not allowed
    type_mapping: dict[type, WireType] = {
        str: "string",
        bool: "boolean",
        int: "integer",
        float: "number",
        dict: "json",
    }
    outer_type_mapping: dict[type, WireType] = {
        list: "array",
        dict: "json",
    }
    wire_type = type_mapping.get(_type)
    if wire_type:
        return wire_type

    if hasattr(_type, "__origin__"):
        wire_type = outer_type_mapping.get(cast(type, get_origin(_type)))
        if wire_type:
            return wire_type

    if isinstance(_type, type) and issubclass(_type, Enum):
        return "string"

    if isinstance(_type, type) and issubclass(_type, BaseModel):
        return "json"

    if is_typeddict(_type):
        return "json"

    raise ToolDefinitionError(f"Unsupported parameter type: {_type}")


def create_func_models(func: Callable) -> tuple[type[BaseModel], type[BaseModel]]:
    """
    Analyze a function to create corresponding Pydantic models for its input and output.
    """
    input_fields = {}
    # TODO figure this out (Sam)
    if asyncio.iscoroutinefunction(func) and hasattr(func, "__wrapped__"):
        func = func.__wrapped__
    for name, param in inspect.signature(func, follow_wrapped=True).parameters.items():
        # Skip ToolContext parameters (including subclasses like arcade_mcp_server.Context)
        ann = param.annotation
        if isinstance(ann, type) and issubclass(ann, ToolContext):
            continue

        # TODO make this cleaner
        tool_field_info = extract_field_info(param)
        param_fields = {
            "default": tool_field_info.default,
            "description": tool_field_info.description
            if tool_field_info.description
            else "No description provided.",
            # TODO more here?
        }
        input_fields[name] = (tool_field_info.field_type, Field(**param_fields))

    input_model = create_model(f"{snake_to_pascal_case(func.__name__)}Input", **input_fields)  # type: ignore[call-overload]

    output_model = determine_output_model(func)
    return input_model, output_model


def determine_output_model(func: Callable) -> type[BaseModel]:
    """
    Determine the output model for a function based on its return annotation.
    """
    return_annotation = inspect.signature(func).return_annotation
    output_model_name = f"{snake_to_pascal_case(func.__name__)}Output"

    # If the return annotation is empty, create a model with no fields
    if return_annotation is inspect.Signature.empty:
        return create_model(output_model_name)

    # If the return annotation has an __origin__ attribute
    # and does not have a __metadata__ attribute.
    # This is the case for TypedDicts.
    elif hasattr(return_annotation, "__origin__"):
        if hasattr(return_annotation, "__metadata__"):
            field_type = return_annotation.__args__[0]
            description = (
                return_annotation.__metadata__[0] if return_annotation.__metadata__ else ""
            )

            # Check if the field type is a TypedDict
            if is_typeddict(field_type):
                # Create a Pydantic model from TypedDict
                typeddict_model = create_model_from_typeddict(
                    field_type, f"{output_model_name}TypedDict"
                )
                return create_model(
                    output_model_name,
                    result=(
                        typeddict_model,
                        Field(
                            description=str(description)
                            if description
                            else "No description provided."
                        ),
                    ),
                )

            # If the return annotation has a description, use it
            if description:
                try:
                    return create_model(
                        output_model_name,
                        result=(field_type, Field(description=str(description))),
                    )
                except Exception:
                    raise ToolOutputSchemaError(
                        f"Unsupported output type '{field_type}'. Only built-in Python types, TypedDicts, "
                        "Pydantic models, and standard collections are supported as tool output types."
                    )

        # If the return annotation is a Union type
        origin = return_annotation.__origin__
        if origin is typing.Union:
            # For union types, create a model with the first non-None argument
            # TODO handle multiple non-None arguments. Raise error?
            for arg in get_args(return_annotation):
                if arg is not type(None):
                    # Check if the arg is a TypedDict
                    if is_typeddict(arg):
                        typeddict_model = create_model_from_typeddict(
                            arg, f"{output_model_name}TypedDict"
                        )
                        return create_model(
                            output_model_name,
                            result=(
                                typeddict_model,
                                Field(description="No description provided."),
                            ),
                        )
                    return create_model(
                        output_model_name,
                        result=(
                            arg,
                            Field(description="No description provided."),
                        ),
                    )

        # If the return annotation has an __origin__ attribute
        # and does not have a __metadata__ attribute.
        # This is the case for TypedDicts.
        return create_model(
            output_model_name,
            result=(
                return_annotation,
                Field(description="No description provided."),
            ),
        )
    else:
        # If the return annotation is a TypedDict
        if is_typeddict(return_annotation):
            typeddict_model = create_model_from_typeddict(return_annotation, output_model_name)
            return create_model(
                output_model_name,
                result=(
                    typeddict_model,
                    Field(description="No description provided."),
                ),
            )

        # If the return annotation is a simple type (like str)
        return create_model(
            output_model_name,
            result=(
                return_annotation,
                Field(description="No description provided."),
            ),
        )


def create_model_from_typeddict(typeddict_class: type, model_name: str) -> type[BaseModel]:
    """
    Create a Pydantic model from a TypedDict class.
    This enables runtime validation of TypedDict structures.
    """
    # Get type hints for the TypedDict
    type_hints = get_type_hints(typeddict_class, include_extras=True)

    # Build field definitions for the Pydantic model
    field_definitions: dict[str, Any] = {}
    for field_name, field_type in type_hints.items():
        # Check if field is required
        is_required = field_name in getattr(typeddict_class, "__required_keys__", set())

        # Handle nested TypedDict
        if is_typeddict(field_type):
            nested_model = create_model_from_typeddict(field_type, f"{model_name}_{field_name}")
            if is_required:
                field_definitions[field_name] = (nested_model, Field())
            else:
                field_definitions[field_name] = (nested_model, Field(default=None))
        else:
            if is_required:
                field_definitions[field_name] = (field_type, Field())
            else:
                field_definitions[field_name] = (field_type, Field(default=None))

    # Create and return the Pydantic model
    return create_model(model_name, **field_definitions)


def to_tool_secret_requirements(
    secrets_requirement: list[str],
) -> list[ToolSecretRequirement]:
    # De-dupe case-insensitively but preserve the original casing for env var lookup
    unique_map: dict[str, str] = {}
    for name in secrets_requirement:
        lowered = str(name).lower()
        if lowered not in unique_map:
            unique_map[lowered] = str(name)
    return [ToolSecretRequirement(key=orig_name) for orig_name in unique_map.values()]


def to_tool_metadata_requirements(
    metadata_requirement: list[str],
) -> list[ToolMetadataRequirement]:
    # Iterate through the list, de-dupe case-insensitively, and convert each string to a ToolMetadataRequirement
    unique_metadata = {name.lower(): name.lower() for name in metadata_requirement}.values()
    return [ToolMetadataRequirement(key=name) for name in unique_metadata]
