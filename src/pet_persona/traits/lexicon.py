"""Trait lexicon for keyword/phrase to trait mapping."""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from pydantic import BaseModel

from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


class TraitMapping(BaseModel):
    """Mapping of keywords/phrases to a trait."""

    keywords: List[str]
    phrases: List[str]
    weight: float = 1.0


class TraitLexicon:
    """Lexicon for mapping text to personality traits."""

    def __init__(self, mappings: Dict[str, TraitMapping]):
        self.mappings = mappings
        self._keyword_to_traits: Dict[str, List[Tuple[str, float]]] = {}
        self._phrase_patterns: List[Tuple[re.Pattern, str, float]] = []
        self._build_indices()

    def _build_indices(self) -> None:
        """Build lookup indices for efficient matching."""
        for trait_id, mapping in self.mappings.items():
            # Index keywords
            for keyword in mapping.keywords:
                keyword_lower = keyword.lower()
                if keyword_lower not in self._keyword_to_traits:
                    self._keyword_to_traits[keyword_lower] = []
                self._keyword_to_traits[keyword_lower].append((trait_id, mapping.weight))

            # Compile phrase patterns
            for phrase in mapping.phrases:
                pattern = re.compile(
                    r"\b" + re.escape(phrase.lower()) + r"\b",
                    re.IGNORECASE,
                )
                self._phrase_patterns.append((pattern, trait_id, mapping.weight))

        logger.debug(
            f"Built indices: {len(self._keyword_to_traits)} keywords, "
            f"{len(self._phrase_patterns)} phrase patterns"
        )

    @classmethod
    def load_from_file(cls, path: Optional[Path] = None) -> "TraitLexicon":
        """Load lexicon from JSON file."""
        if path is None:
            path = Path(__file__).parent / "traits_lexicon.json"

        logger.debug(f"Loading trait lexicon from: {path}")
        with open(path, "r") as f:
            data = json.load(f)

        mappings = {
            trait_id: TraitMapping(**mapping_data)
            for trait_id, mapping_data in data["mappings"].items()
        }
        logger.info(f"Loaded lexicon with {len(mappings)} trait mappings")
        return cls(mappings)

    def find_keyword_matches(self, text: str) -> Dict[str, List[Tuple[str, float]]]:
        """
        Find keyword matches in text.

        Returns:
            Dict mapping trait_id to list of (matched_keyword,weight) tuples
        """
        text_lower = text.lower()
        words = set(re.findall(r"\b\w+\b", text_lower))

        matches: Dict[str, List[Tuple[str, float]]] = {}

        for word in words:
            if word in self._keyword_to_traits:
                for trait_id, weight in self._keyword_to_traits[word]:
                    if trait_id not in matches:
                        matches[trait_id] = []
                    matches[trait_id].append((word, weight))

        return matches

    def find_phrase_matches(self, text: str) -> Dict[str, List[Tuple[str, float]]]:
        """
        Find phrase matches in text.

        Returns:
            Dict mapping trait_id to list of (matched_phrase, weight) tuples
        """
        matches: Dict[str, List[Tuple[str, float]]] = {}

        for pattern, trait_id, weight in self._phrase_patterns:
            if pattern.search(text):
                if trait_id not in matches:
                    matches[trait_id] = []
                matches[trait_id].append((pattern.pattern, weight))

        return matches

    def find_all_matches(
        self, text: str
    ) -> Dict[str, Dict[str, List[Tuple[str, float]]]]:
        """
        Find all keyword and phrase matches in text.

        Returns:
            Dict with 'keywords' and 'phrases' keys, each containing
            trait_id -> [(match, weight)] mappings
        """
        return {
            "keywords": self.find_keyword_matches(text),
            "phrases": self.find_phrase_matches(text),
        }

    def get_trait_ids(self) -> Set[str]:
        """Get all trait IDs in the lexicon."""
        return set(self.mappings.keys())


@lru_cache()
def get_trait_lexicon() -> TraitLexicon:
    """Get cached trait lexicon instance."""
    return TraitLexicon.load_from_file()
