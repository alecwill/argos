"""Caching utilities for ingested data."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

from pet_persona.config import get_settings
from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


class FileCache:
    """File-based cache for storing fetched data."""

    def __init__(self, cache_dir: Optional[Path] = None, ttl_hours: int = 24):
        """
        Initialize file cache.

        Args:
            cache_dir: Directory for cache files (uses defaultif None)
            ttl_hours: Time-to-live in hours
        """
        settings = get_settings()
        self.cache_dir = cache_dir or settings.cache_dir
        self.ttl_seconds = ttl_hours * 3600
        self.enabled = settings.cache_enabled

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key."""
        # Hash the key for filesystem safety
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        safe_key = "".join(c if c.isalnum() else "_" for c in key[:50])
        filename = f"{safe_key}_{key_hash}.json"
        return self.cache_dir / filename

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if not self.enabled:
            return None

        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                data = json.load(f)

            # Check expiration
            cached_at = data.get("cached_at", 0)
            if time.time() - cached_at > self.ttl_seconds:
                logger.debug(f"Cache expired for key: {key[:50]}")
                cache_path.unlink(missing_ok=True)
                return None

            logger.debug(f"Cache hit for key: {key[:50]}")
            return data.get("value")

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Cache read error for key {key[:50]}: {e}")
            return None

    def set(self, key: str, value: Any) -> None:
        """
        Store a value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
        """
        if not self.enabled:
            return

        cache_path = self._get_cache_path(key)

        try:
            data = {
                "key": key,
                "value": value,
                "cached_at": time.time(),
            }
            with open(cache_path, "w") as f:
                json.dump(data, f)
            logger.debug(f"Cached value for key: {key[:50]}")

        except (TypeError, IOError) as e:
            logger.warning(f"Cache write error for key {key[:50]}: {e}")

    def delete(self, key: str) -> bool:
        """
        Delete a cached value.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
            return True
        return False

    def clear(self) -> int:
        """
        Clear all cached values.

        Returns:
            Number of items cleared
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1
        logger.info(f"Cleared {count} cached items")
        return count

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of items removed
        """
        count = 0
        now = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                cached_at = data.get("cached_at", 0)
                if now - cached_at > self.ttl_seconds:
                    cache_file.unlink()
                    count += 1
            except (json.JSONDecodeError, KeyError):
                # Remove corrupted cache files
                cache_file.unlink()
                count += 1

        if count > 0:
            logger.info(f"Cleaned up {count} expired cache entries")
        return count
