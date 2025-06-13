import pytest
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_confluence.utils import build_child_url, build_hierarchy, validate_ids


@pytest.mark.parametrize(
    "ids, max_length, expected_error",
    [
        (None, 250, None),
        (["123", "456"], 250, None),
        (["123", "foo"], 250, ToolExecutionError),
        (["123", "456"], 1, RetryableToolError),
    ],
)
def test_validate_ids(ids: list[str], max_length: int, expected_error: Exception | None) -> None:
    if expected_error:
        with pytest.raises(expected_error):
            validate_ids(ids, max_length)
    else:
        validate_ids(ids, max_length)


@pytest.mark.parametrize(
    "base_url, child, expected",
    [
        (  # Published page
            "https://tes.atlassian.net/wiki/spaces/SOFTWAREDEVELOPMENT",
            {"type": "page", "title": "Test Title-1", "id": "123", "status": "current"},
            "https://tes.atlassian.net/wiki/spaces/SOFTWAREDEVELOPMENT/pages/123/Test+Title-1",
        ),
        (  # Draft page
            "https://tes.atlassian.net/wiki/spaces/SOFTWAREDEVELOPMENT",
            {"type": "page", "title": "Test Title-1", "id": "123", "status": "draft"},
            "https://tes.atlassian.net/wiki/spaces/SOFTWAREDEVELOPMENT/pages/edit-v2/123",
        ),
        (  # Whiteboard
            "https://tes.atlassian.net/wiki/spaces/SOFTWAREDEVELOPMENT",
            {"type": "whiteboard", "title": "Test Title-1", "id": "123", "status": "current"},
            "https://tes.atlassian.net/wiki/spaces/SOFTWAREDEVELOPMENT/whiteboard/123",
        ),
        (  # Database
            "https://tes.atlassian.net/wiki/spaces/SOFTWAREDEVELOPMENT",
            {"type": "database", "title": "Test Title-1", "id": "123", "status": "current"},
            "https://tes.atlassian.net/wiki/spaces/SOFTWAREDEVELOPMENT/database/123",
        ),
        (  # Embed
            "https://tes.atlassian.net/wiki/spaces/SOFTWAREDEVELOPMENT",
            {"type": "embed", "title": "Test Title-1", "id": "123", "status": "current"},
            "https://tes.atlassian.net/wiki/spaces/SOFTWAREDEVELOPMENT/embed/123",
        ),
        (  # Folder
            "https://tes.atlassian.net/wiki/spaces/SOFTWAREDEVELOPMENT",
            {"type": "folder", "title": "Test Title-1", "id": "123", "status": "current"},
            None,  # Folders don't have URLs
        ),
    ],
)
def test_build_child_url(base_url: str, child: dict, expected: str) -> None:
    assert build_child_url(base_url, child) == expected


@pytest.mark.parametrize(
    "input_transformed_children, input_parent_id, input_parent_node, expected_parent_node",
    [
        (  # Parent node is a leaf
            [],
            "2195457",
            {
                "title": "A One Sentence Story About Trees",
                "id": "2195457",
                "type": "page",
                "url": "https://ericconfluence.atlassian.net/wiki/spaces/SOFTWAREDE/pages/2195457/A+One+Sentence+Story+About+Trees",
                "children": [],
            },
            {
                "title": "A One Sentence Story About Trees",
                "id": "2195457",
                "type": "page",
                "url": "https://ericconfluence.atlassian.net/wiki/spaces/SOFTWAREDE/pages/2195457/A+One+Sentence+Story+About+Trees",
                "children": [],
            },
        ),
        (
            [
                {
                    "title": "The Importance of Trees",
                    "id": "2555906",
                    "type": "page",
                    "parent_id": "2162740",
                    "parent_type": "TODO",
                    "url": "https://ericconfluence.atlassian.net/wiki/spaces/SOFTWAREDE/pages/2555906/The+Importance+of+Trees",
                    "children": [],
                    "status": "current",
                },
                {
                    "title": "Erics page",
                    "id": "2686977",
                    "type": "page",
                    "parent_id": "2555906",
                    "parent_type": "TODO",
                    "url": "https://ericconfluence.atlassian.net/wiki/spaces/SOFTWAREDE/pages/2686977/Erics+page",
                    "children": [],
                    "status": "current",
                },
                {
                    "title": "Erics page",
                    "id": "2719745",
                    "type": "page",
                    "parent_id": "2555906",
                    "parent_type": "TODO",
                    "url": "https://ericconfluence.atlassian.net/wiki/spaces/SOFTWAREDE/pages/edit-v2/2719745",
                    "children": [],
                    "status": "draft",
                },
                {
                    "title": "Execute tools",
                    "id": "2621441",
                    "type": "page",
                    "parent_id": "2162740",
                    "parent_type": "TODO",
                    "url": "https://ericconfluence.atlassian.net/wiki/spaces/SOFTWAREDE/pages/2621441/Execute+tools",
                    "children": [],
                    "status": "current",
                },
            ],
            "2162740",
            {
                "title": "Trees",
                "id": "2162740",
                "type": "page",
                "url": "https://ericconfluence.atlassian.net/wiki/spaces/SOFTWAREDE/pages/2162740/Trees",
                "children": [],
            },
            {
                "title": "Trees",
                "id": "2162740",
                "type": "page",
                "url": "https://ericconfluence.atlassian.net/wiki/spaces/SOFTWAREDE/pages/2162740/Trees",
                "children": [
                    {
                        "title": "The Importance of Trees",
                        "id": "2555906",
                        "type": "page",
                        "parent_id": "2162740",
                        "parent_type": "TODO",
                        "url": "https://ericconfluence.atlassian.net/wiki/spaces/SOFTWAREDE/pages/2555906/The+Importance+of+Trees",
                        "children": [
                            {
                                "title": "Erics page",
                                "id": "2686977",
                                "type": "page",
                                "parent_id": "2555906",
                                "parent_type": "TODO",
                                "url": "https://ericconfluence.atlassian.net/wiki/spaces/SOFTWAREDE/pages/2686977/Erics+page",
                                "children": [],
                                "status": "current",
                            },
                            {
                                "title": "Erics page",
                                "id": "2719745",
                                "type": "page",
                                "parent_id": "2555906",
                                "parent_type": "TODO",
                                "url": "https://ericconfluence.atlassian.net/wiki/spaces/SOFTWAREDE/pages/edit-v2/2719745",
                                "children": [],
                                "status": "draft",
                            },
                        ],
                        "status": "current",
                    },
                    {
                        "title": "Execute tools",
                        "id": "2621441",
                        "type": "page",
                        "parent_id": "2162740",
                        "parent_type": "TODO",
                        "url": "https://ericconfluence.atlassian.net/wiki/spaces/SOFTWAREDE/pages/2621441/Execute+tools",
                        "children": [],
                        "status": "current",
                    },
                ],
            },
        ),
    ],
)
def test_build_hierarchy(
    input_transformed_children: list[dict],
    input_parent_id: int,
    input_parent_node: dict,
    expected_parent_node: dict,
) -> None:
    # build_hierarchy modifies the input_parent_node in-place
    build_hierarchy(input_transformed_children, input_parent_id, input_parent_node)
    assert input_parent_node == expected_parent_node
