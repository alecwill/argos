"""Trait framework for personality analysis."""

from pet_persona.traits.catalog import TraitCatalog, get_trait_catalog
from pet_persona.traits.lexicon import TraitLexicon, get_trait_lexicon
from pet_persona.traits.scorer import TraitScorer, score_traits

__all__ = [
    "TraitCatalog",
    "get_trait_catalog",
    "TraitLexicon",
    "get_trait_lexicon",
    "TraitScorer",
    "score_traits",
]
