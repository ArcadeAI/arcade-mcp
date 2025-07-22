import json

from arcade_cli.toolkit_docs.docs_builder import build_javascript_example, build_python_example
from arcade_cli.toolkit_docs.templates import TOOL_CALL_EXAMPLE_JS, TOOL_CALL_EXAMPLE_PY


def test_build_javascript_example():
    tool_fully_qualified_name = "Toolkit.ToolName"

    input_map = {
        "str_arg": "str_value",
        "fake_bool_value": "true",
        "fake_bool_phrase": "this is not a true boolean",
        "int_arg": 123,
        "bool_arg": True,
        "list_arg": ["item1", "item2"],
        "dict_arg": {"key1": "value1", "key2": "value2"},
        "list_of_bool": [True, False],
    }

    response = build_javascript_example(tool_fully_qualified_name, input_map, TOOL_CALL_EXAMPLE_JS)
    assert response == TOOL_CALL_EXAMPLE_JS.format(
        tool_fully_qualified_name=tool_fully_qualified_name,
        input_map=json.dumps(input_map, indent=2, ensure_ascii=False),
    )


def test_build_python_example():
    tool_fully_qualified_name = "Toolkit.ToolName"

    input_map = {
        "str_arg": "str_value",
        "fake_bool_value": "true",
        "fake_bool_phrase": "this is not a true boolean",
        "int_arg": 123,
        "bool_arg": True,
        "list_arg": ["item1", "item2"],
        "dict_arg": {"key1": "value1", "key2": "value2"},
        "list_of_bool": [True, False],
    }

    input_map_str = """{
    'str_arg': 'str_value',
    'fake_bool_value': 'true',
    'fake_bool_phrase': 'this is not a true boolean',
    'int_arg': 123,
    'bool_arg': True,
    'list_arg': ['item1', 'item2'],
    'dict_arg': {'key1': 'value1', 'key2': 'value2'},
    'list_of_bool': [True, False]
}"""

    response = build_python_example(tool_fully_qualified_name, input_map, TOOL_CALL_EXAMPLE_PY)
    assert response == TOOL_CALL_EXAMPLE_PY.format(
        tool_fully_qualified_name=tool_fully_qualified_name,
        input_map=input_map_str,
    )
