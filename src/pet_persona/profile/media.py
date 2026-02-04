"""Media processing for pet profile."""

import mimetypes
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MediaMetadata:
    """Metadata for uploaded media."""

    file_path: str
    file_type: str  # "image", "video", "unknown"
    mime_type: Optional[str]
    file_size: int
    duration_seconds: Optional[float] = None  # For videos
    width: Optional[int] = None
    height: Optional[int] = None
    tags: List[str] = None  # Vision-derived tags

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "duration_seconds": self.duration_seconds,
            "width": self.width,
            "height": self.height,
            "tags": self.tags,
        }


class MediaTagger(ABC):
    """Abstract interface for media tagging (vision analysis)."""

    @abstractmethod
    def tag_image(self, image_path: Path) -> List[str]:
        """
        Generate tags for an image.

        Args:
            image_path: Path to image file

        Returns:
            List of descriptive tags
        """
        pass

    @abstractmethod
    def tag_video(self, video_path: Path) -> List[str]:
        """
        Generate tags for a video.

        Args:
            video_path: Path to video file

        Returns:
            List of descriptive tags
        """
        pass


class PlaceholderMediaTagger(MediaTagger):
    """
    Placeholder media tagger that returns empty tags.

    This is a stub implementation for the MVP. Replace with actual
    vision model integration when GPU/vision capabilities are available.
    """

    def tag_image(self, image_path: Path) -> List[str]:
        """Return empty tags (placeholder)."""
        logger.debug(f"PlaceholderMediaTagger: No tags for image {image_path}")
        return []

    def tag_video(self, video_path: Path) -> List[str]:
        """Return empty tags (placeholder)."""
        logger.debug(f"PlaceholderMediaTagger: No tags for video {video_path}")
        return []


class MediaProcessor:
    """Process and extract metadata from uploaded media."""

    # Supported file types
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

    def __init__(self, tagger: Optional[MediaTagger] = None):
        """
        Initialize media processor.

        Args:
            tagger: Media tagger for vision analysis (uses placeholder if None)
        """
        self.tagger = tagger or PlaceholderMediaTagger()

    def process_file(self, file_path: Path) -> Optional[MediaMetadata]:
        """
        Process a media file and extract metadata.

        Args:
            file_path: Path to media file

        Returns:
            MediaMetadata or None if file not supported/found
        """
        if not file_path.exists():
            logger.warning(f"Media file not found: {file_path}")
            return None

        suffix = file_path.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(file_path))

        # Determine file type
        if suffix in self.IMAGE_EXTENSIONS:
            file_type = "image"
        elif suffix in self.VIDEO_EXTENSIONS:
            file_type = "video"
        else:
            file_type = "unknown"
            logger.warning(f"Unknown media type: {suffix}")

        # Get basic metadata
        file_size = file_path.stat().st_size

        metadata = MediaMetadata(
            file_path=str(file_path),
            file_type=file_type,
            mime_type=mime_type,
            file_size=file_size,
        )

        # Extract type-specific metadata
        if file_type == "image":
            self._extract_image_metadata(file_path, metadata)
        elif file_type == "video":
            self._extract_video_metadata(file_path, metadata)

        # Apply vision tagging
        if file_type == "image":
            metadata.tags = self.tagger.tag_image(file_path)
        elif file_type == "video":
            metadata.tags = self.tagger.tag_video(file_path)

        logger.info(f"Processed media file: {file_path.name} ({file_type})")
        return metadata

    def _extract_image_metadata(
        self, file_path: Path, metadata: MediaMetadata
    ) -> None:
        """Extract image-specific metadata."""
        try:
            # Try using PIL for image dimensions
            from PIL import Image

            with Image.open(file_path) as img:
                metadata.width, metadata.height = img.size

        except ImportError:
            logger.debug("PIL not installed, skipping image dimension extraction")
        except Exception as e:
            logger.warning(f"Error extracting image metadata: {e}")

    def _extract_video_metadata(
        self, file_path: Path, metadata: MediaMetadata
    ) -> None:
        """Extract video-specific metadata."""
        try:
            # Try using ffprobe via subprocess for video info
            import subprocess
            import json

            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    str(file_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                probe_data = json.loads(result.stdout)

                # Get duration
                format_info = probe_data.get("format", {})
                duration = format_info.get("duration")
                if duration:
                    metadata.duration_seconds = float(duration)

                # Get video stream dimensions
                for stream in probe_data.get("streams", []):
                    if stream.get("codec_type") == "video":
                        metadata.width = stream.get("width")
                        metadata.height = stream.get("height")
                        break

        except FileNotFoundError:
            logger.debug("ffprobe not found, skipping video metadata extraction")
        except Exception as e:
            logger.warning(f"Error extracting video metadata: {e}")

    def process_files(self, file_paths: List[Path]) -> List[MediaMetadata]:
        """
        Process multiple media files.

        Args:
            file_paths: List of paths to media files

        Returns:
            List of MediaMetadata objects (excludes failed files)
        """
        results = []
        for path in file_paths:
            metadata = self.process_file(path)
            if metadata:
                results.append(metadata)

        logger.info(f"Processed {len(results)}/{len(file_paths)} media files")
        return results
