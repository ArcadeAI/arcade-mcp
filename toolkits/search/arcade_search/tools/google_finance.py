from typing import Annotated, Any

import serpapi
from arcade.sdk import ToolContext, tool

from arcade_search.enums import GoogleFinanceWindow


@tool(requires_secrets=["SERP_API_KEY"])
async def get_stock_summary(
    context: ToolContext,
    ticker_symbol: Annotated[str, "The stock ticker to get summary for (e.g., GOOG)"],
    exchange_identifier: Annotated[
        str,
        "The exchange identifier. This part indicates the market where the "
        "stock is traded (e.g., NASDAQ)",
    ],
) -> Annotated[dict[str, Any], "Summary of the stock's recent performance"]:
    """
    Retrieve the summary information for a given stock ticker using the Google Finance API.

    This tool uses the SerpApi Google Finance endpoint to fetch summary details such as the
    stock title, exchange, current price, and other summary fields.
    """
    api_key = context.get_secret("SERP_API_KEY")
    client = serpapi.Client(api_key=api_key)

    query = (
        f"{ticker_symbol.upper()}:{exchange_identifier.upper()}"
        if exchange_identifier
        else ticker_symbol.upper()
    )

    params = {
        "engine": "google_finance",
        "q": query,
    }

    search = client.search(params)
    results = search.as_dict()

    summary = results.get("summary", {})
    return summary


@tool(requires_secrets=["SERP_API_KEY"])
async def get_stock_chart_data(
    context: ToolContext,
    ticker_symbol: Annotated[str, "The stock ticker to get summary for (e.g., GOOG)"],
    exchange_identifier: Annotated[
        str,
        "The exchange identifier. This part indicates the market where the "
        "stock is traded (e.g., NASDAQ)",
    ],
    window: Annotated[
        GoogleFinanceWindow, "Time window for the chart data. Defaults to 1 day"
    ] = GoogleFinanceWindow.ONE_DAY,
) -> Annotated[dict[str, Any], "Chart data and key events if there are any"]:
    """
    Retrieve chart data and key events for a given stock ticker using the Google Finance API.

    This tool uses the SerpApi Google Finance endpoint with the specified time window to fetch
    graph data (historical prices) and, if available, key events associated with the stock.
    """
    api_key = context.get_secret("SERP_API_KEY")
    client = serpapi.Client(api_key=api_key)

    query = (
        f"{ticker_symbol.upper()}:{exchange_identifier.upper()}"
        if exchange_identifier
        else ticker_symbol.upper()
    )
    params = {"engine": "google_finance", "q": query, "window": window.value}

    search = client.search(params)
    results = search.as_dict()

    data = {
        "summary": results.get("summary", {}),
        "graph": results.get("graph", []),
    }
    key_events = results.get("key_events")
    if key_events:
        data["key_events"] = key_events

    return data
