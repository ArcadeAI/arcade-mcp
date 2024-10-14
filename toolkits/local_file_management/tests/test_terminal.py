import os

import pytest
from arcade_local_file_management.tools.terminal import (
    copy_file,
    copy_folder,
    create_directory,
    create_file,
    get_text_file_details,
    list_directory,
    move_file,
    move_folder,
    remove_file,
    rename_file,
    rename_folder,
    search_file,
)


# Helper function to create a temporary file
@pytest.fixture
def temp_file(tmp_path):
    file = tmp_path / "temp.txt"
    file.write_text("Hello, World!")
    return file


# Helper function to create a temporary directory
@pytest.fixture
def temp_directory(tmp_path):
    directory = tmp_path / "temp_dir"
    directory.mkdir()
    return directory


def test_get_text_file_details(temp_file):
    details = get_text_file_details(str(temp_file))
    assert "contents" in details
    assert details["contents"] == "Hello, World!"


def test_search_file(temp_file):
    matches = search_file(str(temp_file), "Hello")
    assert matches == ["Hello, World!"]


def test_list_directory(temp_directory):
    contents = list_directory(str(temp_directory))
    assert contents == []


def test_create_file(temp_directory):
    file_path = str(temp_directory / "new_file.txt")
    create_file(file_path, "Sample content")
    assert os.path.exists(file_path)
    with open(file_path) as f:
        assert f.read() == "Sample content"


def test_create_directory(tmp_path):
    new_dir = tmp_path / "new_dir"
    create_directory(str(new_dir))
    assert os.path.exists(new_dir)
    assert os.path.isdir(new_dir)


def test_remove_file(temp_file):
    remove_file(str(temp_file))
    assert not os.path.exists(temp_file)


def test_copy_file(temp_file, temp_directory):
    destination = temp_directory / "copied_file.txt"
    copy_file(str(temp_file), str(destination))
    assert os.path.exists(destination)
    with open(destination) as f:
        assert f.read() == "Hello, World!"


def test_move_file(temp_file, temp_directory):
    destination = temp_directory / "moved_file.txt"
    move_file(str(temp_file), str(destination))
    assert os.path.exists(destination)
    assert not os.path.exists(temp_file)
    with open(destination) as f:
        assert f.read() == "Hello, World!"


def test_rename_file(temp_file):
    new_name = temp_file.parent / "renamed_file.txt"
    rename_file(str(temp_file), "renamed_file.txt")
    assert os.path.exists(new_name)
    assert not os.path.exists(temp_file)
    with open(new_name) as f:
        assert f.read() == "Hello, World!"


def test_copy_folder(temp_directory, tmp_path):
    # Create a subdirectory and a file inside the temp_directory
    sub_dir = temp_directory / "sub_dir"
    sub_dir.mkdir()
    file_in_sub_dir = sub_dir / "file.txt"
    file_in_sub_dir.write_text("Sample content")

    destination = tmp_path / "copied_dir"

    copy_folder(str(temp_directory), str(destination))
    assert os.path.exists(destination)
    assert os.path.exists(destination / "sub_dir" / "file.txt")
    with open(destination / "sub_dir" / "file.txt") as f:
        assert f.read() == "Sample content"


def test_move_folder(temp_directory, tmp_path):
    # Create a subdirectory and a file inside the temp_directory
    sub_dir = temp_directory / "sub_dir"
    sub_dir.mkdir()
    file_in_sub_dir = sub_dir / "file.txt"
    file_in_sub_dir.write_text("Sample content")

    destination = tmp_path / "moved_dir"

    move_folder(str(temp_directory), str(destination))
    assert os.path.exists(destination)
    assert os.path.exists(destination / "sub_dir" / "file.txt")
    assert not os.path.exists(temp_directory)
    with open(destination / "sub_dir" / "file.txt") as f:
        assert f.read() == "Sample content"


def test_rename_folder(temp_directory):
    # Create a subdirectory and a file inside the temp_directory
    sub_dir = temp_directory / "sub_dir"
    sub_dir.mkdir()
    file_in_sub_dir = sub_dir / "file.txt"
    file_in_sub_dir.write_text("Sample content")

    new_name = temp_directory.parent / "renamed_dir"

    rename_folder(str(temp_directory), "renamed_dir")
    assert os.path.exists(new_name)
    assert os.path.exists(new_name / "sub_dir" / "file.txt")
    assert not os.path.exists(temp_directory)
    with open(new_name / "sub_dir" / "file.txt") as f:
        assert f.read() == "Sample content"
