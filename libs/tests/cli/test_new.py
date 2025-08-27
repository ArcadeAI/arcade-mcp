# import re
# from pathlib import Path
# from unittest.mock import MagicMock, patch

# import pytest
# from arcade_cli.new import (
#     create_ignore_pattern,
#     create_new_toolkit,
#     create_package,
#     render_template,
# )
# from jinja2 import DictLoader, Environment


# class TestToolkitNaming:
#     """Test the toolkit naming logic for community vs non-community toolkits."""

#     @patch("arcade_cli.new.Path.cwd")
#     @patch("arcade_cli.new.ask_yes_no_question")
#     @patch("arcade_cli.new.ask_question")
#     @patch("arcade_cli.new.create_package")
#     @patch("arcade_cli.new.console")
#     def test_community_toolkit_adds_arcade_prefix(
#         self, mock_console, mock_create_package, mock_ask, mock_ask_yn, mock_cwd
#     ):
#         """Test that community toolkits get the arcade_ prefix."""
#         # Setup mocks
#         mock_cwd.return_value = Path("/some/path/arcade-ai/toolkits")
#         mock_ask_yn.return_value = True  # Yes, it's a community toolkit
#         mock_ask.side_effect = [
#             "Test description",  # toolkit_description
#             "Test Author",  # toolkit_author_name
#             "test@email.com",  # toolkit_author_email
#             "n",  # include_evals
#         ]

#         with patch("arcade_cli.new.Path.exists", return_value=False):
#             with patch("arcade_cli.new.FileSystemLoader"):
#                 with patch("arcade_cli.new.Environment") as mock_env:
#                     # Capture the context passed to create_package
#                     create_new_toolkit("/output", "mytest")

#                     # Verify the context has arcade_ prefix for package_name
#                     call_args = mock_create_package.call_args
#                     context = call_args[0][3]  # 4th argument is context
#                     assert context["package_name"] == "arcade_mytest"
#                     assert context["toolkit_name"] == "mytest"
#                     assert context["community_toolkit"] is True

#     @patch("arcade_cli.new.Path.cwd")
#     @patch("arcade_cli.new.ask_yes_no_question")
#     @patch("arcade_cli.new.ask_question")
#     @patch("arcade_cli.new.create_package")
#     @patch("arcade_cli.new.console")
#     def test_non_community_toolkit_no_prefix(
#         self, mock_console, mock_create_package, mock_ask, mock_ask_yn, mock_cwd
#     ):
#         """Test that non-community toolkits don't get the arcade_ prefix."""
#         # Setup mocks - different path, not in arcade-ai/toolkits
#         mock_cwd.return_value = Path("/some/other/path")
#         mock_ask.side_effect = [
#             "Test description",  # toolkit_description
#             "Test Author",  # toolkit_author_name
#             "test@email.com",  # toolkit_author_email
#             "n",  # include_evals
#         ]

#         with patch("arcade_cli.new.Path.exists", return_value=False):
#             with patch("arcade_cli.new.FileSystemLoader"):
#                 with patch("arcade_cli.new.Environment") as mock_env:
#                     # Create toolkit - should not prompt for community since not in arcade-ai/toolkits
#                     create_new_toolkit("/output", "mytest")

#                     # Verify ask_yes_no_question was not called
#                     mock_ask_yn.assert_not_called()

#                     # Verify the context has no arcade_ prefix
#                     call_args = mock_create_package.call_args
#                     context = call_args[0][3]  # 4th argument is context
#                     assert context["package_name"] == "mytest"
#                     assert context["toolkit_name"] == "mytest"
#                     assert context["community_toolkit"] is False

#     @patch("arcade_cli.new.Path.cwd")
#     @patch("arcade_cli.new.ask_yes_no_question")
#     @patch("arcade_cli.new.ask_question")
#     @patch("arcade_cli.new.create_package")
#     @patch("arcade_cli.new.console")
#     def test_community_toolkit_prompt_no(
#         self, mock_console, mock_create_package, mock_ask, mock_ask_yn, mock_cwd
#     ):
#         """Test that answering 'no' to community prompt doesn't add prefix."""
#         # Setup mocks
#         mock_cwd.return_value = Path("/some/path/arcade-ai/toolkits")
#         mock_ask_yn.return_value = False  # No, it's not a community toolkit
#         mock_ask.side_effect = [
#             "Test description",  # toolkit_description
#             "Test Author",  # toolkit_author_name
#             "test@email.com",  # toolkit_author_email
#             "n",  # include_evals
#         ]

#         with patch("arcade_cli.new.Path.exists", return_value=False):
#             with patch("arcade_cli.new.FileSystemLoader"):
#                 with patch("arcade_cli.new.Environment") as mock_env:
#                     create_new_toolkit("/output", "mytest")

#                     # Verify the context has no arcade_ prefix when user says no
#                     call_args = mock_create_package.call_args
#                     context = call_args[0][3]  # 4th argument is context
#                     assert context["package_name"] == "mytest"
#                     assert context["toolkit_name"] == "mytest"
#                     assert context["community_toolkit"] is False


# class TestIgnorePatterns:
#     """Test the ignore pattern creation logic."""

#     def test_ignore_pattern_with_evals_and_community(self):
#         """Test ignore patterns for community toolkit with evals."""
#         pattern = create_ignore_pattern(include_evals=True, community_toolkit=True)

#         # Should not match evals directory when include_evals is True
#         assert not pattern.match("evals")
#         assert not pattern.match("test_hello.py")

#         # Should match standard files
#         assert pattern.match(".gitignore")
#         assert pattern.match(".ruff.toml")
#         assert pattern.match(".pre-commit-config.yaml")
#         assert pattern.match("README.md")

#     def test_ignore_pattern_without_evals(self):
#         """Test ignore patterns without evals."""
#         pattern = create_ignore_pattern(include_evals=False, community_toolkit=False)

#         # Should match evals directory when include_evals is False
#         assert pattern.match("evals")
#         assert pattern.match("test_hello.py")

#         # Should not match these files for non-community toolkits
#         assert not pattern.match(".gitignore")
#         assert not pattern.match(".ruff.toml")
#         assert not pattern.match(".pre-commit-config.yaml")
#         assert not pattern.match("README.md")


# class TestRenderTemplate:
#     """Test the template rendering functionality."""

#     def test_render_template_basic(self):
#         """Test basic template rendering."""
#         env = Environment(loader=DictLoader({}))
#         result = render_template(env, "Hello {{ name }}", {"name": "World"})
#         assert result == "Hello World"

#     def test_render_template_with_conditionals(self):
#         """Test template rendering with conditionals."""
#         env = Environment(loader=DictLoader({}))
#         template = "{% if is_community %}arcade_{% endif %}{{ toolkit_name }}"

#         # Test with community toolkit
#         result = render_template(env, template, {"is_community": True, "toolkit_name": "test"})
#         assert result == "arcade_test"

#         # Test without community toolkit
#         result = render_template(env, template, {"is_community": False, "toolkit_name": "test"})
#         assert result == "test"


# class TestStripArcadePrefix:
#     """Test the _strip_arcade_prefix helper function."""

#     def test_strip_arcade_prefix_from_name(self):
#         """Test stripping arcade_ prefix from toolkit name."""
#         from arcade_core.toolkit import Toolkit

#         assert Toolkit._strip_arcade_prefix("arcade_test") == "test"
#         assert Toolkit._strip_arcade_prefix("test") == "test"
#         assert Toolkit._strip_arcade_prefix("arcade_my_toolkit") == "my_toolkit"
#         assert Toolkit._strip_arcade_prefix("myarcade_toolkit") == "myarcade_toolkit"
#         assert Toolkit._strip_arcade_prefix("") == ""


# class TestPyprojectTemplate:
#     """Test the pyproject.toml template rendering."""

#     def test_pyproject_includes_entry_point(self):
#         """Test that pyproject.toml template includes arcade_toolkits entry point."""
#         # Load the template file
#         template_path = (
#             Path(__file__).parent.parent.parent
#             / "arcade-cli"
#             / "arcade_cli"
#             / "templates"
#             / "{{ toolkit_name }}"
#             / "pyproject.toml"
#         )

#         with open(template_path, "r") as f:
#             template_content = f.read()

#         # Verify the entry point section exists
#         assert "[project.entry-points.arcade_toolkits]" in template_content
#         assert 'toolkit_name = "{{ package_name }}"' in template_content

#     def test_pyproject_renders_correctly_community(self):
#         """Test that pyproject.toml renders correctly for community toolkits."""
#         env = Environment(
#             loader=DictLoader({
#                 "pyproject.toml": """
# [project.entry-points.arcade_toolkits]
# toolkit_name = "{{ package_name }}"
# """
#             })
#         )

#         template = env.get_template("pyproject.toml")
#         rendered = template.render(package_name="arcade_mytest")

#         assert 'toolkit_name = "arcade_mytest"' in rendered

#     def test_pyproject_renders_correctly_non_community(self):
#         """Test that pyproject.toml renders correctly for non-community toolkits."""
#         env = Environment(
#             loader=DictLoader({
#                 "pyproject.toml": """
# [project.entry-points.arcade_toolkits]
# toolkit_name = "{{ package_name }}"
# """
#             })
#         )

#         template = env.get_template("pyproject.toml")
#         rendered = template.render(package_name="mytest")

#         assert 'toolkit_name = "mytest"' in rendered
