"""Formatters for evaluation and capture results output."""

from difflib import get_close_matches

from arcade_cli.formatters.base import CaptureFormatter, EvalResultFormatter
from arcade_cli.formatters.html import CaptureHtmlFormatter, HtmlFormatter
from arcade_cli.formatters.json import CaptureJsonFormatter, JsonFormatter
from arcade_cli.formatters.markdown import CaptureMarkdownFormatter, MarkdownFormatter
from arcade_cli.formatters.text import CaptureTextFormatter, TextFormatter

# Registry of available formatters for evaluations
FORMATTERS: dict[str, type[EvalResultFormatter]] = {
    "txt": TextFormatter,
    "md": MarkdownFormatter,
    "html": HtmlFormatter,
    "json": JsonFormatter,
}

# Registry of available formatters for capture mode
CAPTURE_FORMATTERS: dict[str, type[CaptureFormatter]] = {
    "json": CaptureJsonFormatter,
    "txt": CaptureTextFormatter,
    "md": CaptureMarkdownFormatter,
    "html": CaptureHtmlFormatter,
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


def get_capture_formatter(format_name: str) -> CaptureFormatter:
    """
    Get a capture formatter instance by name.

    Args:
        format_name: The format name (e.g., 'json', 'txt', 'md', 'html').

    Returns:
        An instance of the appropriate formatter.

    Raises:
        ValueError: If the format is not supported. Suggests similar format names if available.
    """
    formatter_class = CAPTURE_FORMATTERS.get(format_name.lower())
    if formatter_class is None:
        supported = list(CAPTURE_FORMATTERS.keys())

        close_matches = get_close_matches(format_name.lower(), supported, n=1, cutoff=0.6)

        error_msg = f"Unsupported capture format '{format_name}'."
        if close_matches:
            error_msg += f" Did you mean '{close_matches[0]}'?"
        error_msg += f" Supported formats: {', '.join(supported)}"

        raise ValueError(error_msg)
    return formatter_class()


__all__ = [
    # Eval formatters
    "FORMATTERS",
    "EvalResultFormatter",
    "HtmlFormatter",
    "JsonFormatter",
    "MarkdownFormatter",
    "TextFormatter",
    "get_formatter",
    # Capture formatters
    "CAPTURE_FORMATTERS",
    "CaptureFormatter",
    "CaptureHtmlFormatter",
    "CaptureJsonFormatter",
    "CaptureMarkdownFormatter",
    "CaptureTextFormatter",
    "get_capture_formatter",
]
