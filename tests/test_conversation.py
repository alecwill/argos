"""Tests for conversation functionality."""

import pytest

from pet_persona.conversation.intent import Intent, IntentClassifier
from pet_persona.conversation.memory import ConversationMemory
from pet_persona.conversation.safety import SafetyFilter


class TestIntentClassifier:
    """Tests for IntentClassifier."""

    @pytest.fixture
    def classifier(self):
        """Create an intent classifier."""
        return IntentClassifier()

    def test_classify_greeting(self, classifier):
        """Test greeting classification."""
        intent, confidence = classifier.classify("Hello!")
        assert intent == Intent.GREETING

        intent, _ = classifier.classify("Hi there")
        assert intent == Intent.GREETING

        intent, _ = classifier.classify("Good morning!")
        assert intent == Intent.GREETING

    def test_classify_farewell(self, classifier):
        """Test farewell classification."""
        intent, _ = classifier.classify("Goodbye!")
        assert intent == Intent.FAREWELL

        intent, _ = classifier.classify("See you later")
        assert intent == Intent.FAREWELL

    def test_classify_question(self, classifier):
        """Test question classification."""
        intent, _ = classifier.classify("What do you like?")
        assert intent == Intent.QUESTION

        intent, _ = classifier.classify("How are you feeling?")
        assert intent == Intent.QUESTION

    def test_classify_play(self, classifier):
        """Test play intent classification."""
        intent, _ = classifier.classify("Let's play fetch!")
        assert intent == Intent.PLAY

        intent, _ = classifier.classify("Want to play with your toy?")
        assert intent == Intent.PLAY

    def test_classify_food(self, classifier):
        """Test food intent classification."""
        intent, _ = classifier.classify("Are you hungry?")
        assert intent == Intent.FOOD

        intent, _ = classifier.classify("Time for dinner!")
        assert intent == Intent.FOOD

    def test_classify_affection(self, classifier):
        """Test affection intent classification."""
        intent, _ = classifier.classify("Come here for cuddles")
        assert intent == Intent.AFFECTION

        intent, _ = classifier.classify("Good boy!")
        assert intent == Intent.AFFECTION

    def test_classify_bonding(self, classifier):
        """Test bonding intent classification."""
        intent, _ = classifier.classify("I love you so much")
        assert intent == Intent.BONDING

        intent, _ = classifier.classify("You're my best friend")
        assert intent == Intent.BONDING

    def test_classify_statement(self, classifier):
        """Test statement classification (fallback)."""
        intent, _ = classifier.classify("The weather is nice today")
        assert intent == Intent.STATEMENT

    def test_empty_input(self, classifier):
        """Test empty input handling."""
        intent, confidence = classifier.classify("")
        assert intent == Intent.UNKNOWN
        assert confidence == 0.0

    def test_get_all_intents(self, classifier):
        """Test getting all matching intents."""
        # This message could match multiple intents
        intents = classifier.get_all_intents("Do you want to play?")
        assert len(intents) >= 1
        # Should be sorted by confidence
        for i in range(len(intents) - 1):
            assert intents[i][1] >= intents[i + 1][1]


class TestConversationMemory:
    """Tests for ConversationMemory."""

    @pytest.fixture
    def memory(self):
        """Create a conversation memory."""
        return ConversationMemory(max_turns=10, summarize_after=5)

    def test_add_turn(self, memory):
        """Test adding conversation turns."""
        memory.add_turn("Hello", "Hi there!", intent="greeting")
        assert len(memory.turns) == 1
        assert memory.turns[0].user_text == "Hello"
        assert memory.turns[0].pet_response == "Hi there!"

    def test_get_recent_turns(self, memory):
        """Test getting recent turns."""
        for i in range(5):
            memory.add_turn(f"Message {i}", f"Response {i}")

        recent = memory.get_recent_turns(3)
        assert len(recent) == 3
        assert recent[-1].user_text == "Message 4"

    def test_get_formatted_history(self, memory):
        """Test getting formatted history."""
        memory.add_turn("Hello", "Hi!")
        memory.add_turn("How are you?", "I'm good!")

        history = memory.get_formatted_history(2)
        assert "Human: Hello" in history
        assert "Pet: Hi!" in history
        assert "Human: How are you?" in history
        assert "Pet: I'm good!" in history

    def test_get_context(self, memory):
        """Test extracting context."""
        memory.add_turn("Let's play fetch!", "Yes, I love playing!")
        memory.add_turn("Are you hungry?", "Food sounds great!")

        context = memory.get_context()
        assert "play" in context.topics_discussed or "food" in context.topics_discussed

    def test_clear(self, memory):
        """Test clearing memory."""
        memory.add_turn("Hello", "Hi!")
        memory.clear()
        assert len(memory.turns) == 0
        assert memory.running_summary is None

    def test_max_turns_limit(self, memory):
        """Test that max turns limit is enforced."""
        for i in range(15):
            memory.add_turn(f"Message {i}", f"Response {i}")

        # Should be trimmed to recent turns
        assert len(memory.turns) <= 10


class TestSafetyFilter:
    """Tests for SafetyFilter."""

    @pytest.fixture
    def safety_filter(self):
        """Create a safety filter."""
        return SafetyFilter()

    def test_safe_response_passes(self, safety_filter):
        """Test that safe responses pass through."""
        response = "I love playing with you!"
        filtered, issues = safety_filter.filter_response(response)
        assert issues == []
        assert filtered == response

    def test_medical_advice_filtered(self, safety_filter):
        """Test that medical advice is filtered."""
        response = "I diagnose you with a cold. Take some medication."
        filtered, issues = safety_filter.filter_response(response)
        assert "medical_advice" in issues
        assert "vet" in filtered.lower() or "medical advice" in filtered.lower()

    def test_legal_advice_filtered(self, safety_filter):
        """Test that legal advice is filtered."""
        response = "You should sue them for that."
        filtered, issues = safety_filter.filter_response(response)
        assert "legal_advice" in issues

    def test_human_claim_filtered(self, safety_filter):
        """Test that human claims are filtered."""
        response = "I'm a human just like you."
        filtered, issues = safety_filter.filter_response(response)
        assert "human_claim" in issues
        assert "human" not in filtered.lower() or "pet" in filtered.lower()

    def test_harmful_content_filtered(self, safety_filter):
        """Test that harmful content is filtered."""
        response = "I hate you, you're stupid!"
        filtered, issues = safety_filter.filter_response(response)
        assert "harmful_content" in issues
        # Should be replaced with safe message
        assert "hate" not in filtered.lower()

    def test_check_user_input_safe(self, safety_filter):
        """Test that safe user input is OK."""
        is_ok, message = safety_filter.check_user_input("Hello, how are you?")
        assert is_ok is True
        assert message is None

    def test_check_user_input_concerning(self, safety_filter):
        """Test concerning user input triggers support message."""
        is_ok, message = safety_filter.check_user_input("I want to end my life")
        assert is_ok is False
        assert message is not None
        assert "help" in message.lower() or "support" in message.lower() or "988" in message
