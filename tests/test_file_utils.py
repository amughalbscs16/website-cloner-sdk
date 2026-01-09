"""Tests for file utilities"""

import pytest
import tempfile
from pathlib import Path
from src.utils.file_utils import FileManager


class TestFileManager:
    """Test file management utilities"""

    def test_create_project_directory(self):
        """Test creating project directory with base64 naming"""
        with tempfile.TemporaryDirectory() as temp_dir:
            fm = FileManager(Path(temp_dir))
            url = "https://example.com"
            project_path = fm.create_project_directory(url)

            assert project_path.exists()
            assert project_path.is_dir()
            # Base64 encoding of the URL should be the folder name
            assert len(project_path.name) > 0

    def test_save_file(self):
        """Test saving file content"""
        with tempfile.TemporaryDirectory() as temp_dir:
            fm = FileManager(Path(temp_dir))
            file_path = Path(temp_dir) / "test.txt"
            content = b"Hello, World!"

            fm.save_file(file_path, content)

            assert file_path.exists()
            assert file_path.read_bytes() == content

    def test_get_unique_filename_no_collision(self):
        """Test unique filename generation when no collision"""
        with tempfile.TemporaryDirectory() as temp_dir:
            fm = FileManager(Path(temp_dir))
            directory = Path(temp_dir)
            filename = "test.jpg"

            result = fm.get_unique_filename(directory, filename, [".jpg"])

            assert result.name == filename

    def test_get_unique_filename_with_collision(self):
        """Test unique filename generation with collision"""
        with tempfile.TemporaryDirectory() as temp_dir:
            fm = FileManager(Path(temp_dir))
            directory = Path(temp_dir)
            filename = "test.jpg"

            # Create existing file
            (directory / filename).touch()

            result = fm.get_unique_filename(directory, filename, [".jpg"])

            # Should append a number
            assert result.name != filename
            assert result.name.startswith("test")
            assert result.suffix == ".jpg"
