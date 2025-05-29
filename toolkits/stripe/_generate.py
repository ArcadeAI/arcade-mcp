import logging
from pathlib import Path
from typing import Union, get_args

from stripe_agent_toolkit.functions import *  # noqa: F403
from stripe_agent_toolkit.prompts import *  # noqa: F403
from stripe_agent_toolkit.schema import *  # noqa: F403
from stripe_agent_toolkit.tools import tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_type_str(arg_type):
    """Extract type name, handling Optional/Union types."""
    if hasattr(arg_type, "__origin__") and arg_type.__origin__ is Union:
        non_none = [a for a in get_args(arg_type) if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0].__name__
    return arg_type.__name__ if hasattr(arg_type, "__name__") else str(arg_type)


def generate_stripe_tools(
    output_file: Path = Path("arcade_stripe") / "tools" / "stripe.py",
) -> None:
    """
    Generate the Arcade AI Stripe Toolkit file from the stripe agent toolkit definitions.
    """
    logger.info("Generating stripe tools file at %s", output_file)
    try:
        output_file.touch(exist_ok=True)
        with output_file.open("w") as f:
            f.write("""import os
from typing import Annotated, Optional

from stripe_agent_toolkit.api import StripeAPI

from arcade_tdk import ToolContext, tool

def run_stripe_tool(context: ToolContext, method_name: str, params: dict) -> str:
    \"\"\"
    Helper function that retrieves the Stripe secret key, initializes the API,
    and executes the specified method with the provided parameters.
    \"\"\"
    api_key = context.get_secret("STRIPE_SECRET_KEY")
    stripe_api = StripeAPI(secret_key=api_key, context=None)
    params = {k: v for k, v in params.items() if v is not None}
    return stripe_api.run(method_name, **params)  # type: ignore[no-any-return]

""")
            # Generate each tool function from the stripe agent toolkit
            for tool_info in tools:
                method_name = tool_info["method"]
                method = globals().get(method_name)
                if not method:
                    logger.warning("Method %s not found.", method_name)
                    continue

                args_schema = tool_info["args_schema"]
                description = tool_info["description"].strip()

                arg_names = list(args_schema.__annotations__.keys())
                arg_types = [args_schema.__annotations__[field] for field in arg_names]

                params_list = []
                for name, arg_type in zip(arg_names, arg_types, strict=False):
                    field = args_schema.model_fields[name]
                    # Check if the type annotation already includes Optional (i.e. Union[..., None])
                    is_optional_type = (
                        hasattr(arg_type, "__origin__")
                        and arg_type.__origin__ is Union
                        and type(None) in get_args(arg_type)
                    )
                    if field.is_required:
                        if is_optional_type:
                            params_list.append(
                                f"{name}: Annotated[{get_type_str(arg_type)} | None, "
                                f'"{field.description}"] = None'
                            )
                        else:
                            params_list.append(
                                f"{name}: Annotated[{get_type_str(arg_type)}, "
                                f'"{field.description}"]'
                            )
                    else:
                        default_repr = "None" if field.default is None else repr(field.default)
                        params_list.append(
                            f"{name}: Annotated[Optional[{get_type_str(arg_type)}], "
                            f'"{field.description}"] = {default_repr}'
                        )
                params_str = ", ".join(params_list)
                dict_items = ", ".join([f'"{name}": {name}' for name in arg_names])
                arcade_tool_code = (
                    f'@tool(requires_secrets=["STRIPE_SECRET_KEY"])\n'
                    f"def {method_name}(context: ToolContext, {params_str}) -> "
                    f'Annotated[str, "{description.splitlines()[0]}"]:\n'
                    f'    """{description.splitlines()[0]}"""\n'
                    f'    return run_stripe_tool(context, "{method_name}", '
                    + "{"
                    + dict_items
                    + "})\n\n"
                )
                f.write(arcade_tool_code)
    except Exception:
        logger.exception("An error occurred while generating stripe tools")
        raise


if __name__ == "__main__":
    generate_stripe_tools()
