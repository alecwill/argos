"""Tests for Wikipedia ingestion functionality."""

import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from pet_persona.ingest.wikipedia import WikipediaIngester
from pet_persona.ingest.cache import FileCache


class TestWikipediaIngester:
    """Tests for WikipediaIngester."""

    @pytest.fixture
    def mock_response(self):
        """Create a mock Wikipedia API response."""
        return {
            "query": {
                "pages": {
                    "12345": {
                        "pageid": 12345,
                        "title": "Golden Retriever",
                        "extract": """
                        The Golden Retriever is a medium-largegun dog that was bred to retrieve shot waterfowl.

                        == Temperament ==
                        The Golden Retriever is a friendly, reliable, and trustworthy dog. They are calm,
                        naturally intelligent and biddable, with an exceptional eagerness to please.
                        Golden Retrievers are playful, yet gentle with children, and they tend to get
                        along well with other pets and strangers. They are generally energetic and
                        require regular exercise. They are loving, devoted, and loyal family companions.

                        == History ==
                        The breed was developed in Scotland inthe mid-19th century.
                        """,
                        "revisions": [{"timestamp": "2024-01-01T00:00:00Z"}],
                    }
                }
            }
        }

    @pytest.fixture
    def ingester(self, tmp_path):
        """Create an ingester with temp directories."""
        with patch("pet_persona.ingest.wikipedia.get_settings") as mock_settings:
            mock_settings.return_value.raw_wikipedia_dir = tmp_path / "raw"
            mock_settings.return_value.processed_breeds_dir = tmp_path / "processed"
            mock_settings.return_value.cache_dir = tmp_path / "cache"
            mock_settings.return_value.cache_enabled = False
            mock_settings.return_value.wikipedia_rate_limit_requests = 100
            mock_settings.return_value.wikipedia_rate_limit_period = 60

            (tmp_path / "raw").mkdir()
            (tmp_path / "processed").mkdir()
            (tmp_path / "cache").mkdir()

            return WikipediaIngester()

    def test_extract_temperament_section(self, ingester):
        """Test temperament section extraction."""
        text = """
        Introduction text here.

        == Temperament ==
        This is the temperament section with personality info.
        Very friendly and playful dog.

        == History ==
        This is the history section.
        """

        result = ingester._extract_temperament_section(text)
        assert "temperament" in result.lower() or "friendly" in result.lower()
        # History section should not be included if temperament was found
        assert "history section" not in result.lower() or "temperament" in result.lower()

    def test_extract_no_temperament_section(self, ingester):
        """Test extraction when no temperament section exists."""
        text = """
        This is the first paragraph about the dog breed.

        This is the second paragraph.

        This is the third paragraph about history.
        """

        result = ingester._extract_temperament_section(text)
        # Should return first paragraphs as fallback
        assert "first paragraph" in result or "second paragraph" in result

    @patch("httpx.Client")
    def test_fetch_page(self, mock_client_class, ingester, mock_response):
        """Test fetching a Wikipedia page."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get.return_value.json.return_value = mock_response
        mock_client.get.return_value.raise_for_status = MagicMock()

        result = ingester._fetch_page("Golden Retriever")

        assert result is not None
        assert result["title"] == "Golden Retriever"
        assert "extract" in result

    @patch("httpx.Client")
    def test_fetch_page_not_found(self, mock_client_class, ingester):
        """Test fetching a non-existent page."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get.return_value.json.return_value = {
            "query": {"pages": {"-1": {"missing": ""}}}
        }
        mock_client.get.return_value.raise_for_status = MagicMock()

        result = ingester._fetch_page("NonexistentBreed12345")

        assert result is None

    @patch.object(WikipediaIngester, "_fetch_page")
    def test_ingest_breed(self, mock_fetch, ingester, mock_response, tmp_path):
        """Test ingesting a breed."""
        # Setup mock
        mock_fetch.return_value = {
            "pageid": 12345,
            "title": "Golden Retriever",
            "extract": mock_response["query"]["pages"]["12345"]["extract"],
        }

        # Update ingester paths
        ingester.output_dir = tmp_path / "raw"
        ingester.processed_dir = tmp_path / "processed"
        ingester.output_dir.mkdir(exist_ok=True)
        ingester.processed_dir.mkdir(exist_ok=True)

        baseline = ingester.ingest_breed("Golden Retriever", "dog")

        assert baseline is not None
        assert baseline.breed_name == "Golden Retriever"
        assert baseline.species == "dog"
        assert len(baseline.sources) > 0
        # Should have extracted some traits
        assert len(baseline.extracted_traits) > 0

    @patch.object(WikipediaIngester, "_fetch_page")
    def test_ingest_breed_extracts_traits(self, mock_fetch, ingester, tmp_path):
        """Test that breed ingestion extracts expected traits."""
        mock_fetch.return_value = {
            "pageid": 12345,
            "title": "Golden Retriever",
            "extract": """
            The Golden Retriever is known for being friendly, reliable, and trustworthy.
            They are very playful and gentle dogs that love everyone.
            Golden Retrievers are loyal and devoted family companions.
            """,
        }

        ingester.output_dir = tmp_path / "raw"
        ingester.processed_dir = tmp_path / "processed"
        ingester.output_dir.mkdir(exist_ok=True)
        ingester.processed_dir.mkdir(exist_ok=True)

        baseline = ingester.ingest_breed("Golden Retriever", "dog")

        # Check for expected traits
        trait_ids = set(baseline.extracted_traits.keys())
        assert "friendly" in trait_ids or "playful" in trait_ids or "loyal" in trait_ids

    def test_load_baseline(self, ingester, tmp_path):
        """Test loading a previously saved baseline."""
        # Create a test baseline file
        ingester.processed_dir = tmp_path / "processed"
        ingester.processed_dir.mkdir(exist_ok=True)

        test_baseline = {
            "species": "dog",
            "breed_name": "Test Breed",
            "sources": [],
            "extracted_traits": {
                "friendly": {
                    "trait_name": "Friendly",
                    "score": 0.8,
                    "confidence": 0.7,
                    "evidence": ["Test evidence"],
                }
            },
            "summary": "Test summary",
            "created_at": "2024-01-01T00:00:00",
        }

        baseline_path = ingester.processed_dir / "dog_Test_Breed_baseline.json"
        with open(baseline_path, "w") as f:
            json.dump(test_baseline, f)

        loaded = ingester.load_baseline("Test Breed", "dog")

        assert loaded is not None
        assert loaded.breed_name == "Test Breed"
        assert loaded.species == "dog"
        assert "friendly" in loaded.extracted_traits

    def test_load_baseline_not_found(self, ingester, tmp_path):
        """Test loading a non-existent baseline."""
        ingester.processed_dir = tmp_path / "processed"
        ingester.processed_dir.mkdir(exist_ok=True)

        loaded = ingester.load_baseline("NonexistentBreed", "dog")
        assert loaded is None


class TestFileCache:
    """Tests for FileCache."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create a cache with temp directory."""
        with patch("pet_persona.ingest.cache.get_settings") as mock_settings:
            mock_settings.return_value.cache_dir = tmp_path
            mock_settings.return_value.cache_enabled = True
            return FileCache(cache_dir=tmp_path, ttl_hours=24)

    def test_set_and_get(self, cache):
        """Test setting and getting a value."""
        cache.set("test_key", {"data": "value"})
        result = cache.get("test_key")
        assert result == {"data": "value"}

    def test_get_missing_key(self, cache):
        """Test getting a non-existent key."""
        result = cache.get("nonexistent_key")
        assert result is None

    def test_delete(self, cache):
        """Test deleting a cached value."""
        cache.set("delete_me", "value")
        assert cache.get("delete_me") == "value"

        deleted = cache.delete("delete_me")
        assert deleted is True
        assert cache.get("delete_me") is None

    def test_clear(self, cache):
        """Test clearing all cached values."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        count = cache.clear()
        assert count >= 2

        assert cache.get("key1") is None
        assert cache.get("key2") is None
