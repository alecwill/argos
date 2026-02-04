"""Tests for personality blending functionality."""

import pytest
from datetime import datetime, timedelta

from pet_persona.db.models import TraitScore, TraitVector


class TestTraitVector:
    """Tests for TraitVector blending."""

    def test_get_top_traits(self):
        """Test getting top traits by score."""
        traits = {
            "friendly": TraitScore(trait_name="Friendly", score=0.9, confidence=0.8, evidence=[]),
            "calm": TraitScore(trait_name="Calm", score=0.5, confidence=0.6, evidence=[]),
            "playful": TraitScore(trait_name="Playful", score=0.7, confidence=0.7, evidence=[]),
        }
        vector = TraitVector(traits=traits)

        top = vector.get_top_traits(n=2)
        assert len(top) == 2
        assert top[0].trait_name == "Friendly"
        assert top[1].trait_name == "Playful"

    def test_blend_with_equal_weights(self):
        """Test blending two vectors with equal weights."""
        traits1 = {
            "friendly": TraitScore(trait_name="Friendly", score=0.8, confidence=0.8, evidence=["e1"]),
        }
        traits2 = {
            "friendly": TraitScore(trait_name="Friendly", score=0.4, confidence=0.6, evidence=["e2"]),
        }

        vector1 = TraitVector(traits=traits1)
        vector2 = TraitVector(traits=traits2)

        blended = vector1.blend_with(vector2, self_weight=0.5)

        # Should be approximately average
        assert 0.5 < blended.traits["friendly"].score < 0.7
        assert len(blended.traits["friendly"].evidence) == 2

    def test_blend_with_different_weights(self):
        """Test blending with different weights."""
        traits1 = {
            "calm": TraitScore(trait_name="Calm", score=1.0, confidence=1.0, evidence=[]),
        }
        traits2 = {
            "calm": TraitScore(trait_name="Calm", score=0.0, confidence=1.0, evidence=[]),
        }

        vector1 = TraitVector(traits=traits1)
        vector2 = TraitVector(traits=traits2)

        # Higher weight on vector1
        blended = vector1.blend_with(vector2, self_weight=0.8)
        assert blended.traits["calm"].score > 0.5

        # Higher weight on vector2
        blended = vector1.blend_with(vector2, self_weight=0.2)
        assert blended.traits["calm"].score < 0.5

    def test_blend_with_decay(self):
        """Test blending with time decay."""
        traits1 = {
            "playful": TraitScore(trait_name="Playful", score=0.8, confidence=0.8, evidence=[]),
        }
        traits2 = {
            "playful": TraitScore(trait_name="Playful", score=0.4, confidence=0.8, evidence=[]),
        }

        vector1 = TraitVector(traits=traits1)
        vector2 = TraitVector(traits=traits2)

        # With decay factor
        blended_with_decay = vector1.blend_with(vector2, self_weight=0.5, decay_factor=0.5)
        blended_no_decay = vector1.blend_with(vector2, self_weight=0.5, decay_factor=1.0)

        # Decay should reduce vector1's influence
        assert blended_with_decay.traits["playful"].score != blended_no_decay.traits["playful"].score

    def test_blend_non_overlapping_traits(self):
        """Test blending vectors with non-overlapping traits."""
        traits1 = {
            "friendly": TraitScore(trait_name="Friendly", score=0.8, confidence=0.8, evidence=[]),
        }
        traits2 = {
            "calm": TraitScore(trait_name="Calm", score=0.6, confidence=0.7, evidence=[]),
        }

        vector1 = TraitVector(traits=traits1)
        vector2 = TraitVector(traits=traits2)

        blended = vector1.blend_with(vector2, self_weight=0.5)

        # Both traits should be present
        assert "friendly" in blended.traits
        assert "calm" in blended.traits

    def test_blend_empty_vectors(self):
        """Test blending with empty vectors."""
        vector1 = TraitVector(traits={})
        vector2 = TraitVector(traits={
            "playful": TraitScore(trait_name="Playful", score=0.7, confidence=0.8, evidence=[]),
        })

        blended = vector1.blend_with(vector2)
        assert "playful" in blended.traits

        blended2 = vector2.blend_with(vector1)
        assert "playful" in blended2.traits

    def test_confidence_blending(self):
        """Test that confidence is properly blended."""
        traits1 = {
            "loyal": TraitScore(trait_name="Loyal", score=0.8,confidence=0.9, evidence=[]),
        }
        traits2 = {
            "loyal": TraitScore(trait_name="Loyal", score=0.8,confidence=0.3, evidence=[]),
        }

        vector1 = TraitVector(traits=traits1)
        vector2 = TraitVector(traits=traits2)

        blended = vector1.blend_with(vector2, self_weight=0.5)

        # Confidence should be between the two values
        assert 0.3 < blended.traits["loyal"].confidence < 0.9

    def test_evidence_combination(self):
        """Test that evidence is properly combined."""
        traits1 = {
            "gentle": TraitScore(
                trait_name="Gentle",
                score=0.7,
                confidence=0.8,
                evidence=["evidence 1", "evidence 2"],
            ),
        }
        traits2 = {
            "gentle": TraitScore(
                trait_name="Gentle",
                score=0.6,
                confidence=0.7,
                evidence=["evidence 3", "evidence 4"],
            ),
        }

        vector1 = TraitVector(traits=traits1)
        vector2 = TraitVector(traits=traits2)

        blended = vector1.blend_with(vector2)

        # Evidence should be combined (but limited)
        assert len(blended.traits["gentle"].evidence) >= 2
        assert len(blended.traits["gentle"].evidence) <= 10  #Limit applied
