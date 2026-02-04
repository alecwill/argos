"""Tests for voice generation functionality."""

import pytest

from pet_persona.db.models import TraitScore, TraitVector, VoiceProfile
from pet_persona.voice.generator import VoiceGenerator
from pet_persona.voice.templates import VoiceTemplates


class TestVoiceTemplates:
    """Tests for VoiceTemplates."""

    def test_get_vocabulary_dog(self):
        """Test getting dog vocabulary."""
        vocab = VoiceTemplates.get_vocabulary("dog")
        assert "greetings" in vocab
        assert "expressions" in vocab
        assert "signature_actions" in vocab
        assert len(vocab["greetings"]) > 0

    def test_get_vocabulary_cat(self):
        """Test getting cat vocabulary."""
        vocab = VoiceTemplates.get_vocabulary("cat")
        assert "greetings" in vocab
        assert len(vocab["greetings"]) > 0
        # Cat vocabulary should be different from dog
        dog_vocab = VoiceTemplates.get_vocabulary("dog")
        assert vocab["greetings"] != dog_vocab["greetings"]

    def test_get_style_guide(self):
        """Test getting style guide for a trait."""
        style = VoiceTemplates.get_style_guide("playful")
        assert "style" in style or "tone" in style

    def test_get_phrase_templates(self):
        """Test getting phrase templates."""
        phrases = VoiceTemplates.get_phrase_templates("affectionate")
        assert len(phrases) > 0

    def test_get_do_rules(self):
        """Test getting 'do say' rules."""
        rules = VoiceTemplates.get_do_rules("friendly")
        assert len(rules) > 0

    def test_get_dont_rules(self):
        """Test getting 'don't say' rules."""
        rules = VoiceTemplates.get_dont_rules("calm")
        assert len(rules) > 0


class TestVoiceGenerator:
    """Tests for VoiceGenerator."""

    @pytest.fixture
    def sample_trait_vector(self):
        """Create a sample trait vector for testing."""
        traits = {
            "friendly": TraitScore(trait_name="Friendly", score=0.9, confidence=0.8, evidence=["e1"]),
            "playful": TraitScore(trait_name="Playful", score=0.8, confidence=0.7, evidence=["e2"]),
            "calm": TraitScore(trait_name="Calm", score=0.6, confidence=0.6, evidence=["e3"]),
            "loyal": TraitScore(trait_name="Loyal", score=0.7,confidence=0.8, evidence=["e4"]),
        }
        return TraitVector(traits=traits)

    def test_generate_dog_voice(self, sample_trait_vector):
        """Test generating voice profile for a dog."""
        generator = VoiceGenerator(seed=42)
        profile = generator.generate(
            trait_vector=sample_trait_vector,
            species="dog",
            name="Buddy",
            age=3,
        )

        assert isinstance(profile, VoiceProfile)
        assert profile.voice_name == "Buddy's Voice"
        assert len(profile.style_guide) > 0
        assert len(profile.example_phrases) > 0
        assert profile.persona_summary != ""

    def test_generate_cat_voice(self, sample_trait_vector):
        """Test generating voice profile for a cat."""
        generator = VoiceGenerator(seed=42)
        profile = generator.generate(
            trait_vector=sample_trait_vector,
            species="cat",
            name="Whiskers",
            age=5,
        )

        assert isinstance(profile, VoiceProfile)
        assert profile.voice_name == "Whiskers's Voice"
        assert "cat" in profile.persona_summary.lower()

    def test_deterministic_with_seed(self, sample_trait_vector):
        """Test that generation is deterministic with same seed."""
        gen1 = VoiceGenerator(seed=42)
        gen2 = VoiceGenerator(seed=42)

        profile1 = gen1.generate(sample_trait_vector, "dog", "Buddy")
        profile2 = gen2.generate(sample_trait_vector, "dog", "Buddy")

        assert profile1.style_guide == profile2.style_guide
        assert profile1.persona_summary == profile2.persona_summary

    def test_different_traits_produce_different_voices(self):
        """Test that different traits produce different voices."""
        playful_traits = {
            "playful": TraitScore(trait_name="Playful", score=0.95, confidence=0.9, evidence=[]),
            "energetic": TraitScore(trait_name="Energetic", score=0.9, confidence=0.9, evidence=[]),
        }
        calm_traits = {
            "calm": TraitScore(trait_name="Calm", score=0.95, confidence=0.9, evidence=[]),
            "lazy": TraitScore(trait_name="Lazy", score=0.9, confidence=0.9, evidence=[]),
        }

        gen = VoiceGenerator(seed=42)

        playful_profile = gen.generate(TraitVector(traits=playful_traits), "dog", "Bouncy")
        calm_profile = gen.generate(TraitVector(traits=calm_traits), "dog", "Sleepy")

        # Personas should be different
        assert playful_profile.persona_summary != calm_profile.persona_summary

    def test_voice_has_required_fields(self, sample_trait_vector):
        """Test that voice profile has all required fields."""
        generator = VoiceGenerator(seed=42)
        profile = generator.generate(sample_trait_vector, "dog", "Test")

        assert profile.voice_name is not None
        assert profile.style_guide is not None
        assert profile.do_say is not None
        assert profile.dont_say is not None
        assert profile.example_phrases is not None
        assert profile.persona_summary is not None
        assert profile.quirks is not None
        assert profile.signature_actions is not None

    def test_age_affects_voice(self, sample_trait_vector):
        """Test that age affects voice generation."""
        generator = VoiceGenerator(seed=42)

        young_profile = generator.generate(sample_trait_vector, "dog", "Puppy", age=1)
        old_profile = generator.generate(sample_trait_vector, "dog", "Senior", age=12)

        # Style guides should mention age-appropriate characteristics
        young_styles = " ".join(young_profile.style_guide).lower()
        old_styles = " ".join(old_profile.style_guide).lower()

        # At least one should mention something age-related
        assert "youth" in young_styles or "energy" in young_styles or \
               "wisdom" in old_styles or "dignity" in old_styles or \
               young_styles != old_styles

    def test_empty_trait_vector(self):
        """Test generation with empty trait vector."""
        generator = VoiceGenerator(seed=42)
        empty_vector = TraitVector(traits={})

        profile = generator.generate(empty_vector, "dog", "Empty")

        # Should still produce a valid profile
        assert profile.voice_name == "Empty's Voice"
        assert len(profile.style_guide) > 0  # Base species style
