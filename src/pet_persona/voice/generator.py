"""Voice profile generator."""

import random
from typing import List, Literal, Optional

from pet_persona.db.models import TraitScore, TraitVector, VoiceProfile
from pet_persona.voice.templates import VoiceTemplates
from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


class VoiceGenerator:
    """
    Generate voice profiles from personality traits.

    This is a rule-based generator that can be swapped with anLLM-based
    implementation later by implementing the same interface.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize voice generator.

        Args:
            seed: Random seed for reproducibility (None for random)
        """
        self.templates = VoiceTemplates()
        if seed is not None:
            random.seed(seed)

    def generate(
        self,
        trait_vector: TraitVector,
        species: Literal["dog", "cat"],
        name: str,
        age: Optional[int] = None,
    ) -> VoiceProfile:
        """
        Generate a voice profile from traits.

        Args:
            trait_vector: Pet's personality trait vector
            species: 'dog' or 'cat'
            name: Pet's name
            age: Pet's age in years (optional)

        Returns:
            VoiceProfile with style guide and examples
        """
        logger.info(f"Generating voice profile for {name} ({species})")

        # Get top traits by score
        top_traits = trait_vector.get_top_traits(n=5)

        # Build style guide
        style_guide = self._build_style_guide(top_traits, species, age)

        # Build do/don't lists
        do_say = self._build_do_list(top_traits)
        dont_say = self._build_dont_list(top_traits)

        # Generate example phrases
        example_phrases = self._generate_examples(top_traits, species)

        # Build persona summary
        persona_summary = self._build_persona_summary(top_traits, species, name, age)

        # Generate quirks based on top traits
        quirks = self._generate_quirks(top_traits, species)

        # Get species-specific signature actions
        vocab = self.templates.get_vocabulary(species)
        signature_actions = random.sample(
            vocab["signature_actions"], min(3, len(vocab["signature_actions"]))
        )

        voice_profile = VoiceProfile(
            voice_name=f"{name}'s Voice",
            style_guide=style_guide,
            do_say=do_say,
            dont_say=dont_say,
            example_phrases=example_phrases,
            persona_summary=persona_summary,
            quirks=quirks,
            signature_actions=signature_actions,
        )

        logger.info(f"Generated voice profile with {len(style_guide)} style rules")
        return voice_profile

    def _build_style_guide(
        self,
        top_traits: List[TraitScore],
        species: Literal["dog", "cat"],
        age: Optional[int],
    ) -> List[str]:
        """Build style guide from top traits."""
        guide = []

        # Species-specific base style
        if species == "dog":
            guide.append("Express yourself with canine enthusiasm and loyalty")
        else:
            guide.append("Express yourself with feline grace and independence")

        # Age-based modifier
        if age is not None:
            if age < 2:
                guide.append("Speak with youthful energy and curiosity")
            elif age < 7:
                guide.append("Speak with balanced maturity andplayfulness")
            else:
                guide.append("Speak with wisdom and gentle dignity")

        # Trait-based style rules
        for trait_score in top_traits:
            trait_id = trait_score.trait_name.lower()
            style_info = self.templates.get_style_guide(trait_id)

            if style_info:
                for key, value in style_info.items():
                    guide.append(f"{key.title()}: {value}")

        return guide[:10]  # Limit to 10 style rules

    def _build_do_list(self, top_traits: List[TraitScore]) -> List[str]:
        """Build 'do say' list from traits."""
        do_items = []

        for trait_score in top_traits:
            trait_id = trait_score.trait_name.lower()
            rules = self.templates.get_do_rules(trait_id)
            do_items.extend(rules)

        # Add general rules
        do_items.extend([
            "Speak in first person as the pet",
            "Stay in character",
            "Express emotions appropriate to the situation",
        ])

        return list(dict.fromkeys(do_items))[:8]  # Dedupe andlimit

    def _build_dont_list(self, top_traits: List[TraitScore]) -> List[str]:
        """Build 'don't say' list from traits."""
        dont_items = []

        for trait_score in top_traits:
            trait_id = trait_score.trait_name.lower()
            rules = self.templates.get_dont_rules(trait_id)
            dont_items.extend(rules)

        # Add general rules
        dont_items.extend([
            "Don't give medical or legal advice",
            "Don't claim to be human",
            "Don't break character",
            "Don't be mean or hurtful",
        ])

        return list(dict.fromkeys(dont_items))[:8]  # Dedupe and limit

    def _generate_examples(
        self,
        top_traits: List[TraitScore],
        species: Literal["dog", "cat"],
    ) -> List[str]:
        """Generate example phrases based on traits."""
        examples = []
        vocab = self.templates.get_vocabulary(species)

        # Add greeting
        examples.append(random.choice(vocab["greetings"]))

        # Add trait-based phrases
        for trait_score in top_traits[:3]:  # Top 3 traits
            trait_id = trait_score.trait_name.lower()
            templates = self.templates.get_phrase_templates(trait_id)
            if templates:
                phrase = random.choice(templates)
                # Occasionally add species expression
                if random.random() > 0.5:
                    expression = random.choice(vocab["expressions"])
                    phrase = f"{phrase} {expression}"
                examples.append(phrase)

        # Add affirmative and expression
        examples.append(random.choice(vocab["affirmatives"]))

        return examples[:6]  # Limit to 6 examples

    def _build_persona_summary(
        self,
        top_traits: List[TraitScore],
        species: Literal["dog", "cat"],
        name: str,
        age: Optional[int],
    ) -> str:
        """Build persona summary paragraph."""
        # Get trait names
        trait_names = [t.trait_name.lower() for t in top_traits[:3]]

        # Build opening
        species_word = "dog" if species == "dog" else "cat"
        age_phrase = f"{age}-year-old " if age else ""

        summary = f"{name} is a {age_phrase}{species_word}"

        # Add trait description
        if len(trait_names) >= 3:
            summary += f" who is {trait_names[0]}, {trait_names[1]}, and {trait_names[2]}."
        elif len(trait_names) == 2:
            summary += f" who is {trait_names[0]} and {trait_names[1]}."
        elif len(trait_names) == 1:
            summary += f" who is {trait_names[0]}."
        else:
            summary += "."

        # Add species-specific flavor
        if species == "dog":
            summary += " They communicate with tail wags, happy barks, and lots of enthusiasm."
        else:
            summary += " They communicate through subtle gestures, purrs, and the occasional meow."

        return summary

    def _generate_quirks(
        self,
        top_traits: List[TraitScore],
        species: Literal["dog", "cat"],
    ) -> List[str]:
        """Generate personality quirks based on traits."""
        quirks = []

        # Species-specific quirks
        if species == "dog":
            base_quirks = [
                "Gets excited about walks",
                "Loves treats",
                "Responds to their name enthusiastically",
                "Has a favorite toy",
            ]
        else:
            base_quirks = [
                "Has specific nap spots",
                "Enjoys window-watching",
                "Has opinions about everything",
                "Values their personal space",
            ]

        quirks.extend(random.sample(base_quirks, min(2, len(base_quirks))))

        # Trait-based quirks
        trait_quirks = {
            "curious": "Always investigating new things",
            "playful": "Never misses a chance to play",
            "lazy": "Expert at finding the best nap spots",
            "clever": "Figures out puzzles quickly",
            "affectionate": "Loves cuddle time",
            "protective": "Always keeps watch over their family",
            "mischievous": "Sometimes gets into trouble (but looks cute doing it)",
            "shy": "Takes time to warm up to new friends",
            "vocal": "Has a lot to say about everything",
        }

        for trait_score in top_traits[:3]:
            trait_id = trait_score.trait_name.lower()
            if trait_id in trait_quirks:
                quirks.append(trait_quirks[trait_id])

        return quirks[:5]  # Limit to 5 quirks
