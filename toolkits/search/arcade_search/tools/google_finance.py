from typing import Annotated, Any

from arcade_tdk import ToolContext, tool

from arcade_search.enums import GoogleFinanceWindow
from arcade_search.utils import call_serpapi, prepare_params


@tool(requires_secrets=["SERP_API_KEY"])
async def get_stock_summary(
    context: ToolContext,
    ticker_symbol: Annotated[
        str,
        "The stock ticker to get summary for. For example, 'GOOG' is the ticker symbol for Google",
    ],
    exchange_identifier: Annotated[
        str,
        "The exchange identifier. This part indicates the market where the "
        "stock is traded. For example, 'NASDAQ', 'NYSE', 'TSE', 'LSE', etc.",
    ],
) -> Annotated[dict[str, Any], "Summary of the stock's recent performance"]:
    """Retrieve the summary information for a given stock ticker using the Google Finance API.

    Gets the stock's current price as well as price movement from the most recent trading day.
    """
    # Prepare the request
    query = (
        f"{ticker_symbol.upper()}:{exchange_identifier.upper()}"
        if exchange_identifier
        else ticker_symbol.upper()
    )
    params = prepare_params("google_finance", q=query)

    # Execute the request
    results = call_serpapi(context, params)

    # Parse the results
    summary: dict = results.get("summary", {})

    return summary


@tool(requires_secrets=["SERP_API_KEY"])
async def get_stock_historical_data(
    context: ToolContext,
    ticker_symbol: Annotated[
        str,
        "The stock ticker to get summary for. For example, 'GOOG' is the ticker symbol for Google",
    ],
    exchange_identifier: Annotated[
        str,
        "The exchange identifier. This part indicates the market where the "
        "stock is traded. For example, 'NASDAQ', 'NYSE', 'TSE', 'LSE', etc.",
    ],
    window: Annotated[
        GoogleFinanceWindow, "Time window for the graph data. Defaults to 1 month"
    ] = GoogleFinanceWindow.ONE_MONTH,
) -> Annotated[
    dict[str, Any],
    "A stock's price and volume data at a specific time interval over a specified time window",
]:
    """Fetch historical stock price data over a specified time window

    Returns a stock's price and volume data over a specified time window
    """
    # Prepare the request
    query = (
        f"{ticker_symbol.upper()}:{exchange_identifier.upper()}"
        if exchange_identifier
        else ticker_symbol.upper()
    )
    params = prepare_params("google_finance", q=query, window=window.value)

    # Execute the request
    results = call_serpapi(context, params)

    # Parse the results
    data = {
        "summary": results.get("summary", {}),
        "graph": results.get("graph", []),
    }
    key_events = results.get("key_events")
    if key_events:
        data["key_events"] = key_events

    return data
