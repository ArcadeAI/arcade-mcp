"""Tests for Resource Manager implementation."""

import asyncio

import pytest
from arcade_mcp_server.exceptions import NotFoundError
from arcade_mcp_server.managers.resource import ResourceManager
from arcade_mcp_server.types import (
    BlobResourceContents,
    Resource,
    ResourceContents,
    ResourceTemplate,
    TextResourceContents,
)


class TestResourceManager:
    """Test ResourceManager class."""

    @pytest.fixture
    def resource_manager(self):
        """Create a resource manager instance."""
        return ResourceManager()

    @pytest.fixture
    def sample_resource(self):
        """Create a sample resource."""
        return Resource(
            uri="file:///test.txt",
            name="test.txt",
            description="A test text file",
            mimeType="text/plain",
        )

    @pytest.fixture
    def sample_template(self):
        """Create a sample resource template."""
        return ResourceTemplate(
            uriTemplate="file:///{path}",
            name="File Template",
            description="Template for file resources",
            mimeType="text/plain",
        )

    def test_manager_initialization(self):
        """Test resource manager initialization."""
        manager = ResourceManager()
        # Passive manager: no started flag
        assert isinstance(manager, ResourceManager)

    @pytest.mark.asyncio
    async def test_manager_lifecycle(self, resource_manager):
        """Passive manager has no explicit lifecycle; ensure methods work."""
        resources = await resource_manager.list_resources()
        assert resources == []

    @pytest.mark.asyncio
    async def test_add_resource(self, resource_manager, sample_resource):
        """Test adding resources."""
        await resource_manager.add_resource(sample_resource)

        resources = await resource_manager.list_resources()
        assert len(resources) == 1
        assert resources[0].uri == sample_resource.uri

    @pytest.mark.asyncio
    async def test_remove_resource(self, resource_manager, sample_resource):
        """Test removing resources."""
        await resource_manager.add_resource(sample_resource)
        removed = await resource_manager.remove_resource(sample_resource.uri)
        assert removed.uri == sample_resource.uri

        resources = await resource_manager.list_resources()
        assert len(resources) == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent_resource(self, resource_manager):
        """Test removing non-existent resource."""
        with pytest.raises(NotFoundError):
            await resource_manager.remove_resource("file:///nonexistent.txt")

    @pytest.mark.asyncio
    async def test_add_resource_template(self, resource_manager, sample_template):
        """Test adding resource templates."""
        await resource_manager.add_template(sample_template)

        templates = await resource_manager.list_resource_templates()
        assert len(templates) == 1
        assert templates[0].uriTemplate == sample_template.uriTemplate

    @pytest.mark.asyncio
    async def test_resource_handlers(self, resource_manager):
        """Test adding and using resource handlers."""
        resource = Resource(
            uri="custom://test", name="Custom Resource", description="Resource with custom handler"
        )

        async def custom_handler(uri: str) -> list[ResourceContents]:
            return [
                TextResourceContents(
                    uri=uri, text="Custom content for " + uri, mimeType="text/plain"
                )
            ]

        await resource_manager.add_resource(resource, handler=custom_handler)

        contents = await resource_manager.read_resource("custom://test")

        assert len(contents) == 1
        assert contents[0].text == "Custom content for custom://test"

    @pytest.mark.asyncio
    async def test_read_resource_without_handler(self, resource_manager, sample_resource):
        """Test reading resource without a handler returns default content."""
        await resource_manager.add_resource(sample_resource)

        contents = await resource_manager.read_resource(sample_resource.uri)
        assert len(contents) == 1
        assert contents[0].uri == sample_resource.uri

    @pytest.mark.asyncio
    async def test_read_nonexistent_resource(self, resource_manager):
        """Test reading non-existent resource."""
        with pytest.raises(NotFoundError):
            await resource_manager.read_resource("file:///nonexistent.txt")

    @pytest.mark.asyncio
    async def test_binary_resource_content(self, resource_manager):
        """Test handling binary resource content."""
        resource = Resource(uri="file:///image.png", name="image.png", mimeType="image/png")

        async def image_handler(uri: str) -> list[ResourceContents]:
            import base64

            png_data = base64.b64encode(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
            ).decode()
            return [BlobResourceContents(uri=uri, blob=png_data, mimeType="image/png")]

        await resource_manager.add_resource(resource, handler=image_handler)

        contents = await resource_manager.read_resource("file:///image.png")

        assert len(contents) == 1
        assert isinstance(contents[0], BlobResourceContents)
        assert contents[0].mimeType == "image/png"

    @pytest.mark.asyncio
    async def test_multiple_resource_contents(self, resource_manager):
        """Test resources that return multiple contents."""
        resource = Resource(uri="multi://resource", name="Multi Resource")

        async def multi_handler(uri: str) -> list[ResourceContents]:
            return [
                TextResourceContents(uri=uri + "#part1", text="Part 1"),
                TextResourceContents(uri=uri + "#part2", text="Part 2"),
                BlobResourceContents(uri=uri + "#data", blob="YmluYXJ5"),
            ]

        await resource_manager.add_resource(resource, handler=multi_handler)

        contents = await resource_manager.read_resource("multi://resource")

        assert len(contents) == 3
        assert contents[0].text == "Part 1"
        assert contents[1].text == "Part 2"
        assert contents[2].blob == "YmluYXJ5"

    @pytest.mark.asyncio
    async def test_concurrent_resource_operations(self, resource_manager):
        """Test concurrent resource operations."""
        # Create multiple resources
        resources = []
        for i in range(10):
            resource = Resource(
                uri=f"file:///{i}.txt", name=f"File {i}", description=f"Test file {i}"
            )
            resources.append(resource)

        tasks = [resource_manager.add_resource(r) for r in resources]
        await asyncio.gather(*tasks)

        listed = await resource_manager.list_resources()
        assert len(listed) == 10

    @pytest.mark.asyncio
    async def test_list_resources_and_templates_initial(self):
        """Passive manager lists resources/templates initially as empty."""
        manager = ResourceManager()
        resources = await manager.list_resources()
        assert resources == []
        templates = await manager.list_resource_templates()
        assert templates == []
