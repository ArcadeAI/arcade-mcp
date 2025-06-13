from enum import Enum
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from arcade_tdk.errors import ToolExecutionError

from arcade_confluence.enums import BodyFormat, PageUpdateMode
from arcade_confluence.utils import (
    build_child_url,
    build_hierarchy,
    remove_none_values,
)


class ConfluenceAPIVersion(str, Enum):
    V1 = "wiki/rest/api"
    V2 = "wiki/api/v2"


class ConfluenceClient:
    ACCESSIBLE_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
    BASE_URL = "https://api.atlassian.com/ex/confluence"

    def __init__(self, token: str, api_version: ConfluenceAPIVersion):
        self.token = token
        self.cloud_id = self._get_cloud_id()
        self.api_version = api_version.value

    def _get_cloud_id(self) -> str:
        """
        Fetch the cloudId for <workspace_name>.atlassian.net
        using the OAuth2 3LO accessible-resources endpoint.

        For details on why this is necessary, see: https://developer.atlassian.com/cloud/oauth/getting-started/making-calls-to-api
        """
        headers = {"Authorization": f"Bearer {self.token}"}
        resp = httpx.get(self.ACCESSIBLE_RESOURCES_URL, headers=headers)
        resp.raise_for_status()
        resp_json = resp.json()

        if len(resp_json) == 0:
            raise ToolExecutionError(message="No workspaces found for the authenticated user.")

        return resp_json[0].get("id")  # type: ignore[no-any-return]

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.BASE_URL}/{self.cloud_id}/{self.api_version}/{path.lstrip('/')}",
                headers=headers,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()

    async def get(self, path: str, **kwargs: Any) -> Any:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Any:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> Any:
        return await self.request("PUT", path, **kwargs)


class ConfluenceClientV1(ConfluenceClient):
    def __init__(self, token: str):
        super().__init__(token, api_version=ConfluenceAPIVersion.V1)

    def _build_query_cql(self, query: str, enable_fuzzy: bool) -> str:
        """Build CQL for a single query (term or phrase).

        Args:
            query: The search query (single word term or multi-word phrase)
            enable_fuzzy: Whether to enable fuzzy matching for single terms

        Returns:
            CQL string for the query
        """
        query = query.strip()
        if not query:
            return ""

        # For phrases (multiple words), don't use fuzzy matching
        if " " in query:
            return f'(text ~ "{query}" OR title ~ "{query}" OR space.title ~ "{query}")'
        else:
            # For single terms, optionally use fuzzy matching
            term_suffix = "~" if enable_fuzzy else ""
            return f'(text ~ "{query}{term_suffix}" OR title ~ "{query}{term_suffix}" OR space.title ~ "{query}{term_suffix}")'  # noqa: E501

    def _build_and_cql(self, queries: list[str], enable_fuzzy: bool) -> str:
        """Build CQL for queries that must ALL be present (AND logic).

        Args:
            queries: List of queries that must all be present
            enable_fuzzy: Whether to enable fuzzy matching for single terms

        Returns:
            CQL string with AND logic
        """
        and_parts = []
        for query in queries:
            query_cql = self._build_query_cql(query, enable_fuzzy)
            if query_cql:
                and_parts.append(query_cql)

        if not and_parts:
            return ""

        return f"({' AND '.join(and_parts)})"

    def _build_or_cql(self, queries: list[str], enable_fuzzy: bool) -> str:
        """Build CQL for queries where ANY can be present (OR logic).

        Args:
            queries: List of queries where any can be present
            enable_fuzzy: Whether to enable fuzzy matching for single terms

        Returns:
            CQL string with OR logic
        """
        or_parts = []
        for query in queries:
            query_cql = self._build_query_cql(query, enable_fuzzy)
            if query_cql:
                or_parts.append(query_cql)

        if not or_parts:
            return ""

        return f"({' OR '.join(or_parts)})"

    def construct_cql(
        self,
        must_contain_all: list[str] | None,
        can_contain_any: list[str] | None,
        enable_fuzzy: bool = False,
    ) -> str:
        """Construct CQL query with AND/OR logic.

        Learn about advanced searching using CQL here: https://developer.atlassian.com/cloud/confluence/advanced-searching-using-cql/

        Args:
            must_contain_all: Queries that must ALL be present (AND logic)
            can_contain_any: Queries where ANY can be present (OR logic)
            enable_fuzzy: Whether to enable fuzzy matching for single terms

        Returns:
            CQL query string

        Raises:
            ToolExecutionError: If no search parameters are provided
        """
        cql_parts = []

        # Handle must_contain_all (AND logic)
        if must_contain_all:
            and_cql = self._build_and_cql(must_contain_all, enable_fuzzy)
            if and_cql:
                cql_parts.append(and_cql)

        # Handle can_contain_any (OR logic)
        if can_contain_any:
            or_cql = self._build_or_cql(can_contain_any, enable_fuzzy)
            if or_cql:
                cql_parts.append(or_cql)

        # If there's only one part, return it
        if len(cql_parts) == 1:
            return cql_parts[0]

        # AND the must_contain_all with the can_contain_any
        if len(cql_parts) > 1:
            return f"({' AND '.join(cql_parts)})"

        raise ToolExecutionError(message="At least one search parameter must be provided")

    def transform_search_content_response(
        self, response: dict[str, Any]
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Transform the response from the GET /search endpoint by converting relative webui paths
        to absolute URLs using the base URL from the response.
        """
        base_url = response.get("_links", {}).get("base", "")
        transformed_results = []
        for result in response.get("results", []):
            content = result.get("content", {})
            transformed_result = {
                "id": content.get("id"),
                "title": content.get("title"),
                "type": content.get("type"),
                "status": content.get("status"),
                "excerpt": result.get("excerpt"),
                "url": f"{base_url}{result.get('url')}",
            }
            transformed_results.append(transformed_result)

        return {"results": transformed_results}


class ConfluenceClientV2(ConfluenceClient):
    def __init__(self, token: str):
        super().__init__(token, api_version=ConfluenceAPIVersion.V2)

    def _transform_links(
        self, response: dict[str, Any], base_url: str | None = None
    ) -> dict[str, Any]:
        """
        Transform the links in a page response by converting relative URLs to absolute URLs.

        Args:
            response: A page object from the API
            base_url: The base URL to use for the transformation

        Returns:
            The transformed response
        """
        result = response.copy()
        if "_links" in result:
            base_url = base_url or result["_links"].get("base", "")
            webui_path = result["_links"].get("webui", "")
            result["url"] = f"{base_url}{webui_path}"
            del result["_links"]
        return result

    def transform_get_spaces_response(
        self, response: dict[str, Any]
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Transform the response from the GET /spaces endpoint by converting relative webui paths
        to absolute URLs using the base URL from the response.
        """
        pagination_token = parse_qs(urlparse(response.get("_links", {}).get("next", "")).query).get(
            "cursor",
            [None],  # type: ignore[list-item]
        )[0]

        base_url = response.get("_links", {}).get("base", "")
        results = response.get("results", [])

        transformed_results = []
        for space in results:
            space_copy = space.copy()
            if "_links" in space_copy and "webui" in space_copy["_links"]:
                webui_path = space_copy["_links"]["webui"]
                space_copy["url"] = base_url + webui_path
                del space_copy["_links"]
            transformed_results.append(space_copy)

        results = {"spaces": transformed_results, "pagination_token": pagination_token}
        return remove_none_values(results)

    def transform_list_pages_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Transform the response from the GET /pages endpoint."""
        pagination_token = parse_qs(urlparse(response.get("_links", {}).get("next", "")).query).get(
            "cursor",
            [None],  # type: ignore[list-item]
        )[0]

        base_url = response.get("_links", {}).get("base", "")
        pages = [self._transform_links(page, base_url) for page in response["results"]]
        results = {"pages": pages, "pagination_token": pagination_token}
        return remove_none_values(results)

    def transform_get_multiple_pages_response(
        self, response: dict[str, Any]
    ) -> dict[str, list[dict[str, Any]]]:
        """Transform the response from the GET /pages endpoint."""
        base_url = response.get("_links", {}).get("base", "")
        pages = [self._transform_links(page, base_url) for page in response["results"]]
        return {"pages": pages}

    def transform_space_response(
        self, response: dict[str, Any], base_url: str | None = None
    ) -> dict[str, dict[str, Any]]:
        """Transform API responses that return a space object."""
        return {"space": self._transform_links(response, base_url)}

    def transform_page_response(self, response: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Transform API responses that return a page object."""
        return {"page": self._transform_links(response)}

    def transform_get_attachments_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Transform the response from the GET /pages/{id}/attachments endpoint."""
        pagination_token = parse_qs(urlparse(response.get("_links", {}).get("next", "")).query).get(
            "cursor",
            [None],  # type: ignore[list-item]
        )[0]

        base_url = response.get("_links", {}).get("base", "")
        attachments = []
        for attachment in response["results"]:
            result = attachment.copy()
            if "_links" in result:
                webui_path = result["_links"].get("webui", "")
                download_path = result["_links"].get("download", "")
                result["url"] = f"{base_url}{webui_path}"
                result["download_link"] = f"{base_url}{download_path}"
                del result["_links"]
                del result["webuiLink"]
                del result["downloadLink"]
                del result["version"]
            attachments.append(result)

        return {"attachments": attachments, "pagination_token": pagination_token}

    def prepare_update_page_payload(
        self,
        page_id: str,
        status: str,
        title: str,
        body_representation: str,
        body_value: str,
        version_number: int,
        version_message: str,
    ) -> dict[str, Any]:
        """Prepare a payload for the PUT /pages/{id} endpoint."""
        return {
            "id": page_id,
            "status": status,
            "title": title,
            "body": {
                "representation": body_representation,
                "value": body_value,
            },
            "version": {
                "number": version_number,
                "message": version_message,
            },
        }

    def prepare_update_page_content_payload(
        self,
        content: str,
        update_mode: PageUpdateMode,
        old_content: str,
        page_id: str,
        status: str,
        title: str,
        body_representation: BodyFormat,
        old_version_number: int,
    ) -> dict[str, Any]:
        """Prepare a payload for when updating the content of a page

        Args:
            content: The content to update the page with
            update_mode: The mode of update to use
            old_content: The content of the page before the update
            page_id: The ID of the page to update
            status: The status of the page
            title: The title of the page
            body_representation: The format that the body (content) is in
            old_version_number: The version number of the page before the update

        Returns:
            A payload for the PUT /pages/{id} endpoint's json body
        """
        updated_content = ""
        updated_message = ""
        if update_mode == PageUpdateMode.APPEND:
            updated_content = f"{old_content}<br/>{content}"
            updated_message = "Append content to the page"
        elif update_mode == PageUpdateMode.PREPEND:
            updated_content = f"{content}<br/>{old_content}"
            updated_message = "Prepend content to the page"
        elif update_mode == PageUpdateMode.REPLACE:
            updated_content = content
            updated_message = "Replace the page content"
        payload = self.prepare_update_page_payload(
            page_id=page_id,
            status=status,
            title=title,
            body_representation=body_representation.to_api_value(),
            body_value=updated_content,
            version_number=old_version_number + 1,
            version_message=updated_message,
        )
        return payload

    async def get_root_pages_in_space(self, space_id: str) -> dict[str, Any]:
        """
        Get the root pages in a space.

        Requires Confluence scope 'read:page:confluence'
        """
        params = {
            "depth": "root",
            "limit": 250,
        }
        pages = await self.get(f"spaces/{space_id}/pages", params=params)
        base_url = pages.get("_links", {}).get("base", "")
        return {"pages": [self._transform_links(page, base_url) for page in pages["results"]]}

    async def get_space_homepage(self, space_id: str) -> dict[str, Any]:
        """
        Get the homepage of a space.

        Requires Confluence scope 'read:page:confluence'
        """
        root_pages = await self.get_root_pages_in_space(space_id)
        for page in root_pages["pages"]:
            if page.get("url", "").endswith("overview"):
                return self._transform_links(page)
        raise ToolExecutionError(message="No homepage found for space.")

    async def get_page_by_id(
        self, page_id: str, content_format: BodyFormat = BodyFormat.STORAGE
    ) -> dict[str, Any]:
        """Get a page by its ID.

        Requires Confluence scope 'read:page:confluence'

        Args:
            page_id: The ID of the page to get
            content_format: The format of the page content

        Returns:
            The page object
        """
        params = remove_none_values({
            "body-format": content_format.to_api_value(),
        })
        try:
            page = await self.get(f"pages/{page_id}", params=params)
        except httpx.HTTPStatusError as e:
            # If the page is not found, return an empty page object
            if e.response.status_code in [400, 404]:
                return self.transform_page_response({})
            raise

        return self.transform_page_response(page)

    async def get_page_by_title(
        self, page_title: str, content_format: BodyFormat = BodyFormat.STORAGE
    ) -> dict[str, Any]:
        """Get a page by its title.

        Requires Confluence scope 'read:page:confluence'

        Args:
            page_title: The title of the page to get
            content_format: The format of the page content

        Returns:
            The page object
        """
        params = {
            "title": page_title,
            "body-format": content_format.to_api_value(),
        }
        response = await self.get("pages", params=params)
        pages = response.get("results", [])
        if not pages:
            # If the page is not found, return an empty page object
            return self.transform_page_response({})
        return self.transform_page_response(pages[0])

    async def get_space_by_id(self, space_id: str) -> dict[str, Any]:
        """Get a space by its ID.

        Requires Confluence scope 'read:space:confluence'

        Args:
            space_id: The ID of the space to get

        Returns:
            The space object
        """
        space = await self.get(f"spaces/{space_id}")
        return self.transform_space_response(space)

    async def get_space_by_key(self, space_key: str) -> dict[str, Any]:
        """Get a space by its key.

        Requires Confluence scope 'read:space:confluence'

        Args:
            space_key: The key of the space to get

        Returns:
            The space object
        """
        response = await self.get("spaces", params={"keys": [space_key]})
        base_url = response.get("_links", {}).get("base", "")
        spaces = response.get("results", [])
        if not spaces:
            raise ToolExecutionError(message=f"No space found with key: '{space_key}'")
        return self.transform_space_response(spaces[0], base_url=base_url)

    async def get_space(self, space_identifier: str) -> dict[str, Any]:
        """Get a space from its identifier.

        Requires Confluence scope 'read:space:confluence'

        Args:
            space_identifier: The identifier of the space to get. Can be a space's ID or key.
        """
        return (
            await self.get_space_by_id(space_identifier)
            if space_identifier.isdigit()
            else await self.get_space_by_key(space_identifier)
        )

    async def get_page_id(self, page_identifier: str) -> str:
        """Get the ID of a page from its identifier.

        Args:
            page_identifier: The identifier of the page to get. Can be a page's ID or title.

        Returns:
            The ID of the page
        """
        if page_identifier.isdigit():
            page_id = page_identifier
        else:
            page = await self.get_page_by_title(page_identifier)
            page_id = page.get("page", {}).get("id")

        if not page_id:
            raise ToolExecutionError(message=f"No page found with identifier: '{page_identifier}'")

        return page_id

    async def get_space_id(self, space_identifier: str) -> str:
        """Get the ID of a space from its identifier.

        Args:
            space_identifier: The identifier of the space to get. Can be a space's ID or title.
        """
        if space_identifier.isdigit():
            space_id = space_identifier
        else:
            space = await self.get_space_by_key(space_identifier)
            space_id = space.get("space", {}).get("id")
        return space_id

    def create_space_tree(self, space: dict) -> dict:
        """Create the initial tree structure for a space.

        Args:
            space: The transformed space object

        Returns:
            A dictionary representing the root of the space hierarchy tree without any children
        """
        space_internal = space.get("space", {})
        return {
            "key": space_internal.get("key"),
            "id": space_internal.get("id"),
            "type": "space",
            "url": space_internal.get("url"),
            "children": [],
        }

    def convert_root_pages_to_tree_nodes(self, pages: list) -> list:
        """Convert root pages of a space to tree nodes.

        Args:
            pages: List of page objects from the API

        Returns:
            A list of tree nodes representing the root pages
        """
        return [
            {
                "title": page.get("title"),
                "id": page.get("id"),
                "type": "page",
                "url": page.get("url"),
                "children": [],
            }
            for page in pages
        ]

    async def process_page_descendants(self, root_children: list, base_url: str) -> None:
        """Process descendants for each page and build the hierarchy.

        Args:
            root_children: The root children of the space
            base_url: The base URL for the Confluence space

        Returns:
            None (modifies root_children in place)
        """
        descendent_params = {"limit": 250, "depth": 5}

        for i, child in enumerate(root_children):
            page_id = child["id"]
            descendants = await self.get(f"pages/{page_id}/descendants", params=descendent_params)

            # Transform descendants into our desired format
            transformed_children = []
            for descendant in descendants.get("results", []):
                transformed_child = {
                    "title": descendant.get("title"),
                    "id": descendant.get("id"),
                    "type": descendant.get("type"),
                    "parent_id": page_id
                    if descendant.get("parentId") is None
                    else descendant.get("parentId"),
                    "parent_type": descendant.get("parentType", "TODO"),
                    "url": build_child_url(base_url, descendant),
                    "children": [],
                    "status": descendant.get("status"),
                }
                transformed_children.append(transformed_child)

            # Build the hierarchy for the current root page
            build_hierarchy(transformed_children, page_id, root_children[i])
