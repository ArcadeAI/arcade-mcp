from dataclasses import asdict, dataclass, field


# ------------------------------------------------------
#  Parent types.
#  See Notion API docs for more information:
#  https://developers.notion.com/reference/parent-object
# ------------------------------------------------------
@dataclass
class Parent:
    type: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DatabaseParent(Parent):
    database_id: str
    type: str = field(init=False, default="database_id")


@dataclass
class PageParent(Parent):
    page_id: str
    type: str = field(init=False, default="page_id")


@dataclass
class WorkspaceParent(Parent):
    workspace: bool = True
    type: str = field(init=False, default="workspace")


@dataclass
class BlockParent(Parent):
    block_id: str
    type: str = field(init=False, default="block_id")


def create_parent(parent_data: dict) -> Parent:
    """
    Create a parent object from a dictionary.

    See https://developers.notion.com/reference/parent-object for more information
    about the parent object.

    Args:
        parent_data (dict): The dictionary containing the parent data.

    Returns:
        Parent: The parent object.
    """
    parent_type = parent_data.get("type")
    if parent_type == "database_id":
        return DatabaseParent(database_id=parent_data.get("database_id", ""))
    elif parent_type == "page_id":
        return PageParent(page_id=parent_data.get("page_id", ""))
    elif parent_type == "workspace":
        return WorkspaceParent()
    elif parent_type == "block_id":
        return BlockParent(block_id=parent_data.get("block_id", ""))
    else:
        raise ValueError(f"Unknown parent type: {parent_type}")  # noqa: TRY003


# ------------------------------------------------------
#  Property types.
#  See Notion API docs for more information:
#  https://developers.notion.com/reference/property-object
#  and https://developers.notion.com/reference/page-property-values
# ------------------------------------------------------


@dataclass
class PageWithPageParentProperties:
    """Properties for a page that has a parent that is also a page"""

    title: str

    def to_dict(self) -> dict:
        return {
            "title": {
                "title": [
                    {
                        "type": "text",
                        "text": {
                            "content": self.title,
                        },
                    },
                ],
            },
        }


@dataclass
class PageWithDatabaseParentProperties:
    # TODO: Implement when database parent is supported for `create_page` tool
    pass


@dataclass
class DatabaseProperties:
    # TODO: Implement when create_database tool is implemented
    pass
