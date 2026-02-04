"""Questionnaire processing for pet personality."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pet_persona.db.models import QuestionnaireResponse, TraitScore
from pet_persona.traits import score_traits
from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


# Questionnaire categories and their trait associations
CATEGORY_TRAIT_WEIGHTS = {
    "energy": {
        "active": 1.0,
        "energetic": 1.0,
        "lazy": -1.0,
        "playful": 0.8,
    },
    "social": {
        "friendly": 1.0,
        "sociable": 1.0,
        "shy": -0.8,
        "reserved": -0.5,
    },
    "temperament": {
        "calm": 1.0,
        "anxious": -1.0,
        "gentle": 0.8,
        "aggressive": -0.8,
    },
    "trainability": {
        "trainable": 1.0,
        "intelligent": 0.8,
        "obedient": 0.8,
        "stubborn": -0.8,
    },
    "independence": {
        "independent": 1.0,
        "devoted": -0.5,
        "loyal": -0.3,
    },
    "vocalization": {
        "vocal": 1.0,
        "quiet": -1.0,
    },
    "personality": {},  # General, uses text scoring
}


class QuestionnaireProcessor:
    """Process questionnaire responses to extract personality traits."""

    def __init__(self):
        self.category_weights = CATEGORY_TRAIT_WEIGHTS

    def load_questionnaire(self, path: Path) -> Dict[str, Any]:
        """
        Load a questionnaire schema from JSON file.

        Args:
            path: Path to questionnaire JSON file

        Returns:
            Questionnaire schema dict
        """
        with open(path, "r") as f:
            return json.load(f)

    def parse_responses(
        self, questionnaire: Dict[str, Any], answers: Dict[str, str]
    ) -> List[QuestionnaireResponse]:
        """
        Parse raw answers into QuestionnaireResponse objects.

        Args:
            questionnaire: Questionnaire schema
            answers: Dict mapping question_id to answer

        Returns:
            List of QuestionnaireResponse objects
        """
        responses = []

        for question in questionnaire.get("questions", []):
            question_id = question.get("id")
            if question_id not in answers:
                continue

            response = QuestionnaireResponse(
                question_id=question_id,
                question_text=question.get("text", ""),
                answer=answers[question_id],
                category=question.get("category"),
            )
            responses.append(response)

        logger.debug(f"Parsed {len(responses)} questionnaire responses")
        return responses

    def score_from_responses(
        self, responses: List[QuestionnaireResponse]
    ) -> Dict[str, TraitScore]:
        """
        Score traits from questionnaire responses.

        Uses a combination of:
        1. Category-based trait weighting for structured answers
        2. Text-based trait extraction for free-form answers

        Args:
            responses: List of QuestionnaireResponse objects

        Returns:
            Dict mapping trait_id to TraitScore
        """
        # Collect text for scoring
        texts_to_score = []
        category_signals: Dict[str, List[float]] = {}

        for response in responses:
            # Add answer text for scoring
            if response.answer:
                texts_to_score.append(
                    f"{response.question_text} {response.answer}"
                )

            # Process categorical signals
            category = response.category
            if category and category in self.category_weights:
                # Try to extract numerical signal from answer
                signal = self._extract_signal(response.answer)
                if signal is not None:
                    for trait_id, weight in self.category_weights[category].items():
                        if trait_id not in category_signals:
                            category_signals[trait_id] = []
                        category_signals[trait_id].append(signal * weight)

        # Get text-based scores
        text_scores = score_traits(texts_to_score)

        # Combine with category-based signals
        for trait_id, signals in category_signals.items():
            if not signals:
                continue

            avg_signal = sum(signals) / len(signals)
            # Convert signal (-1 to 1) to score (0 to 1)
            category_score = (avg_signal + 1) / 2

            if trait_id in text_scores:
                # Blend text and category scores
                existing = text_scores[trait_id]
                blended_score = (existing.score + category_score) / 2
                blended_confidence = max(existing.confidence, 0.5)
                text_scores[trait_id] = TraitScore(
                    trait_name=existing.trait_name,
                    score=round(blended_score, 3),
                    confidence=round(blended_confidence, 3),
                    evidence=existing.evidence,
                )
            else:
                # Add new trait from category
                from pet_persona.traits import get_trait_catalog

                catalog = get_trait_catalog()
                trait_def = catalog.get_trait(trait_id)
                if trait_def:
                    text_scores[trait_id] = TraitScore(
                        trait_name=trait_def.name,
                        score=round(max(0, min(1, category_score)), 3),
                        confidence=0.5,
                        evidence=[f"Based on questionnaire ({category} category)"],
                    )

        logger.info(f"Scored {len(text_scores)} traits from questionnaire")
        return text_scores

    def _extract_signal(self, answer: str) -> Optional[float]:
        """
        Extract a numerical signal from an answer.

        Maps common responses to -1 to 1 scale.

        Args:
            answer: Answer text

        Returns:
            Signal value or None if not mappable
        """
        answer_lower = answer.lower().strip()

        # Numerical scale (1-5 or 1-10)
        try:
            num = int(answer_lower)
            if 1 <= num <= 5:
                return (num - 3) / 2  # -1 to 1
            elif 1 <= num <= 10:
                return (num - 5.5) / 4.5  # -1 to 1
        except ValueError:
            pass

        # Common text responses
        positive_words = {
            "yes": 0.8,
            "very": 1.0,
            "extremely": 1.0,
            "highly": 1.0,
            "always": 1.0,
            "often": 0.6,
            "usually": 0.5,
            "sometimes": 0.0,
            "loves": 0.9,
            "enjoys": 0.7,
            "high": 0.8,
        }

        negative_words = {
            "no": -0.8,
            "not": -0.5,
            "never": -1.0,
            "rarely": -0.6,
            "seldom": -0.5,
            "low": -0.8,
            "hates": -0.9,
            "dislikes": -0.7,
        }

        # Check for keyword matches
        for word, value in positive_words.items():
            if word in answer_lower:
                return value

        for word, value in negative_words.items():
            if word in answer_lower:
                return value

        return None
