def remove_none_values(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not None}


def inject_pagination_in_tool_response(response: dict, page: int) -> dict:
    if "next_page" not in response:
        return response

    response["pagination"] = {
        "current_page": page,
        "next_page": page + 1 if "next_page" in response else None,
    }

    del response["next_page"]

    return response
