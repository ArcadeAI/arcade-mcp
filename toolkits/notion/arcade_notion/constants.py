NOTION_API_URL = "https://api.notion.com/v1"


ENDPOINTS = {
    "create_a_page": "/pages",
    "retrieve_block_children": "/blocks/{block_id}/children",
    "search_by_title": "/search",
    "query_a_database": "/databases/{database_id}/query",
    "update_page_properties": "/pages/{page_id}",
    "append_block_children": "/blocks/{block_id}/children",
    "retrieve_a_database": "/databases/{database_id}",
    "create_comment": "/comments",
    "retrieve_a_page": "/pages/{page_id}",
    "retrieve_a_block": "/blocks/{block_id}",
}

UNTITLED_TITLE = "New Page"
