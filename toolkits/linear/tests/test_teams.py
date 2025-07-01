import pytest
from arcade_tdk import ToolContext

from arcade_linear.tools.teams import get_teams


@pytest.mark.asyncio
async def test_get_teams_success(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response,
    build_team_dict,
    build_graphql_response,
    build_paginated_response,
):
    """Test successful team retrieval"""
    # Create sample teams
    team1 = build_team_dict(name="Team Alpha", key="ALPHA")
    team2 = build_team_dict(name="Team Beta", key="BETA")

    # Build paginated response
    teams_response = build_paginated_response([team1, team2])

    # Build full GraphQL response
    graphql_data = build_graphql_response({"teams": teams_response})

    # Mock the HTTP response
    http_response = mock_httpx_response(200, graphql_data)
    mock_httpx_client.post.return_value = http_response

    result = await get_teams(context=mock_context)

    assert result["total_count"] == 2
    assert len(result["teams"]) == 2
    assert result["teams"][0]["name"] == "Team Alpha"
    assert result["teams"][0]["key"] == "ALPHA"
    assert result["teams"][1]["name"] == "Team Beta"
    assert result["teams"][1]["key"] == "BETA"

    # Verify the request was made correctly
    mock_httpx_client.post.assert_called_once()
    call_args = mock_httpx_client.post.call_args

    # Check URL
    assert call_args[0][0] == "https://api.linear.app/graphql"

    # Check that query is in the request body
    request_body = call_args[1]["json"]
    assert "query" in request_body
    assert "teams" in request_body["query"]


@pytest.mark.asyncio
async def test_get_teams_with_team_filter(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response,
    build_team_dict,
    build_graphql_response,
    build_paginated_response,
):
    """Test team retrieval with name filter"""
    # Create sample team
    team = build_team_dict(name="Engineering Team", key="ENG")

    # Build responses
    teams_response = build_paginated_response([team])
    graphql_data = build_graphql_response({"teams": teams_response})
    http_response = mock_httpx_response(200, graphql_data)
    mock_httpx_client.post.return_value = http_response

    result = await get_teams(context=mock_context, team_name="Engineering")

    assert result["total_count"] == 1
    assert len(result["teams"]) == 1
    assert result["teams"][0]["name"] == "Engineering Team"

    # Verify filter was applied in the request
    call_args = mock_httpx_client.post.call_args
    request_body = call_args[1]["json"]
    assert "variables" in request_body
    assert "filter" in request_body["variables"]


@pytest.mark.asyncio
async def test_get_teams_empty_result(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response,
    build_graphql_response,
    build_paginated_response,
):
    """Test handling of empty teams list"""
    # Build empty response
    teams_response = build_paginated_response([])
    graphql_data = build_graphql_response({"teams": teams_response})
    http_response = mock_httpx_response(200, graphql_data)
    mock_httpx_client.post.return_value = http_response

    result = await get_teams(context=mock_context)

    assert result["total_count"] == 0
    assert len(result["teams"]) == 0


@pytest.mark.asyncio
async def test_get_teams_graphql_error(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response,
):
    """Test handling of GraphQL errors"""
    # Build error response
    error_data = {
        "data": None,
        "errors": [
            {"message": "Authentication required", "extensions": {"code": "UNAUTHENTICATED"}}
        ],
    }
    http_response = mock_httpx_response(200, error_data)
    mock_httpx_client.post.return_value = http_response

    # The tool should raise an exception for GraphQL errors
    with pytest.raises(Exception) as exc_info:
        await get_teams(context=mock_context)

    assert "Authentication required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_teams_http_error(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response,
):
    """Test handling of HTTP errors"""
    # Mock HTTP 401 error
    error_response = mock_httpx_response(401, {"error": "Unauthorized"})
    mock_httpx_client.post.return_value = error_response

    with pytest.raises(Exception) as exc_info:
        await get_teams(context=mock_context)

    # Should contain HTTP status information
    assert "401" in str(exc_info.value) or "Unauthorized" in str(exc_info.value)
