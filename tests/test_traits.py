"""Tests for trait scoring functionality."""

import pytest

from pet_persona.traits.catalog import TraitCatalog, get_trait_catalog
from pet_persona.traits.lexicon import TraitLexicon, get_trait_lexicon
from pet_persona.traits.scorer import TraitScorer, score_traits


class TestTraitCatalog:
    """Tests for TraitCatalog."""

    def test_load_catalog(self):
        """Test loading the trait catalog."""
        catalog = get_trait_catalog()
        assert catalog is not None
        assert len(catalog.traits) > 0

    def test_get_trait(self):
        """Test getting a specific trait."""
        catalog = get_trait_catalog()
        trait = catalog.get_trait("friendly")
        assert trait is not None
        assert trait.name == "Friendly"
        assert "dog" in trait.applies_to
        assert "cat" in trait.applies_to

    def test_get_traits_for_species(self):
        """Test filtering traits by species."""
        catalog = get_trait_catalog()
        dog_traits = catalog.get_traits_for_species("dog")
        assert len(dog_traits) > 0
        for trait in dog_traits:
            assert "dog" in trait.applies_to

    def test_get_opposite(self):
        """Test getting opposite trait."""
        catalog = get_trait_catalog()
        opposite = catalog.get_opposite("calm")
        assert opposite == "anxious"


class TestTraitLexicon:
    """Tests for TraitLexicon."""

    def test_load_lexicon(self):
        """Test loading the trait lexicon."""
        lexicon = get_trait_lexicon()
        assert lexicon is not None
        assert len(lexicon.mappings) > 0

    def test_find_keyword_matches(self):
        """Test keyword matching."""
        lexicon = get_trait_lexicon()
        text = "This dog is very friendly and playful"
        matches = lexicon.find_keyword_matches(text)
        assert "friendly" in matches
        assert "playful" in matches

    def test_find_phrase_matches(self):
        """Test phrase matching."""
        lexicon = get_trait_lexicon()
        text = "The cat loves to cuddle and is very loving"
        matches = lexicon.find_phrase_matches(text)
        assert "affectionate" in matches

    def test_case_insensitive(self):
        """Test that matching is case insensitive."""
        lexicon = get_trait_lexicon()
        text1 = "FRIENDLY dog"
        text2 = "friendly dog"
        matches1 = lexicon.find_keyword_matches(text1)
        matches2 = lexicon.find_keyword_matches(text2)
        assert "friendly" in matches1
        assert "friendly" in matches2


class TestTraitScorer:
    """Tests for TraitScorer."""

    def test_score_single_text(self):
        """Test scoring a single text."""
        scorer = TraitScorer()
        scores = scorer.score_text("This is a very friendly and playful dog")
        assert len(scores) > 0
        assert "friendly" in scores
        assert scores["friendly"].score > 0

    def test_score_multiple_texts(self):
        """Test scoring multiple texts."""
        texts = [
            "The dog is very energetic and active",
            "Always running and playing",
            "Loves to exercise and play fetch",
        ]
        scores = score_traits(texts)
        assert "active" in scores or "energetic" in scores
        assert any(s.confidence > 0.3 for s in scores.values())

    def test_deterministic_output(self):
        """Test that scoring produces deterministic output."""
        text = "A calm and gentle dog that is very loyal"
        scores1 = score_traits([text])
        scores2 = score_traits([text])

        assert set(scores1.keys()) == set(scores2.keys())
        for trait_id in scores1:
            assert scores1[trait_id].score == scores2[trait_id].score
            assert scores1[trait_id].confidence == scores2[trait_id].confidence

    def test_empty_input(self):
        """Test scoring with empty input."""
        scores = score_traits([])
        assert len(scores) == 0

        scores = score_traits([""])
        assert len(scores) == 0

    def test_evidence_extraction(self):
        """Test that evidence is extracted correctly."""
        text = "This friendly dog loves everyone. Very gentle nature."
        scores = score_traits([text])

        if "friendly" in scores:
            assert len(scores["friendly"].evidence) > 0

    def test_score_range(self):
        """Test that scores are in valid range."""
        text = "Extremely friendly, playful, energetic, and loyal dog"
        scores = score_traits([text])

        for trait_score in scores.values():
            assert 0.0 <= trait_score.score <= 1.0
            assert 0.0 <= trait_score.confidence <= 1.0
