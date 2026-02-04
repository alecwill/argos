"""Intent classification for user messages."""

import re
from enum import Enum
from typing import Dict, List, Optional, Tuple

from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


class Intent(Enum):
    """User message intents."""

    GREETING = "greeting"
    FAREWELL = "farewell"
    QUESTION = "question"
    BONDING = "bonding"
    PLAY = "play"
    FOOD = "food"
    TRAINING = "training"
    BEHAVIOR = "behavior"
    HEALTH = "health"
    AFFECTION = "affection"
    STATEMENT = "statement"
    COMMAND = "command"
    UNKNOWN = "unknown"


# Keyword patterns for each intent
INTENT_PATTERNS: Dict[Intent, List[str]] = {
    Intent.GREETING: [
        r"\b(hi|hello|hey|greetings|howdy|sup|yo)\b",
        r"\bgood\s+(morning|afternoon|evening|night)\b",
        r"\bwhat'?s?\s+up\b",
    ],
    Intent.FAREWELL: [
        r"\b(bye|goodbye|goodnight|farewell|see\s+you|later|cya)\b",
        r"\bgotta\s+go\b",
        r"\btalk\s+(to\s+you\s+)?later\b",
    ],
    Intent.QUESTION: [
        r"\?$",
        r"^(what|who|where|when|why|how|which|whose|whom)\b",
        r"\bdo\s+you\s+(like|want|think|know|feel)\b",
    ],
    Intent.BONDING: [
        r"\b(love\s+you|miss\s+you|missed\s+you|thinking\s+of\s+you)\b",
        r"\b(best\s+friend|my\s+buddy|my\s+pal)\b",
        r"\bhow\s+are\s+you\b",
    ],
    Intent.PLAY: [
        r"\b(play|game|fetch|toy|ball|frisbee|catch)\b",
        r"\b(let'?s?\s+play|wanna\s+play|want\s+to\s+play)\b",
        r"\b(run|chase|jump|zoomies)\b",
    ],
    Intent.FOOD: [
        r"\b(food|treat|snack|hungry|eat|dinner|breakfast|lunch)\b",
        r"\b(yummy|delicious|tasty)\b",
        r"\b(feed|feeding|meal)\b",
    ],
    Intent.TRAINING: [
        r"\b(sit|stay|come|heel|down|roll\s+over|shake|paw)\b",
        r"\b(train|training|learn|teach|command)\b",
        r"\b(trick|behavior)\b",
    ],
    Intent.BEHAVIOR: [
        r"\b(why\s+do\s+you|why\s+are\s+you)\b",
        r"\b(barking|meowing|whining|scratching|biting)\b",
        r"\b(behavior|behave|act|acting)\b",
    ],
    Intent.HEALTH: [
        r"\b(sick|ill|hurt|pain|vet|doctor|medicine)\b",
        r"\b(feel\s+okay|feeling\s+well|not\s+feeling)\b",
        r"\b(health|healthy|checkup)\b",
    ],
    Intent.AFFECTION: [
        r"\b(cuddle|hug|pet|scratch|belly\s+rub|pat)\b",
        r"\b(come\s+here|sit\s+with\s+me|snuggle)\b",
        r"\b(good\s+(boy|girl|kitty|doggo))\b",
    ],
    Intent.COMMAND: [
        r"^(sit|stay|come|go|stop|no|yes|okay)[\s!.]*$",
        r"\b(do\s+this|do\s+that|don'?t)\b",
    ],
}


# Priority for tie-breaking: higher = preferred when scores are equal.
# More specific intents should win over generic ones.
INTENT_PRIORITY: Dict[Intent, int] = {
    Intent.QUESTION: 0,   # Very generic (matches any '?')
    Intent.STATEMENT: 0,
    Intent.UNKNOWN: 0,
    Intent.COMMAND: 1,
    Intent.TRAINING: 1,
    Intent.BEHAVIOR: 2,
    Intent.HEALTH: 2,
    Intent.GREETING: 3,
    Intent.FAREWELL: 3,
    Intent.PLAY: 3,
    Intent.FOOD: 3,
    Intent.AFFECTION: 3,
    Intent.BONDING: 3,
}


class IntentClassifier:
    """
    Classify user message intents.

    MVP: Rule-based classification using keyword patterns.
    Can be extended with ML classifier later.
    """

    def __init__(self):
        """Initialize intent classifier."""
        self.patterns = INTENT_PATTERNS
        self._compiled_patterns: Dict[Intent, List[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficiency."""
        for intent, patterns in self.patterns.items():
            self._compiled_patterns[intent] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def classify(self, text: str) -> Tuple[Intent, float]:
        """
        Classify the intent of a message.

        Args:
            text: User message text

        Returns:
            Tuple of (Intent, confidence)
        """
        if not text.strip():
            return Intent.UNKNOWN, 0.0

        text = text.strip()

        # Track matches
        intent_scores: Dict[Intent, float] = {}

        for intent, patterns in self._compiled_patterns.items():
            matches = sum(1 for p in patterns if p.search(text))
            if matches > 0:
                # Score based on number of pattern matches
                intent_scores[intent] = matches / len(patterns)

        if not intent_scores:
            # Default to statement if no patterns match
            return Intent.STATEMENT, 0.5

        # Dampen QUESTION score when more specific intents also matched,
        # since '?' and starting question words are very generic patterns
        if Intent.QUESTION in intent_scores and len(intent_scores) > 1:
            intent_scores[Intent.QUESTION] *= 0.6

        # Get highest scoring intent, breaking ties by specificity priority
        best_intent = max(intent_scores, key=lambda i: (intent_scores[i], INTENT_PRIORITY.get(i, 1)))
        confidence = min(intent_scores[best_intent] * 1.5, 1.0)  # Scale up confidence

        logger.debug(f"Classified intent: {best_intent.value} (confidence: {confidence:.2f})")
        return best_intent, confidence

    def get_all_intents(self, text: str) -> List[Tuple[Intent,float]]:
        """
        Get all matching intents for a message.

        Args:
            text: User message text

        Returns:
            List of (Intent, confidence) tuples, sorted by confidence
        """
        if not text.strip():
            return [(Intent.UNKNOWN, 0.0)]

        intent_scores = []

        for intent, patterns in self._compiled_patterns.items():
            matches = sum(1 for p in patterns if p.search(text))
            if matches > 0:
                confidence = min(matches / len(patterns) * 1.5, 1.0)
                intent_scores.append((intent, confidence))

        if not intent_scores:
            return [(Intent.STATEMENT, 0.5)]

        # Sort by confidence descending
        intent_scores.sort(key=lambda x: x[1], reverse=True)
        return intent_scores
