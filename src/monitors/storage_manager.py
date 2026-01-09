"""Storage manager for screenshots and metadata"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from ..utils.logger import logger


class StorageManager:
    """Manages screenshot storage, metadata, and cleanup"""

    def __init__(self, base_dir: Path):
        """
        Initialize storage manager

        Args:
            base_dir: Base project directory
        """
        self.base_dir = Path(base_dir)
        self.images_dir = self.base_dir / "screenshots"
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def create_folder_structure(self, page_name: str) -> Path:
        """
        Create organized folder structure for screenshots

        Args:
            page_name: Name/identifier for the page

        Returns:
            Path to the dated folder
        """
        # Clean page name for filesystem
        clean_name = "".join(c for c in page_name if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_name = clean_name or "unnamed"

        # Create structure: screenshots/{page_name}/{YYYY-MM-DD}/
        date_str = datetime.now().strftime("%Y-%m-%d")
        folder_path = self.images_dir / clean_name / date_str
        folder_path.mkdir(parents=True, exist_ok=True)

        return folder_path

    def save_screenshot(
        self,
        image_data: bytes,
        page_name: str,
        url: str,
        viewport: Optional[tuple] = None,
        additional_metadata: Optional[Dict] = None
    ) -> Path:
        """
        Save screenshot with metadata

        Args:
            image_data: Raw image bytes (PNG format)
            page_name: Name/identifier for the page
            url: URL that was captured
            viewport: Optional (width, height) tuple
            additional_metadata: Optional dict of extra metadata

        Returns:
            Path to saved screenshot
        """
        # Create folder structure
        folder_path = self.create_folder_structure(page_name)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
        viewport_str = f"{viewport[0]}x{viewport[1]}" if viewport else "fullpage"
        filename = f"{timestamp}_{viewport_str}.png"
        file_path = folder_path / filename

        # Save image
        file_path.write_bytes(image_data)

        # Calculate hash for deduplication
        image_hash = hashlib.sha256(image_data).hexdigest()

        # Create metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "page_name": page_name,
            "filename": filename,
            "file_size": len(image_data),
            "viewport": viewport if viewport else "fullpage",
            "sha256": image_hash,
        }

        if additional_metadata:
            metadata.update(additional_metadata)

        # Save metadata
        self.save_metadata(page_name, metadata)

        logger.info(f"Screenshot saved: {file_path}")
        return file_path

    def save_metadata(self, page_name: str, metadata: Dict):
        """
        Save/append metadata to metadata.json

        Args:
            page_name: Page identifier
            metadata: Metadata dictionary
        """
        # Clean page name
        clean_name = "".join(c for c in page_name if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_name = clean_name or "unnamed"

        # Metadata file path
        metadata_file = self.images_dir / clean_name / "metadata.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing metadata
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    all_metadata = json.load(f)
            except:
                all_metadata = []
        else:
            all_metadata = []

        # Append new metadata
        all_metadata.append(metadata)

        # Save
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(all_metadata, f, indent=2, ensure_ascii=False)

    def cleanup_old_screenshots(self, days: int = 30) -> int:
        """
        Remove screenshots older than N days

        Args:
            days: Number of days to keep

        Returns:
            Number of files deleted
        """
        deleted_count = 0
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)

        for png_file in self.images_dir.rglob("*.png"):
            if png_file.stat().st_mtime < cutoff_date:
                png_file.unlink()
                deleted_count += 1
                logger.debug(f"Deleted old screenshot: {png_file}")

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old screenshots (>{days} days)")

        return deleted_count

    def detect_duplicates(self, page_name: str) -> List[tuple]:
        """
        Find duplicate screenshots using hash comparison

        Args:
            page_name: Page identifier

        Returns:
            List of (file_path, duplicate_of) tuples
        """
        # Clean page name
        clean_name = "".join(c for c in page_name if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_name = clean_name or "unnamed"

        # Load metadata
        metadata_file = self.images_dir / clean_name / "metadata.json"
        if not metadata_file.exists():
            return []

        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                all_metadata = json.load(f)
        except:
            return []

        # Build hash -> filename mapping
        hash_map = {}
        duplicates = []

        for meta in all_metadata:
            file_hash = meta.get("sha256")
            filename = meta.get("filename")

            if not file_hash or not filename:
                continue

            if file_hash in hash_map:
                # Duplicate found
                original = hash_map[file_hash]
                duplicates.append((filename, original))
                logger.debug(f"Duplicate detected: {filename} (same as {original})")
            else:
                hash_map[file_hash] = filename

        return duplicates

    def get_screenshot_count(self, page_name: Optional[str] = None) -> int:
        """
        Get total screenshot count

        Args:
            page_name: Optional page name to filter

        Returns:
            Screenshot count
        """
        if page_name:
            clean_name = "".join(c for c in page_name if c.isalnum() or c in (' ', '-', '_')).strip()
            clean_name = clean_name or "unnamed"
            page_dir = self.images_dir / clean_name
            if page_dir.exists():
                return len(list(page_dir.rglob("*.png")))
            return 0
        else:
            return len(list(self.images_dir.rglob("*.png")))

    def get_statistics(self) -> Dict:
        """
        Get storage statistics

        Returns:
            Dictionary with storage stats
        """
        total_screenshots = len(list(self.images_dir.rglob("*.png")))
        total_size = sum(f.stat().st_size for f in self.images_dir.rglob("*.png"))
        total_pages = len([d for d in self.images_dir.iterdir() if d.is_dir()])

        return {
            "total_screenshots": total_screenshots,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "total_pages": total_pages,
            "storage_path": str(self.images_dir)
        }
