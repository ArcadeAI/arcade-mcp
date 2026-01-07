"""Tests for arcade_core.converters.utils module."""

from arcade_core.converters.utils import denormalize_tool_name, normalize_tool_name


class TestNormalizeToolName:
    """Tests for normalize_tool_name function."""

    def test_simple_dot_notation(self):
        """Test converting simple dot notation to underscores."""
        assert normalize_tool_name("Google.Search") == "Google_Search"

    def test_multiple_dots(self):
        """Test converting multiple dots."""
        assert normalize_tool_name("Namespace.Sub.Tool") == "Namespace_Sub_Tool"

    def test_no_dots(self):
        """Test that names without dots are unchanged."""
        assert normalize_tool_name("MyTool") == "MyTool"

    def test_empty_string(self):
        """Test empty string input."""
        assert normalize_tool_name("") == ""

    def test_underscore_preserved(self):
        """Test that existing underscores are preserved."""
        assert normalize_tool_name("My_Tool.Name") == "My_Tool_Name"

    def test_single_character(self):
        """Test single character names."""
        assert normalize_tool_name("A") == "A"
        assert normalize_tool_name(".") == "_"


class TestDenormalizeToolName:
    """Tests for denormalize_tool_name function."""

    def test_simple_underscore_notation(self):
        """Test converting simple underscore notation to dots."""
        assert denormalize_tool_name("Google_Search") == "Google.Search"

    def test_multiple_underscores(self):
        """Test converting multiple underscores."""
        assert denormalize_tool_name("Namespace_Sub_Tool") == "Namespace.Sub.Tool"

    def test_no_underscores(self):
        """Test that names without underscores are unchanged."""
        assert denormalize_tool_name("MyTool") == "MyTool"

    def test_empty_string(self):
        """Test empty string input."""
        assert denormalize_tool_name("") == ""

    def test_custom_separator(self):
        """Test using a custom separator."""
        assert denormalize_tool_name("Google_Search", separator="::") == "Google::Search"

    def test_single_character(self):
        """Test single character names."""
        assert denormalize_tool_name("A") == "A"
        assert denormalize_tool_name("_") == "."


class TestRoundTrip:
    """Tests for round-trip conversion (normalize then denormalize)."""

    def test_roundtrip_simple(self):
        """Test round-trip for simple names without original underscores."""
        original = "Google.Search"
        normalized = normalize_tool_name(original)
        denormalized = denormalize_tool_name(normalized)
        assert denormalized == original

    def test_roundtrip_multiple_dots(self):
        """Test round-trip for names with multiple dots."""
        original = "Namespace.Sub.Tool"
        normalized = normalize_tool_name(original)
        denormalized = denormalize_tool_name(normalized)
        assert denormalized == original

    def test_roundtrip_with_original_underscores_is_lossy(self):
        """Test that round-trip is lossy when original has underscores.

        This documents the known limitation: if the original name contains
        underscores, denormalization cannot distinguish them from dots.
        """
        original = "My_Tool.Name"
        normalized = normalize_tool_name(original)  # "My_Tool_Name"
        denormalized = denormalize_tool_name(normalized)  # "My.Tool.Name"
        # This is NOT equal to original - expected behavior
        assert denormalized != original
        assert denormalized == "My.Tool.Name"
