"""File management utilities"""

import os
import base64
from pathlib import Path
from typing import Dict, Tuple, Optional
from .logger import logger


class FileManager:
    """Manages file operations for downloaded resources"""

    # Illegal characters in Windows filenames
    ILLEGAL_CHARS = ['/', '\\', '<', '>', ':', '"', '|', '?', '*']

    def __init__(self, base_path: Path):
        """Initialize file manager with base project path"""
        self.base_path = base_path
        self.files_dict: Dict[str, int] = {}
        self.link_file: Dict[str, str] = {}

    @staticmethod
    def get_project_folder(url: str) -> str:
        """Generate a base64-encoded folder name from URL"""
        folder_bytes = base64.b64encode(url.encode('utf-8'))
        return folder_bytes.decode('utf-8')

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Remove illegal characters from filename"""
        for char in FileManager.ILLEGAL_CHARS:
            filename = filename.replace(char, '')
        return filename

    def create_project_directory(self, url: str) -> Path:
        """Create and return project directory for a URL"""
        folder = self.get_project_folder(url)
        path = self.base_path / folder
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Project directory: {path}")
        return path

    def make_directory_structure(self, file_url: str, project_path: Path) -> Tuple[Path, str]:
        """
        Create directory structure based on URL path

        Args:
            file_url: The file URL
            project_path: Base project path

        Returns:
            Tuple of (save_directory, html_directory)
        """
        # Remove protocol
        file_url_clean = file_url.split('//', 1)[-1] if '//' in file_url else file_url

        # Split path components
        parts = Path(file_url_clean).parts

        save_directory = project_path
        html_directory = ""

        # Create folders (skip first part - domain, and last part - filename)
        if len(parts) > 2:
            for folder in parts[1:-1]:
                folder = self.sanitize_filename(folder)
                save_directory = save_directory / folder
                try:
                    save_directory.mkdir(exist_ok=True, parents=True)
                except Exception as e:
                    logger.warning(f"Could not create directory {save_directory}: {e}")
                    continue
                html_directory = os.path.join(html_directory, folder)

        return save_directory, html_directory

    def get_unique_filename(
        self,
        directory: Path,
        filename: str,
        allowed_extensions: tuple
    ) -> Path:
        """
        Generate a unique filename in the directory

        Args:
            directory: Target directory
            filename: Original filename
            allowed_extensions: Tuple of allowed extensions

        Returns:
            Unique file path
        """
        # Split filename and extensions
        parts = filename.split('?')[0].split('#')[0].split('.')

        if len(parts) == 1 and parts[0] in allowed_extensions:
            # Just an extension
            base_name = "0"
            extension = parts[0]
        else:
            # Normal filename with extension(s)
            base_name = parts[0]
            extension = '.'.join(parts[1:]) if len(parts) > 1 else ""

        # Generate unique name
        counter = 0
        if extension:
            file_path = directory / f"{base_name}.{extension}"
        else:
            file_path = directory / base_name

        while str(file_path) in self.files_dict:
            counter += 1
            if extension:
                file_path = directory / f"{base_name}{counter}.{extension}"
            else:
                file_path = directory / f"{base_name}{counter}"

        self.files_dict[str(file_path)] = 1
        return file_path

    def save_file(self, file_path: Path, content: bytes) -> None:
        """Save binary content to file"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)
            logger.debug(f"Saved file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to save file {file_path}: {e}")
            raise

    def read_file(self, file_path: Path, encoding: str = 'utf-8') -> Optional[str]:
        """Read text file"""
        try:
            return file_path.read_text(encoding=encoding)
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None
