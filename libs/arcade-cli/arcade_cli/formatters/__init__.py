"""Formatters for evaluation results output."""

from difflib import get_close_matches

from arcade_cli.formatters.base import EvalResultFormatter
from arcade_cli.formatters.html import HtmlFormatter
from arcade_cli.formatters.markdown import MarkdownFormatter
from arcade_cli.formatters.text import TextFormatter

# Registry of available formatters
FORMATTERS: dict[str, type[EvalResultFormatter]] = {
    "txt": TextFormatter,
    "md": MarkdownFormatter,
    "html": HtmlFormatter,
}


def get_formatter(format_name: str) -> EvalResultFormatter:
    """
    Get a formatter instance by name.

    Args:
        format_name: The format name (e.g., 'txt', 'md').

    Returns:
        An instance of the appropriate formatter.

    Raises:
        ValueError: If the format is not supported. Suggests similar format names if available.
    """
    formatter_class = FORMATTERS.get(format_name.lower())
    if formatter_class is None:
        supported = list(FORMATTERS.keys())

        # Try to find a close match for better error messages
        close_matches = get_close_matches(format_name.lower(), supported, n=1, cutoff=0.6)

        error_msg = f"Unsupported format '{format_name}'."
        if close_matches:
            error_msg += f" Did you mean '{close_matches[0]}'?"
        error_msg += f" Supported formats: {', '.join(supported)}"

        raise ValueError(error_msg)
    return formatter_class()


__all__ = [
    "FORMATTERS",
    "EvalResultFormatter",
    "HtmlFormatter",
    "MarkdownFormatter",
    "TextFormatter",
    "get_formatter",
]
