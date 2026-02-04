"""Trait scoring from text."""

import math
from collections import defaultdict
from typing import Dict, List, Optional

from pet_persona.db.models import TraitScore, TraitVector
from pet_persona.traits.catalog import get_trait_catalog
from pet_persona.traits.lexicon import get_trait_lexicon
from pet_persona.utils.logging import get_logger
from pet_persona.utils.text import extract_sentences

logger = get_logger(__name__)


class TraitScorer:
    """Score personality traits from text content."""

    def __init__(
        self,
        catalog=None,
        lexicon=None,
        keyword_weight: float = 1.0,
        phrase_weight: float = 1.5,
    ):
        """
        Initialize trait scorer.

        Args:
            catalog: Trait catalog (uses default if None)
            lexicon: Trait lexicon (uses default if None)
            keyword_weight: Base weight for keyword matches
            phrase_weight: Base weight for phrase matches (higher = more important)
        """
        self.catalog = catalog or get_trait_catalog()
        self.lexicon = lexicon or get_trait_lexicon()
        self.keyword_weight = keyword_weight
        self.phrase_weight = phrase_weight

    def score_text(self, text: str) -> Dict[str, TraitScore]:
        """
        Score traits from a single text.

        Args:
            text: Text to analyze

        Returns:
            Dict mapping trait_id to TraitScore
        """
        return self.score_texts([text])

    def score_texts(self, texts: List[str]) -> Dict[str, TraitScore]:
        """
        Score traits from multiple texts.

        Args:
            texts: List of texts to analyze

        Returns:
            Dict mapping trait_id to TraitScore
        """
        # Aggregate matches across all texts
        trait_evidence: Dict[str, List[str]] = defaultdict(list)
        trait_weights: Dict[str, List[float]] = defaultdict(list)

        for text in texts:
            if not text:
                continue

            matches = self.lexicon.find_all_matches(text)

            # Process keyword matches
            for trait_id, keyword_matches in matches["keywords"].items():
                for keyword, weight in keyword_matches:
                    # Extract context sentence
                    sentences = extract_sentences(text)
                    for sentence in sentences:
                        if keyword.lower() in sentence.lower():
                            trait_evidence[trait_id].append(sentence)
                            trait_weights[trait_id].append(weight * self.keyword_weight)
                            break
                    else:
                        # No sentence found, use truncated text
                        trait_evidence[trait_id].append(text[:200])
                        trait_weights[trait_id].append(weight * self.keyword_weight)

            # Process phrase matches
            for trait_id, phrase_matches in matches["phrases"].items():
                for phrase_pattern, weight in phrase_matches:
                    sentences = extract_sentences(text)
                    for sentence in sentences:
                        # Check if phrase matches in sentence
                        import re
                        if re.search(phrase_pattern, sentence, re.IGNORECASE):
                            trait_evidence[trait_id].append(sentence)
                            trait_weights[trait_id].append(weight * self.phrase_weight)
                            break
                    else:
                        trait_evidence[trait_id].append(text[:200])
                        trait_weights[trait_id].append(weight * self.phrase_weight)

        # Calculate final scores
        scores = {}
        max_total_weight = 10.0  # Normalize factor

        for trait_id in trait_evidence:
            # Verify trait exists in catalog
            trait_def = self.catalog.get_trait(trait_id)
            if not trait_def:
                continue

            # Calculate score and confidence
            weights = trait_weights[trait_id]
            total_weight = sum(weights)
            match_count = len(weights)

            # Score: sigmoid of total weight, capped at 1.0
            raw_score = total_weight / max_total_weight
            score = min(1.0, 1.0 / (1.0 + math.exp(-3 * (raw_score - 0.5))))

            # Confidence: based on number of matches and weight consistency
            confidence = min(1.0, match_count / 5.0)  # Max confidence at 5+ matches

            # Deduplicate and limit evidence
            unique_evidence = list(dict.fromkeys(trait_evidence[trait_id]))[:5]

            scores[trait_id] = TraitScore(
                trait_name=trait_def.name,
                score=round(score, 3),
                confidence=round(confidence, 3),
                evidence=unique_evidence,
            )

        logger.debug(f"Scored {len(scores)} traits from {len(texts)} texts")
        return scores

    def score_to_vector(self, scores: Dict[str, TraitScore]) -> TraitVector:
        """Convert trait scores to a TraitVector."""
        return TraitVector(traits=scores)


def score_traits(texts: List[str]) -> Dict[str, TraitScore]:
    """
    Convenience function to score traits from texts.

    Args:
        texts: List of texts to analyze

    Returns:
        Dict mapping trait_id to TraitScore
    """
    scorer = TraitScorer()
    return scorer.score_texts(texts)
