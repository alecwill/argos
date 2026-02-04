"""Repository for database operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from pet_persona.db.models import (
    ConversationSession,
    ConversationTurn,
    Document,
    Pet,
    PersonalitySnapshot,
    TraitScore,
    TraitVector,
    User,
    VoiceProfile,
    VoiceProfileModel,
)
from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


class Repository:
    """Repository for all database operations."""

    def __init__(self, session: Session):
        self.session = session

    # ========================================================================
    # User operations
    # ========================================================================

    def create_user(self, username: str, email: Optional[str] = None) -> User:
        """Create a new user."""
        user = User(username=username, email=email)
        self.session.add(user)
        self.session.flush()
        logger.info(f"Created user: {user.id} ({username})")
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.session.get(User, user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        statement = select(User).where(User.username == username)
        return self.session.exec(statement).first()

    def get_or_create_user(self, username: str, email: Optional[str] = None) -> User:
        """Get existing user or create new one."""
        user = self.get_user_by_username(username)
        if user is None:
            user = self.create_user(username, email)
        return user

    # ========================================================================
    # Pet operations
    # ========================================================================

    def create_pet(
        self,
        user_id: str,
        name: str,
        species: str,
        breed: str,
        age: Optional[int] = None,
        sex: Optional[str] = None,
    ) -> Pet:
        """Create a new pet."""
        pet = Pet(
            user_id=user_id,
            name=name,
            species=species.lower(),
            breed=breed,
            age=age,
            sex=sex,
        )
        self.session.add(pet)
        self.session.flush()
        logger.info(f"Created pet: {pet.id} ({name}, {species}- {breed})")
        return pet

    def get_pet(self, pet_id: str) -> Optional[Pet]:
        """Get pet by ID."""
        return self.session.get(Pet, pet_id)

    def get_pets_by_user(self, user_id: str) -> List[Pet]:
        """Get all pets for a user."""
        statement = select(Pet).where(Pet.user_id == user_id)
        return list(self.session.exec(statement).all())

    def update_pet_questionnaire(
        self, pet_id: str, responses: List[Dict[str, Any]]
    ) -> Optional[Pet]:
        """Update pet's questionnaire responses."""
        pet = self.get_pet(pet_id)
        if pet:
            pet.questionnaire_responses = responses
            pet.updated_at = datetime.utcnow()
            self.session.add(pet)
            self.session.flush()
            logger.info(f"Updated questionnaire for pet: {pet_id}")
        return pet

    # ========================================================================
    # Document operations
    # ========================================================================

    def create_document(
        self,
        pet_id: str,
        doc_type: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """Create a new document."""
        doc = Document(
            pet_id=pet_id,
            doc_type=doc_type,
            title=title,
            content=content,
            metadata=metadata or {},
        )
        self.session.add(doc)
        self.session.flush()
        logger.debug(f"Created document: {doc.id} ({doc_type})")
        return doc

    def get_documents_by_pet(
        self, pet_id: str, doc_type: Optional[str] = None
    ) -> List[Document]:
        """Get all documents for a pet."""
        statement = select(Document).where(Document.pet_id == pet_id)
        if doc_type:
            statement = statement.where(Document.doc_type == doc_type)
        return list(self.session.exec(statement).all())

    # ========================================================================
    # Personality snapshot operations
    # ========================================================================

    def create_personality_snapshot(
        self,
        pet_id: str,
        trait_vector: TraitVector,
        evidence_store: Optional[Dict[str, Any]] = None,
    ) -> PersonalitySnapshot:
        """Create a new personality snapshot."""
        # Mark existing snapshots as not current
        existing = self.get_current_snapshot(pet_id)
        if existing:
            existing.is_current = False
            self.session.add(existing)
            version = existing.version + 1
        else:
            version = 1

        # Convert trait vector to dict for storage
        trait_dict = {
            name: {
                "score": ts.score,
                "confidence": ts.confidence,
                "evidence": ts.evidence,
            }
            for name, ts in trait_vector.traits.items()
        }

        snapshot = PersonalitySnapshot(
            pet_id=pet_id,
            version=version,
            trait_vector=trait_dict,
            evidence_store=evidence_store or {},
            is_current=True,
        )
        self.session.add(snapshot)
        self.session.flush()
        logger.info(f"Created personality snapshot v{version} for pet: {pet_id}")
        return snapshot

    def get_current_snapshot(self, pet_id: str) -> Optional[PersonalitySnapshot]:
        """Get the current personality snapshot for a pet."""
        statement = (
            select(PersonalitySnapshot)
            .where(PersonalitySnapshot.pet_id == pet_id)
            .where(PersonalitySnapshot.is_current == True)
        )
        return self.session.exec(statement).first()

    def get_snapshot_history(self, pet_id: str) -> List[PersonalitySnapshot]:
        """Get all personality snapshots for a pet."""
        statement = (
            select(PersonalitySnapshot)
            .where(PersonalitySnapshot.pet_id == pet_id)
            .order_by(PersonalitySnapshot.version.desc())
        )
        return list(self.session.exec(statement).all())

    # ========================================================================
    # Voice profile operations
    # ========================================================================

    def create_voice_profile(self, pet_id: str, voice_profile:VoiceProfile) -> VoiceProfileModel:
        """Create a new voice profile."""
        # Mark existing profiles as not current
        existing = self.get_current_voice_profile(pet_id)
        if existing:
            existing.is_current = False
            self.session.add(existing)

        profile = VoiceProfileModel(
            pet_id=pet_id,
            voice_name=voice_profile.voice_name,
            style_guide=voice_profile.style_guide,
            do_say=voice_profile.do_say,
            dont_say=voice_profile.dont_say,
            example_phrases=voice_profile.example_phrases,
            persona_summary=voice_profile.persona_summary,
            quirks=voice_profile.quirks,
            signature_actions=voice_profile.signature_actions,
            is_current=True,
        )
        self.session.add(profile)
        self.session.flush()
        logger.info(f"Created voice profile for pet: {pet_id}")
        return profile

    def get_current_voice_profile(self, pet_id: str) -> Optional[VoiceProfileModel]:
        """Get the current voice profile for a pet."""
        statement = (
            select(VoiceProfileModel)
            .where(VoiceProfileModel.pet_id == pet_id)
            .where(VoiceProfileModel.is_current == True)
        )
        return self.session.exec(statement).first()

    # ========================================================================
    # Conversation operations
    # ========================================================================

    def create_conversation_session(self, pet_id: str) -> ConversationSession:
        """Create a new conversation session."""
        session = ConversationSession(pet_id=pet_id)
        self.session.add(session)
        self.session.flush()
        logger.debug(f"Created conversation session: {session.id}")
        return session

    def get_conversation_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get a conversation session by ID."""
        return self.session.get(ConversationSession, session_id)

    def add_conversation_turn(
        self,
        session_id: str,
        pet_id: str,
        user_text: str,
        pet_response: str,
        user_mode: str = "text",
        evidence_snippets: Optional[List[str]] = None,
        voice_constraints: Optional[List[str]] = None,
    ) -> ConversationTurn:
        """Add a turn to a conversation."""
        turn = ConversationTurn(
            session_id=session_id,
            pet_id=pet_id,
            user_text=user_text,
            pet_response_text=pet_response,
            user_mode=user_mode,
            retrieved_evidence_snippets=evidence_snippets or [],
            voice_constraints_used=voice_constraints or [],
        )
        self.session.add(turn)
        self.session.flush()
        return turn

    def get_recent_turns(
        self, pet_id: str, limit: int = 10
    ) -> List[ConversationTurn]:
        """Get recent conversation turns for a pet."""
        statement = (
            select(ConversationTurn)
            .where(ConversationTurn.pet_id == pet_id)
            .order_by(ConversationTurn.timestamp.desc())
            .limit(limit)
        )
        turns = list(self.session.exec(statement).all())
        return list(reversed(turns))  # Return in chronological order
