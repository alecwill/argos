"""Wikipedia ingestion pipeline."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import httpx

from pet_persona.config import get_settings
from pet_persona.db.models import BreedBaseline, SourceDoc, TraitScore
from pet_persona.ingest.cache import FileCache
from pet_persona.ingest.models import (
    WIKIPEDIA_CAT_TITLE_PATTERNS,
    WIKIPEDIA_DOG_TITLE_PATTERNS,
)
from pet_persona.ingest.rate_limit import RateLimiterRegistry
from pet_persona.traits import score_traits
from pet_persona.utils.logging import get_logger
from pet_persona.utils.text import clean_text

logger = get_logger(__name__)

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"


class WikipediaIngester:
    """Ingest breed information from Wikipedia."""

    def __init__(self):
        settings = get_settings()
        self.cache = FileCache()
        self.rate_limiter = RateLimiterRegistry.get(
            "wikipedia",
            max_requests=settings.wikipedia_rate_limit_requests,
            period_seconds=settings.wikipedia_rate_limit_period,
        )
        self.output_dir = settings.raw_wikipedia_dir
        self.processed_dir = settings.processed_breeds_dir

    def _fetch_page(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a Wikipedia page by title.

        Args:
            title: Wikipedia page title

        Returns:
            Page data dict or None if not found
        """
        cache_key = f"wikipedia:{title}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        self.rate_limiter.acquire()

        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts|revisions",
            "exintro": False,
            "explaintext": True,
            "rvprop": "timestamp",
            "format": "json",
            "redirects": 1,
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(WIKIPEDIA_API_URL, params=params)
                response.raise_for_status()
                data = response.json()

            pages = data.get("query", {}).get("pages", {})

            # Check for valid page
            for page_id, page_data in pages.items():
                if page_id == "-1":
                    logger.debug(f"Wikipedia page not found: {title}")
                    return None

                result = {
                    "title": page_data.get("title", title),
                    "pageid": page_id,
                    "extract": page_data.get("extract", ""),
                    "timestamp": page_data.get("revisions", [{}])[0].get("timestamp"),
                }

                self.cache.set(cache_key, result)
                logger.debug(f"Fetched Wikipedia page: {title}")
                return result

        except httpx.HTTPError as e:
            logger.error(f"Wikipedia API error for '{title}': {e}")
            return None

        return None

    def _extract_temperament_section(self, text: str) -> str:
        """Extract temperament/behavior related sections from page text."""
        if not text:
            return ""

        # Common section headers for temperament info
        section_keywords = [
            "temperament",
            "personality",
            "behavior",
            "behaviour",
            "character",
            "disposition",
            "traits",
            "characteristics",
        ]

        # Try to find relevant sections
        lines = text.split("\n")
        relevant_content = []
        in_relevant_section = False
        section_depth = 0

        for line in lines:
            # Check if this is a section header
            header_match = re.match(r"^(={2,})\s*(.+?)\s*\1$",line)
            if header_match:
                header_text = header_match.group(2).lower()
                depth = len(header_match.group(1))

                # Check if entering relevant section
                if any(kw in header_text for kw in section_keywords):
                    in_relevant_section = True
                    section_depth = depth
                    relevant_content.append(line)
                # Check if leaving relevant section (same or higher level header)
                elif in_relevant_section and depth <= section_depth:
                    in_relevant_section = False
                    section_depth = 0
            elif in_relevant_section:
                relevant_content.append(line)

        # If no specific sections found, include first part ofintro
        if not relevant_content:
            paragraphs = text.split("\n\n")
            # Take first 3 paragraphs as general description
            relevant_content = paragraphs[:3]

        return "\n".join(relevant_content)

    def _find_breed_page(
        self, breed: str, species: Literal["dog", "cat"]
    ) -> Optional[Dict[str, Any]]:
        """
        Find the Wikipedia page for a breed, trying multiple title patterns.

        Args:
            breed: Breed name
            species: 'dog' or 'cat'

        Returns:
            Page data or None if not found
        """
        patterns = (
            WIKIPEDIA_DOG_TITLE_PATTERNS
            if species == "dog"
            else WIKIPEDIA_CAT_TITLE_PATTERNS
        )

        for pattern in patterns:
            title = pattern.format(breed=breed)
            page = self._fetch_page(title)
            if page and page.get("extract"):
                return page

        logger.warning(f"No Wikipedia page found for {species}breed: {breed}")
        return None

    def ingest_breed(
        self, breed: str, species: Literal["dog", "cat"]
    ) -> Optional[BreedBaseline]:
        """
        Ingest breed information from Wikipedia.

        Args:
            breed: Breed name
            species: 'dog' or 'cat'

        Returns:
            BreedBaseline or None if ingestion failed
        """
        logger.info(f"Ingesting Wikipedia data for {species}: {breed}")

        page = self._find_breed_page(breed, species)
        if not page:
            return None

        # Save raw data
        raw_path = self.output_dir / f"{species}_{breed.replace(' ', '_')}.json"
        with open(raw_path, "w") as f:
            json.dump(page, f, indent=2)
        logger.debug(f"Saved raw Wikipedia data to: {raw_path}")

        # Extract relevant content
        full_text = clean_text(page.get("extract", ""))
        temperament_text = self._extract_temperament_section(full_text)

        # Create source document
        source_doc = SourceDoc(
            source_type="wikipedia",
            source_id=str(page.get("pageid", "")),
            title=page.get("title", breed),
            url=f"https://en.wikipedia.org/wiki/{page.get('title', breed).replace(' ', '_')}",
            content=temperament_text or full_text,
            metadata={"species": species, "breed": breed},
        )

        # Score traits from the content
        texts_to_score = [temperament_text] if temperament_text else [full_text]
        trait_scores = score_traits(texts_to_score)

        # Generate summary from first paragraph
        paragraphs = full_text.split("\n\n")
        summary = paragraphs[0] if paragraphs else ""

        # Create breed baseline
        baseline = BreedBaseline(
            species=species,
            breed_name=breed,
            sources=[source_doc],
            extracted_traits=trait_scores,
            summary=summary[:500] if len(summary) > 500 else summary,
        )

        # Save processed baseline
        processed_path = (
            self.processed_dir / f"{species}_{breed.replace(' ', '_')}_baseline.json"
        )
        with open(processed_path, "w") as f:
            json.dump(baseline.model_dump(mode="json"), f, indent=2, default=str)
        logger.info(f"Saved processed baseline to: {processed_path}")

        return baseline

    def ingest_breeds(
        self, breeds: List[str], species: Literal["dog", "cat"]
    ) -> List[BreedBaseline]:
        """
        Ingest multiple breeds.

        Args:
            breeds: List of breed names
            species: 'dog' or 'cat'

        Returns:
            List of successfully ingested BreedBaselines
        """
        baselines = []
        for breed in breeds:
            baseline = self.ingest_breed(breed, species)
            if baseline:
                baselines.append(baseline)

        logger.info(f"Successfully ingested {len(baselines)}/{len(breeds)} {species} breeds")
        return baselines

    def load_baseline(
        self, breed: str, species: Literal["dog", "cat"]
    ) -> Optional[BreedBaseline]:
        """
        Load a previously ingested breed baseline.

        Args:
            breed: Breed name
            species: 'dog' or 'cat'

        Returns:
            BreedBaseline or None if not found
        """
        processed_path = (
            self.processed_dir / f"{species}_{breed.replace(' ', '_')}_baseline.json"
        )

        if not processed_path.exists():
            return None

        with open(processed_path, "r") as f:
            data = json.load(f)

        # Reconstruct the baseline
        sources = [SourceDoc(**s) for s in data.get("sources",[])]
        traits = {
            k: TraitScore(**v) for k, v in data.get("extracted_traits", {}).items()
        }

        return BreedBaseline(
            species=data["species"],
            breed_name=data["breed_name"],
            sources=sources,
            extracted_traits=traits,
            summary=data.get("summary", ""),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.utcnow(),
        )
