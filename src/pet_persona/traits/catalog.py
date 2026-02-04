"""Trait catalog management."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel

from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


class TraitDefinition(BaseModel):
    """Definition of a personality trait."""

    id: str
    name: str
    description: str
    applies_to: List[Literal["dog", "cat"]]
    opposite: Optional[str] = None


class TraitCatalog:
    """Catalog of personality traits."""

    def __init__(self, traits: List[TraitDefinition]):
        self.traits = {t.id: t for t in traits}
        self._by_species: Dict[str, List[TraitDefinition]] = {}

    @classmethod
    def load_from_file(cls, path: Optional[Path] = None) -> "TraitCatalog":
        """Load trait catalog from JSON file."""
        if path is None:
            path = Path(__file__).parent / "traits_catalog.json"

        logger.debug(f"Loading trait catalog from: {path}")
        with open(path, "r") as f:
            data = json.load(f)

        traits = [TraitDefinition(**t) for t in data["traits"]]
        logger.info(f"Loaded {len(traits)} traits from catalog")
        return cls(traits)

    def get_trait(self, trait_id: str) -> Optional[TraitDefinition]:
        """Get a trait by ID."""
        return self.traits.get(trait_id)

    def get_all_traits(self) -> List[TraitDefinition]:
        """Get all traits."""
        return list(self.traits.values())

    def get_traits_for_species(self, species: str) -> List[TraitDefinition]:
        """Get traits applicable to a species."""
        if species not in self._by_species:
            self._by_species[species] = [
                t for t in self.traits.values() if species in t.applies_to
            ]
        return self._by_species[species]

    def get_trait_ids(self) -> List[str]:
        """Get all trait IDs."""
        return list(self.traits.keys())

    def get_opposite(self, trait_id: str) -> Optional[str]:
        """Get the opposite trait ID for a given trait."""
        trait = self.get_trait(trait_id)
        return trait.opposite if trait else None


@lru_cache()
def get_trait_catalog() -> TraitCatalog:
    """Get cached trait catalog instance."""
    return TraitCatalog.load_from_file()
