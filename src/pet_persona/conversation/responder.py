"""Pet responder - main conversation engine."""

import random
from typing import Dict, List, Literal, Optional, Tuple

from pet_persona.conversation.intent import Intent, IntentClassifier
from pet_persona.conversation.memory import ConversationMemory
from pet_persona.conversation.safety import SafetyFilter
from pet_persona.db.models import TraitScore, TraitVector, VoiceProfile
from pet_persona.db.repo import Repository
from pet_persona.db.session import get_session
from pet_persona.retrieval.vector_store import FAISSVectorStore, SearchResult
from pet_persona.utils.logging import get_logger
from pet_persona.voice.templates import VoiceTemplates

logger = get_logger(__name__)


class PetResponder:
    """
    Generate pet responses based on personality and context.

    This is the main conversation engine that:
    1. Classifies user intent
    2. Retrieves relevant context from pet profile
    3. Generates personality-driven responses
    4. Applies safety filtering
    """

    def __init__(
        self,
        pet_id: str,
        playful_mode: bool = False,
    ):
        """
        Initialize pet responder.

        Args:
            pet_id: Pet ID to respond as
            playful_mode: If True, generate more expressive responses
        """
        self.pet_id = pet_id
        self.playful_mode = playful_mode

        self.intent_classifier = IntentClassifier()
        self.memory = ConversationMemory()
        self.safety_filter = SafetyFilter()
        self.vector_store: Optional[FAISSVectorStore] = None

        # Load pet data
        self._pet = None
        self._trait_vector: Optional[TraitVector] = None
        self._voice_profile: Optional[VoiceProfile] = None
        self._load_pet_data()

    def _load_pet_data(self) -> None:
        """Load pet data from database."""
        with get_session() as session:
            repo = Repository(session)

            self._pet = repo.get_pet(self.pet_id)
            if not self._pet:
                raise ValueError(f"Pet not found: {self.pet_id}")

            # Load current personality snapshot
            snapshot = repo.get_current_snapshot(self.pet_id)
            if snapshot:
                self._trait_vector = snapshot.to_trait_vector()

            # Load current voice profile
            voice_profile_model = repo.get_current_voice_profile(self.pet_id)
            if voice_profile_model:
                self._voice_profile = voice_profile_model.to_voice_profile()

            # Load documents into vector store
            self._load_documents(repo)

        logger.info(f"Loaded responder for {self._pet.name} ({self._pet.species})")

    def _load_documents(self, repo: Repository) -> None:
        """Load pet documents into vector store for retrieval."""
        documents = repo.get_documents_by_pet(self.pet_id)

        if documents:
            self.vector_store = FAISSVectorStore()
            for doc in documents:
                self.vector_store.add(
                    doc_id=doc.id,
                    content=doc.content,
                    metadata={"type": doc.doc_type, "title": doc.title},
                )
            logger.debug(f"Loaded {len(documents)} documents into vector store")

    def respond(
        self,
        user_text: str,
        session_id: Optional[str] = None,
        debug: bool = False,
    ) -> Dict:
        """
        Generate a response to user input.

        Args:
            user_text: User's message
            session_id: Optional conversation session ID
            debug: If True, include debug info in response

        Returns:
            Dict with response text and optional debug info
        """
        # Check user input for safety concerns
        is_ok, support_message = self.safety_filter.check_user_input(user_text)
        if not is_ok:
            return {
                "response": support_message,
                "intent": "safety_concern",
                "evidence": [],
                "constraints": ["safety_response"],
            }

        # Classify intent
        intent, intent_confidence = self.intent_classifier.classify(user_text)
        logger.debug(f"Classified intent: {intent.value} ({intent_confidence:.2f})")

        # Retrieve relevant evidence
        evidence_snippets = self._retrieve_evidence(user_text)

        # Select voice constraints based on top traits
        voice_constraints = self._select_voice_constraints()

        # Generate response
        response = self._generate_response(
            user_text=user_text,
            intent=intent,
            evidence=evidence_snippets,
            constraints=voice_constraints,
        )

        # Apply safety filtering
        filtered_response, safety_issues = self.safety_filter.filter_response(response)

        # Add to memory
        self.memory.add_turn(
            user_text=user_text,
            pet_response=filtered_response,
            intent=intent.value,
            evidence_used=evidence_snippets[:3],
        )

        # Save to database if session_id provided
        if session_id:
            self._save_turn(session_id, user_text, filtered_response, evidence_snippets, voice_constraints)

        result = {
            "response": filtered_response,
            "intent": intent.value,
        }

        if debug:
            result["evidence"] = evidence_snippets
            result["constraints"] = voice_constraints
            result["safety_issues"] = safety_issues

        return result

    def _retrieve_evidence(self, query: str, k: int = 3) -> List[str]:
        """Retrieve relevant evidence snippets."""
        if not self.vector_store:
            return []

        results = self.vector_store.search(query, k=k)
        return [r.content[:200] for r in results]

    def _select_voice_constraints(self) -> List[str]:
        """Select voice constraints based on top traits."""
        if not self._trait_vector:
            return []

        top_traits = self._trait_vector.get_top_traits(n=3)
        constraints = []

        for trait in top_traits:
            style = VoiceTemplates.get_style_guide(trait.trait_name.lower())
            if style:
                constraints.append(f"{trait.trait_name}: {style.get('tone', '')}")

        return constraints

    def _generate_response(
        self,
        user_text: str,
        intent: Intent,
        evidence: List[str],
        constraints: List[str],
    ) -> str:
        """
        Generate a response using templates and rules.

        This is the MVP rule-based generator. Can be swapped with
        an LLM-based implementation later.
        """
        species = self._pet.species
        name = self._pet.name
        vocab = VoiceTemplates.get_vocabulary(species)

        # Get top traits for personality
        top_traits = []
        if self._trait_vector:
            top_traits = [t.trait_name.lower() for t in self._trait_vector.get_top_traits(n=3)]

        # Build response based on intent
        response_parts = []

        # Intent-specific response templates
        if intent == Intent.GREETING:
            response_parts.append(self._greeting_response(vocab, top_traits))
        elif intent == Intent.FAREWELL:
            response_parts.append(self._farewell_response(vocab, top_traits))
        elif intent == Intent.QUESTION:
            response_parts.append(self._question_response(user_text, vocab, top_traits, evidence))
        elif intent == Intent.BONDING:
            response_parts.append(self._bonding_response(vocab, top_traits))
        elif intent == Intent.PLAY:
            response_parts.append(self._play_response(vocab, top_traits))
        elif intent == Intent.FOOD:
            response_parts.append(self._food_response(vocab, top_traits))
        elif intent == Intent.AFFECTION:
            response_parts.append(self._affection_response(vocab, top_traits))
        elif intent == Intent.HEALTH:
            response_parts.append(self._health_response(vocab,top_traits))
        else:
            response_parts.append(self._general_response(user_text, vocab, top_traits, evidence))

        # Occasionally add signature action (not every time)
        if self._voice_profile and random.random() > 0.6:
            if self._voice_profile.signature_actions:
                response_parts.append(random.choice(self._voice_profile.signature_actions))

        return " ".join(response_parts)

    def _greeting_response(self, vocab: Dict, traits: List[str]) -> str:
        """Generate greeting response."""
        greeting = random.choice(vocab["greetings"])

        if "energetic" in traits or "playful" in traits:
            extras = [
                "I'm so happy to see you!",
                "This is the best!",
                "I've been waiting for you!",
            ]
        elif "calm" in traits or "lazy" in traits:
            extras = [
                "Nice to see you.",
                "Hello there.",
                "Oh, you're back.",
            ]
        elif "affectionate" in traits:
            extras = [
                "I missed you so much!",
                "Come give me some love!",
                "I was thinking about you!",
            ]
        else:
            extras = ["Hello!", "Hi there!", "Hey!"]

        return f"{greeting} {random.choice(extras)}"

    def _farewell_response(self, vocab: Dict, traits: List[str]) -> str:
        """Generate farewell response."""
        if "loyal" in traits or "devoted" in traits:
            responses = [
                "I'll be waiting for you! Come back soon!",
                "I'll miss you! Hurry back!",
                "I'll be right here when you return!",
            ]
        elif "independent" in traits:
            responses = [
                "See you later then.",
                "Alright, catch you later.",
                "Okay, bye for now.",
            ]
        else:
            responses = [
                "Bye bye! Take care!",
                "See you soon!",
                "Goodbye, friend!",
            ]

        return random.choice(responses)

    def _question_response(
        self, question: str, vocab: Dict, traits: List[str], evidence: List[str]
    ) -> str:
        """Generate response to a question."""
        question_lower = question.lower()

        # Common questions
        if "how are you" in question_lower:
            if "happy" in traits or "playful" in traits:
                return "I'm doing great! Life is good when you're around!"
            elif "calm" in traits:
                return "I'm doing well, thanks for asking. Nice and relaxed."
            else:
                return "I'm good! Thanks for asking!"

        if "what do you want" in question_lower or "what wouldyou like" in question_lower:
            templates = VoiceTemplates.get_phrase_templates
            for trait in traits:
                phrases = templates(trait)
                if phrases:
                    return random.choice(phrases)
            return "I'm happy just being here with you!"

        if "do you love me" in question_lower:
            if "affectionate" in traits:
                return "Of course I do! You're my favorite person in the whole world!"
            else:
                return "Yes, I do! You're my human!"

        # Use evidence if available
        if evidence:
            intro = random.choice([
                "Well, I think",
                "From what I know,",
                "Let me tell you,",
            ])
            return f"{intro} {evidence[0][:100]}..."

        # Default curious response
        return random.choice([
            "Hmm, that's an interesting question!",
            "I'm not sure, but I'd love to find out!",
            "Great question! What do you think?",
        ])

    def _bonding_response(self, vocab: Dict, traits: List[str]) -> str:
        """Generate bonding/affection response."""
        if "affectionate" in traits:
            responses = [
                "I love you too! You're the best thing in my life!",
                "Aww, you make me so happy! *nuzzles*",
                "I feel the same way about you! We're best friends forever!",
            ]
        elif "shy" in traits:
            responses = [
                "Oh... that's so nice... I like you too.",
                "*blushes* You're pretty great yourself.",
                "That means a lot to me...",
            ]
        else:
            responses = [
                "You're the best! I'm so lucky to have you!",
                "Aww, I care about you too!",
                "We make a great team, don't we?",
            ]

        expression = random.choice(vocab["expressions"])
        return f"{random.choice(responses)} {expression}"

    def _play_response(self, vocab: Dict, traits: List[str]) -> str:
        """Generate play-related response."""
        if "playful" in traits or "energetic" in traits:
            responses = [
                "Yes yes yes! Let's play! I'm so ready!",
                "Play time! This is the best! What should we do?",
                "Finally! I've been waiting all day for this!",
            ]
        elif "lazy" in traits:
            responses = [
                "Play? Now? Maybe just a little bit...",
                "Okay, but can we also nap after?",
                "I'll play for a bit, but then I need rest.",
            ]
        else:
            responses = [
                "Sure, let's play! What do you want to do?",
                "Sounds fun! I'm in!",
                "Play time is always a good time!",
            ]

        return random.choice(responses)

    def _food_response(self, vocab: Dict, traits: List[str]) -> str:
        """Generate food-related response."""
        expressions = ["*perks up*", "*eyes get big*", "*lickslips*"]

        responses = [
            "Food?! Did someone say food?!",
            "Treats? For me? You're the best!",
            "Is it dinner time? I'm always ready for that!",
            "Yum! Food is one of my favorite things!",
        ]

        return f"{random.choice(expressions)} {random.choice(responses)}"

    def _affection_response(self, vocab: Dict, traits: List[str]) -> str:
        """Generate response to physical affection."""
        if "affectionate" in traits:
            responses = [
                "Oh yes, I love cuddles! More please!",
                "This is the best! Don't ever stop!",
                "I could stay like this forever!",
            ]
        elif "independent" in traits:
            responses = [
                "Okay, but just for a bit.",
                "That's nice... I'll allow it.",
                "Fine, you may pet me.",
            ]
        else:
            responses = [
                "That feels nice!",
                "I like this!",
                "You give the best pets!",
            ]

        expression = random.choice(vocab["expressions"])
        return f"{random.choice(responses)} {expression}"

    def _health_response(self, vocab: Dict, traits: List[str])-> str:
        """Generate health-related response with appropriate caution."""
        return (
            "I'm just a pet, so I'm not the best at health advice. "
            "If you're worried about something, maybe we should ask the vet? "
            "They know a lot more than me about that stuff!"
        )

    def _general_response(
        self, text: str, vocab: Dict, traits: List[str], evidence: List[str]
    ) -> str:
        """Generate general response."""
        # If we have evidence, use it
        if evidence:
            intros = [
                "Interesting!",
                "I see!",
                "Hmm, let me think...",
            ]
            return f"{random.choice(intros)} {evidence[0][:100]}..."

        # Otherwise, generate based on personality
        affirmative = random.choice(vocab["affirmatives"])

        generic_responses = [
            f"{affirmative} That sounds interesting!",
            "Tell me more about that!",
            "I like talking with you!",
            f"{affirmative} What else is on your mind?",
        ]

        return random.choice(generic_responses)

    def _save_turn(
        self,
        session_id: str,
        user_text: str,
        response: str,
        evidence: List[str],
        constraints: List[str],
    ) -> None:
        """Save conversation turn to database."""
        try:
            with get_session() as session:
                repo = Repository(session)
                repo.add_conversation_turn(
                    session_id=session_id,
                    pet_id=self.pet_id,
                    user_text=user_text,
                    pet_response=response,
                    user_mode="text",
                    evidence_snippets=evidence,
                    voice_constraints=constraints,
                )
        except Exception as e:
            logger.error(f"Failed to save conversation turn: {e}")
