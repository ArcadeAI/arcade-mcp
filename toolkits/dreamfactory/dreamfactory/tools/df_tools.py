import json
from typing import Annotated, TypedDict

import httpx
from arcade_tdk import ToolContext, tool  # type: ignore[import-untyped]
from arcade_tdk.errors import RetryableToolError
from loguru import logger

RETRY_AFTER_MS = 500


def get_params(
    filter_str: str = "",
    fields: str | list[str] = "*",
    limit: int | None = None,
    offset: int = 0,
    order_field: str = "",
    related: str | list[str] = "",
) -> dict[str, str | int | None]:
    params: dict[str, str | int | None] = {}
    if filter_str:
        params["filter"] = filter_str
    if fields:
        params["fields"] = fields if isinstance(fields, str) else ",".join(fields)
    if limit:
        params["limit"] = limit
    if offset:
        params["offset"] = offset
    if order_field:
        params["order"] = order_field
    if related:
        params["related"] = related if isinstance(related, str) else ",".join(related)
    return params


class TableUrlWithHeaders(TypedDict):
    url: str
    headers: dict[str, str]


def table_url_with_headers(table_name: str, base_url: str, dream_factory_api_key: str) -> TableUrlWithHeaders:
    return {"url": f"{base_url}/_table/{table_name}", "headers": {"X-DreamFactory-API-Key": dream_factory_api_key}}


@tool(requires_secrets=["DREAM_FACTORY_BASE_URL", "DREAM_FACTORY_API_KEY"])  # type: ignore[arg-type]
def list_table_names(context: ToolContext) -> str:
    """List the names of all the available tables."""

    base_url = context.get_secret("DREAM_FACTORY_BASE_URL")
    dream_factory_api_key = context.get_secret("DREAM_FACTORY_API_KEY")
    try:
        res = httpx.get(url=f"{base_url}/_table", headers={"X-DreamFactory-API-Key": dream_factory_api_key}).json()
    except Exception as e:
        raise RetryableToolError(  # noqa: TRY003
            f"Failed to list table names: {e}", retry_after_ms=RETRY_AFTER_MS
        ) from e
    return json.dumps({"available_tables": [t["name"] for t in res["resource"]]})


@tool(requires_secrets=["DREAM_FACTORY_BASE_URL", "DREAM_FACTORY_API_KEY"])  # type: ignore[arg-type]
def get_table_schema(
    context: ToolContext, table_name: Annotated[str, "The name of the table to get the schema for"]
) -> str:
    """Get the schema of a table.

    Parameters
    ----------
    table_name : str
        The name of the table to get the schema for

    Returns
    -------
    dict[str, str | dict[str, str]]
        The schema information for the specified table
    """

    base_url = context.get_secret("DREAM_FACTORY_BASE_URL")
    dream_factory_api_key = context.get_secret("DREAM_FACTORY_API_KEY")
    logger.info(f"Accessing schema for table {table_name} with API key {dream_factory_api_key}")
    try:
        return json.dumps(
            httpx.get(
                url=f"{base_url}/_schema/{table_name}", headers={"X-DreamFactory-API-Key": dream_factory_api_key}
            ).json()
        )
    except Exception as e:
        raise RetryableToolError(  # noqa: TRY003
            f"Failed to get schema for table {table_name}: {e}", retry_after_ms=RETRY_AFTER_MS
        ) from e


@tool(requires_secrets=["DREAM_FACTORY_BASE_URL", "DREAM_FACTORY_API_KEY"])  # type: ignore[arg-type]
def get_table_records(
    context: ToolContext,
    table_name: Annotated[str, "The name of the table to get the records from"],
    filter_str: Annotated[
        str, "The filter to apply to the data. This is equivalent to the WHERE clause of a SQL statement"
    ] = "",
    fields: Annotated[
        list[str] | None,
        """The fields to return. If ['*'] or None, all fields will be returned. Default is None""",
    ] = None,
    limit: Annotated[
        int | None,
        """Max number of records to return. If None, all matching records will be returned,
        subject to the offset parameter or system settings maximum. Default is None""",
    ] = None,
    offset: Annotated[
        int,
        """Index of first record to return. For example, to get records 91-100,
        set offset to 90 and limit to 10. Default is 0""",
    ] = 0,
    order_field: Annotated[
        str,
        """The field to order the records by. Also supports sort direction ASC or DESC
        such as 'Name ASC'. Default direction is ASC""",
    ] = "",
    related: Annotated[
        list[str] | None,
        """Names of related tables to join via foreign keys based on the schema
        (e.g. hr_employees_by_department_id). Can be a single table name,
        a list of table names, or ['*'] to include all related tables. Default is None""",
    ] = None,
) -> str:
    """Get the records of a table.

    Parameters
    ----------
    table_name : str
        The name of the table to get the records from
    filter_str : str, optional
        The filter to apply to the data. This is equivalent to the WHERE clause of a SQL statement
    fields : list[str], optional
        The fields to return. If ['*'] or None, all fields will be returned. Default is None
    limit : int or None, optional
        Max number of records to return. If None, all matching records will be returned,
        subject to the offset parameter or system settings maximum. Default is None
    offset : int, optional
        Index of first record to return. For example, to get records 91-100,
        set offset to 90 and limit to 10. Default is 0
    order_field : str, optional
        The field to order the records by. Also supports sort direction ASC or DESC
        such as 'Name ASC'. Default direction is ASC
    related : list[str], optional
        Names of related tables to join via foreign keys based on the schema
        (e.g. hr_employees_by_department_id). Can be a single table name,
        a list of table names, or ['*'] to include all related tables. Default is None

    Returns
    -------
    dict
        The records of the table

    Notes
    -----
    Filter Strings support standardized ANSI SQL syntax with the following operators:

    Logical Operators (clauses must be wrapped in parentheses):
    - AND: True if both conditions are true
    - OR: True if either condition is true
    - NOT: True if the condition is false

    Comparison Operators:
    - '=' or 'EQ': Equality test
    - '!=' or 'NE' or '<>': Inequality test
    - '>' or 'GT': Greater than
    - '>=' or 'GTE': Greater than or equal
    - '<' or 'LT': Less than
    - '<=' or 'LTE': Less than or equal
    - 'IN': Equality check against values in a set, e.g., a IN (1,2,3)
    - 'NOT IN' or 'NIN': Inverse of IN (MongoDB only)
    - 'LIKE': Pattern matching with '%' wildcard
    - 'CONTAINS': Same as LIKE '%value%'
    - 'STARTS WITH': Same as LIKE 'value%'
    - 'ENDS WITH': Same as LIKE '%value'

    REMINDER: When using an operator, you must include the parentheses.

    Examples
    --------
    >>> # Filter by name
    >>> (first_name='John') AND (last_name='Smith')
    >>> # Filter by multiple first names
    >>> (first_name='John') OR (first_name='Jane')
    >>> # Filter by inequality
    >>> first_name!='John'
    >>> # Pattern matching
    >>> first_name like 'J%'
    >>> email like '%@mycompany.com'
    >>> # Range filtering
    >>> (Age >= 30) AND (Age < 40)
    """
    try:
        return json.dumps(
            httpx.get(
                **table_url_with_headers(
                    table_name=table_name,
                    base_url=context.get_secret("DREAM_FACTORY_BASE_URL"),
                    dream_factory_api_key=context.get_secret("DREAM_FACTORY_API_KEY"),
                ),
                params=get_params(
                    filter_str=filter_str,
                    fields=fields or "*",
                    limit=limit,
                    offset=offset,
                    order_field=order_field,
                    related=related or "",
                ),
            ).json()
        )
    except Exception as e:
        raise RetryableToolError(  # noqa: TRY003
            f"Failed to get records for table {table_name}: {e}", retry_after_ms=RETRY_AFTER_MS
        ) from e


@tool(requires_secrets=["DREAM_FACTORY_BASE_URL", "DREAM_FACTORY_API_KEY"])  # type: ignore[arg-type]
def get_table_records_by_ids(
    context: ToolContext,
    table_name: Annotated[str, "The name of the table to get the records from"],
    ids: Annotated[list[str], "The IDs of the records to get"],
    fields: Annotated[
        list[str] | None,
        """The fields to return. If ['*'] or None, all fields will be returned. Default is None""",
    ] = None,
    related: Annotated[
        list[str] | None,
        """Names of related tables to join via foreign keys based on the schema
        (e.g. hr_employees_by_department_id). Can be a single table name,
        a list of table names, or ['*'] to include all related tables. Default is None""",
    ] = None,
) -> str:
    """Get one or more records from a table by their IDs.

    Parameters
    ----------
    table_name : str
        The name of the table to get the records from
    ids : list[str]
        The IDs of the records to get
    fields : list[str], optional
        The fields to return. If ['*'] or None, all fields will be returned. Default is None
    related : list[str], optional
        Names of related tables to join via foreign keys based on the schema
        (e.g. hr_employees_by_department_id). Can be a single table name,
        a list of table names, or ['*'] to include all related tables. Default is None

    Returns
    -------
    dict
        The records of the table
    """
    params: dict[str, str | int | None] = {"ids": ids if isinstance(ids, str) else ",".join(ids)}
    params.update(get_params(fields=fields or "*", related=related or ""))
    try:
        return json.dumps(
            httpx.get(
                **table_url_with_headers(
                    table_name=table_name,
                    base_url=context.get_secret("DREAM_FACTORY_BASE_URL"),
                    dream_factory_api_key=context.get_secret("DREAM_FACTORY_API_KEY"),
                ),
                params=params,
            ).json()
        )
    except Exception as e:
        raise RetryableToolError(  # noqa: TRY003
            f"Failed to get records for table {table_name}: {e}", retry_after_ms=RETRY_AFTER_MS
        ) from e


@tool
def calculate_sum(values: Annotated[list[float], "List of numerical values to sum"]) -> float:
    """Calculate the sum of a list of values.

    Parameters
    ----------
    values : list[float]
        List of numerical values to sum

    Returns
    -------
    float
        Sum of the input values
    """
    return sum(values)


@tool
def calculate_difference(num1: Annotated[float, "First number"], num2: Annotated[float, "Second number"]) -> float:
    """Calculate the difference between two numbers.

    Parameters
    ----------
    num1 : float
        First number
    num2 : float
        Second number

    Returns
    -------
    float
        The result of num2 - num1
    """
    return num2 - num1


@tool
def calculate_mean(values: Annotated[list[float], "List of numerical values to calculate the mean of"]) -> float:
    """Calculate the mean of a list of values.

    Parameters
    ----------
    values : list[float]
        List of numerical values

    Returns
    -------
    float
        Arithmetic mean of the input values
    """
    return sum(values) / len(values)
