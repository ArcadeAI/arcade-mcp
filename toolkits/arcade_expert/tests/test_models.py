from arcade_arcade_expert.models import Links


def test_links_initialization():
    # Test that Links can be initialized with a list of links
    links = Links(links=["https://example.com", "https://test.com"])
    assert links.links == ["https://example.com", "https://test.com"]


def test_validate_links():
    # Test that validate_links removes invalid URLs
    links = Links(links=["https://example.com", "not-a-valid-url", "https://test.com"])
    links.validate_links()
    assert links.links == ["https://example.com", "https://test.com"]


def test_validate_links_empty():
    # Test with empty list
    links = Links(links=[])
    links.validate_links()
    assert links.links == []


def test_validate_links_all_invalid():
    # Test with all invalid links
    links = Links(links=["not-valid-1", "not-valid-2"])
    links.validate_links()
    assert links.links == []
