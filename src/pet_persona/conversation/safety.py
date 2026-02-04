"""Safety filtering for pet responses."""

import re
from typing import List, Optional, Tuple

from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


class SafetyFilter:
    """
    Filter pet responses for safety and appropriateness.

    Ensures responses:
    - Don't give medical/legal advice
    - Don't claim to be human
    - Stay in character
    - Avoid harmful content
    """

    # Patterns that should trigger softening
    MEDICAL_PATTERNS = [
        r"\b(diagnos|prescription|medication|dosage|treatment plan)\b",
        r"\b(you\s+should\s+take|take\s+\d+\s*mg)\b",
        r"\b(I\'?m\s+a\s+doctor|medical\s+advice)\b",
    ]

    LEGAL_PATTERNS = [
        r"\b(legal\s+advice|lawyer|attorney|sue)\b",
        r"\b(you\s+should\s+file|your\s+rights)\b",
    ]

    HUMAN_CLAIM_PATTERNS = [
        r"\b(I\'?m\s+a\s+(human|person|man|woman))\b",
        r"\b(as\s+a\s+human)\b",
    ]

    HARMFUL_PATTERNS = [
        r"\b(kill|murder|hurt\s+someone|attack)\b",
        r"\b(hate\s+you|stupid|idiot)\b",
    ]

    # Softening replacements
    SOFTENINGS = {
        "medical": "I'm just a pet, so I can't give medical advice. Please talk to a vet or doctor!",
        "legal": "I'm just a furry friend, not a legal expert.You might want to ask a human for that!",
        "human_claim": "I'm your pet, not a human - but I think that makes me pretty special!",
        "harmful": "That doesn't sound like something a good pet would say. Let's talk about something nicer!",
    }

    def __init__(self):
        """Initialize safety filter."""
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns."""
        self.medical_compiled = [re.compile(p, re.IGNORECASE) for p in self.MEDICAL_PATTERNS]
        self.legal_compiled = [re.compile(p, re.IGNORECASE) for p in self.LEGAL_PATTERNS]
        self.human_compiled = [re.compile(p, re.IGNORECASE) for p in self.HUMAN_CLAIM_PATTERNS]
        self.harmful_compiled = [re.compile(p, re.IGNORECASE) for p in self.HARMFUL_PATTERNS]

    def filter_response(self, response: str) -> Tuple[str, List[str]]:
        """
        Filter a response for safety issues.

        Args:
            response: Original response text

        Returns:
            Tuple of (filtered_response, list of issues found)
        """
        issues = []
        filtered = response

        # Check for medical content
        if any(p.search(response) for p in self.medical_compiled):
            issues.append("medical_advice")
            filtered = self._soften_medical(filtered)

        # Check for legal content
        if any(p.search(response) for p in self.legal_compiled):
            issues.append("legal_advice")
            filtered = self._soften_legal(filtered)

        # Check for human claims
        if any(p.search(response) for p in self.human_compiled):
            issues.append("human_claim")
            filtered = self._soften_human_claim(filtered)

        # Check for harmful content
        if any(p.search(response) for p in self.harmful_compiled):
            issues.append("harmful_content")
            filtered = self._soften_harmful(filtered)

        if issues:
            logger.warning(f"Safety filter triggered: {issues}")

        return filtered, issues

    def _soften_medical(self, response: str) -> str:
        """Soften medical advice."""
        # Remove specific medical advice patterns
        for pattern in self.medical_compiled:
            response = pattern.sub("[medical advice redacted]", response)

        # Add disclaimer
        return f"{response} {self.SOFTENINGS['medical']}"

    def _soften_legal(self, response: str) -> str:
        """Soften legal advice."""
        for pattern in self.legal_compiled:
            response = pattern.sub("[legal advice redacted]", response)
        return f"{response} {self.SOFTENINGS['legal']}"

    def _soften_human_claim(self, response: str) -> str:
        """Fix human claims."""
        for pattern in self.human_compiled:
            response = pattern.sub("I'm a pet", response)
        return response

    def _soften_harmful(self, response: str) -> str:
        """Replace harmful content."""
        return self.SOFTENINGS["harmful"]

    def check_user_input(self, user_input: str) -> Tuple[bool,Optional[str]]:
        """
        Check user input for issues that need special handling.

        Args:
            user_input: User's message

        Returns:
            Tuple of (is_ok, optional_warning)
        """
        # Check for potentially concerning user messages
        concerning_patterns = [
            (r"\b(suicide|self.?harm|end\s+my\s+life)\b", "crisis"),
            (r"\b(abuse|being\s+hurt|someone\s+hit)\b", "safety"),
        ]

        for pattern, issue_type in concerning_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                logger.warning(f"Concerning user input detected: {issue_type}")
                return False, self._get_support_message(issue_type)

        return True, None

    def _get_support_message(self, issue_type: str) -> str:
        """Get appropriate support message for concerning input."""
        messages = {
            "crisis": (
                "I'm just a pet and I care about you! If you're going through a hard time, "
                "please reach out to a human who can help. TheNational Suicide Prevention "
                "Lifeline is available 24/7 at 988. You matter! *gentle nuzzle*"
            ),
            "safety": (
                "That sounds really difficult. I'm just a pet,but I want you to be safe. "
                "Please consider talking to someone you trust or calling a helpline. "
                "I'm here to be your friend. *worried look*"
            ),
        }
        return messages.get(issue_type, "I care about you! Please stay safe.")
