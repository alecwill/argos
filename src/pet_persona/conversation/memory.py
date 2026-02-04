"""Conversation memory management."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MemoryTurn:
    """A single turn in conversation memory."""

    user_text: str
    pet_response: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    intent: Optional[str] = None
    evidence_used: List[str] = field(default_factory=list)


@dataclass
class ConversationContext:
    """Context extracted from conversation history."""

    topics_discussed: List[str]
    emotional_tone: str  # "positive", "neutral", "concerned"
    pet_mentioned_activities: List[str]
    user_asked_about: List[str]


class ConversationMemory:
    """
    Manage conversation history and context.

    Stores turns and can generate running summaries
    after N turns to keep context manageable.
    """

    def __init__(
        self,
        max_turns: int = 20,
        summarize_after: int = 10,
    ):
        """
        Initialize conversation memory.

        Args:
            max_turns: Maximum turns to keep in memory
            summarize_after: Generate summary after this many turns
        """
        self.max_turns = max_turns
        self.summarize_after = summarize_after
        self.turns: List[MemoryTurn] = []
        self.running_summary: Optional[str] = None
        self._topic_keywords: Dict[str, List[str]] = {
            "food": ["food", "eat", "treat", "hungry", "dinner", "snack"],
            "play": ["play", "game", "fetch", "toy", "ball", "fun"],
            "walk": ["walk", "outside", "park", "run"],
            "sleep": ["sleep", "tired", "nap", "rest", "bed"],
            "affection": ["love", "cuddle", "pet", "hug", "miss"],
            "health": ["sick", "vet", "hurt", "pain"],
        }

    def add_turn(
        self,
        user_text: str,
        pet_response: str,
        intent: Optional[str] = None,
        evidence_used: Optional[List[str]] = None,
    ) -> None:
        """
        Add a conversation turn to memory.

        Args:
            user_text: User's message
            pet_response: Pet's response
            intent: Detected intent
            evidence_used: Evidence snippets used in response
        """
        turn = MemoryTurn(
            user_text=user_text,
            pet_response=pet_response,
            intent=intent,
            evidence_used=evidence_used or [],
        )
        self.turns.append(turn)

        # Trim if over max
        if len(self.turns) > self.max_turns:
            self._compact_memory()

        # Generate summary if needed
        if len(self.turns) >= self.summarize_after and self.running_summary is None:
            self._update_summary()

        logger.debug(f"Added conversation turn (total: {len(self.turns)})")

    def get_recent_turns(self, n: int = 5) -> List[MemoryTurn]:
        """
        Get the N most recent turns.

        Args:
            n: Number of turns to retrieve

        Returns:
            List of MemoryTurn objects
        """
        return self.turns[-n:]

    def get_context(self) -> ConversationContext:
        """
        Extract context from conversation history.

        Returns:
            ConversationContext object
        """
        topics = self._extract_topics()
        tone = self._analyze_tone()
        activities = self._extract_pet_activities()
        questions = self._extract_user_questions()

        return ConversationContext(
            topics_discussed=topics,
            emotional_tone=tone,
            pet_mentioned_activities=activities,
            user_asked_about=questions,
        )

    def get_formatted_history(self, n: int = 5) -> str:
        """
        Get formatted conversation history string.

        Args:
            n: Number of recent turns to include

        Returns:
            Formatted history string
        """
        recent = self.get_recent_turns(n)
        if not recent:
            return ""

        lines = []
        for turn in recent:
            lines.append(f"Human: {turn.user_text}")
            lines.append(f"Pet: {turn.pet_response}")

        return "\n".join(lines)

    def _compact_memory(self) -> None:
        """Compact memory by updating summary and trimming turns."""
        self._update_summary()
        # Keep only recent turns after max
        self.turns = self.turns[-self.summarize_after:]

    def _update_summary(self) -> None:
        """Update the running summary (simple version for MVP)."""
        if len(self.turns) < 3:
            return

        context = self.get_context()
        parts = []

        if context.topics_discussed:
            parts.append(f"Discussed: {', '.join(context.topics_discussed[:5])}")
        if context.user_asked_about:
            parts.append(f"User asked about: {', '.join(context.user_asked_about[:3])}")
        parts.append(f"Tone: {context.emotional_tone}")

        self.running_summary = ". ".join(parts)
        logger.debug(f"Updated conversation summary: {self.running_summary}")

    def _extract_topics(self) -> List[str]:
        """Extract topics discussed from turns."""
        topics = set()

        for turn in self.turns:
            combined_text = f"{turn.user_text} {turn.pet_response}".lower()
            for topic, keywords in self._topic_keywords.items():
                if any(kw in combined_text for kw in keywords):
                    topics.add(topic)

        return list(topics)

    def _analyze_tone(self) -> str:
        """Analyze emotional tone of conversation."""
        positive_words = {"love", "happy", "good", "great", "wonderful", "fun", "yay"}
        concerned_words = {"worried", "sick", "hurt", "sad", "scared", "help"}

        positive_count = 0
        concerned_count = 0

        for turn in self.turns[-5:]:  # Recent turns
            text = f"{turn.user_text} {turn.pet_response}".lower()
            positive_count += sum(1 for w in positive_words if w in text)
            concerned_count += sum(1 for w in concerned_words if w in text)

        if concerned_count > positive_count:
            return "concerned"
        elif positive_count > 0:
            return "positive"
        return "neutral"

    def _extract_pet_activities(self) -> List[str]:
        """Extract activities the pet mentioned doing."""
        activities = set()
        activity_patterns = [
            "playing", "eating", "sleeping", "running", "walking",
            "cuddling", "watching", "waiting", "exploring",
        ]

        for turn in self.turns:
            text = turn.pet_response.lower()
            for activity in activity_patterns:
                if activity in text:
                    activities.add(activity)

        return list(activities)

    def _extract_user_questions(self) -> List[str]:
        """Extract what the user asked about."""
        questions = set()

        for turn in self.turns:
            if "?" in turn.user_text:
                # Simple extraction of question topics
                for topic, keywords in self._topic_keywords.items():
                    if any(kw in turn.user_text.lower() for kw in keywords):
                        questions.add(topic)

        return list(questions)

    def clear(self) -> None:
        """Clear all memory."""
        self.turns.clear()
        self.running_summary = None
