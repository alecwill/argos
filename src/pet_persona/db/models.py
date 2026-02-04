"""SQLModel database models for Pet Persona AI."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field as PydanticField
from sqlmodel import Column, Field, JSON, Relationship, SQLModel


# ============================================================================
# Pydantic Models (for data transfer and validation)
# ============================================================================


class TraitScore(BaseModel):
    """Score for a single personality trait."""

    trait_name: str
    score: float = PydanticField(ge=0.0, le=1.0, description="Trait score from 0-1")
    confidence: float = PydanticField(ge=0.0, le=1.0, description="Confidence in the score")
    evidence: List[str] = PydanticField(default_factory=list, description="Supporting evidence")


class TraitVector(BaseModel):
    """Complete personality trait vector."""

    traits: Dict[str, TraitScore] = PydanticField(default_factory=dict)
    computed_at: datetime = PydanticField(default_factory=datetime.utcnow)

    def get_top_traits(self, n: int = 5) -> List[TraitScore]:
        """Get top N traits by score."""
        sorted_traits = sorted(self.traits.values(), key=lambda t: t.score, reverse=True)
        return sorted_traits[:n]

    def blend_with(
        self, other: "TraitVector", self_weight: float = 0.5, decay_factor: float = 1.0
    ) -> "TraitVector":
        """Blend this trait vector with another using weightedaverage."""
        all_traits = set(self.traits.keys()) | set(other.traits.keys())
        blended = {}

        for trait_name in all_traits:
            self_trait = self.traits.get(trait_name)
            other_trait = other.traits.get(trait_name)

            if self_trait and other_trait:
                # Weighted blend
                adjusted_self_weight = self_weight * decay_factor
                adjusted_other_weight = (1 - self_weight)

                total_weight = adjusted_self_weight + adjusted_other_weight
                blended_score = (
                    self_trait.score * adjusted_self_weight
                    + other_trait.score * adjusted_other_weight
                ) / total_weight
                blended_confidence = (
                    self_trait.confidence * adjusted_self_weight
                    + other_trait.confidence * adjusted_other_weight
                ) / total_weight

                evidence = self_trait.evidence + other_trait.evidence
                blended[trait_name] = TraitScore(
                    trait_name=trait_name,
                    score=blended_score,
                    confidence=blended_confidence,
                    evidence=evidence[:10],  # Limit evidence
                )
            elif self_trait:
                blended[trait_name] = self_trait.model_copy()
            else:
                blended[trait_name] = other_trait.model_copy()

        return TraitVector(traits=blended)


class SourceDoc(BaseModel):
    """Metadata for a source document."""

    source_type: Literal["wikipedia", "youtube", "user_story","questionnaire"]
    source_id: str
    title: str
    url: Optional[str] = None
    content: str
    fetched_at: datetime = PydanticField(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = PydanticField(default_factory=dict)


class BreedBaseline(BaseModel):
    """Baseline personality profile for a breed."""

    species: Literal["dog", "cat"]
    breed_name: str
    sources: List[SourceDoc] = PydanticField(default_factory=list)
    extracted_traits: Dict[str, TraitScore] = PydanticField(default_factory=dict)
    summary: str = ""
    created_at: datetime = PydanticField(default_factory=datetime.utcnow)
    updated_at: datetime = PydanticField(default_factory=datetime.utcnow)


class VoiceProfile(BaseModel):
    """Voice/personality profile for a pet."""

    voice_name: str
    style_guide: List[str] = PydanticField(default_factory=list)
    do_say: List[str] = PydanticField(default_factory=list)
    dont_say: List[str] = PydanticField(default_factory=list)
    example_phrases: List[str] = PydanticField(default_factory=list)
    persona_summary: str = ""
    quirks: List[str] = PydanticField(default_factory=list)
    signature_actions: List[str] = PydanticField(default_factory=list)


class QuestionnaireResponse(BaseModel):
    """User's questionnaire responses about their pet."""

    question_id: str
    question_text: str
    answer: str
    category: Optional[str] = None


class SpeechConfig(BaseModel):
    """Configuration for speech features."""

    stt_provider: Literal["faster_whisper", "none"] = "faster_whisper"
    tts_provider: Literal["pyttsx3", "none"] = "pyttsx3"
    language: str = "en"
    device: Optional[str] = None
    sample_rate: int = 16000


# ============================================================================
# SQLModel Database Models
# ============================================================================


class User(SQLModel, table=True):
    """User account."""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    username: str = Field(index=True, unique=True)
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    pets: List["Pet"] = Relationship(back_populates="owner")


class Pet(SQLModel, table=True):
    """Pet profile."""

    __tablename__ = "pets"
    __table_args__ = {"extend_existing": True}

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    name: str
    species: str  # "dog" or "cat"
    breed: str
    age: Optional[int] = None
    sex: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Questionnaire responses stored as JSON
    questionnaire_responses: Optional[List[Dict[str, Any]]] = Field(
        default=None, sa_column=Column(JSON)
    )

    # Relationships
    owner: Optional[User] = Relationship(back_populates="pets")
    documents: List["Document"] = Relationship(back_populates="pet")
    snapshots: List["PersonalitySnapshot"] = Relationship(back_populates="pet")
    voice_profiles: List["VoiceProfileModel"] = Relationship(back_populates="pet")
    conversation_sessions: List["ConversationSession"] = Relationship(back_populates="pet")


class Document(SQLModel, table=True):
    """Document associated with a pet or breed."""

    __tablename__ = "documents"
    __table_args__ = {"extend_existing": True}

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    pet_id: Optional[str] = Field(default=None, foreign_key="pets.id", index=True)
    doc_type: str  # "user_story", "media_metadata", "questionnaire", etc.
    title: str
    content: str
    doc_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    pet: Optional[Pet] = Relationship(back_populates="documents")


class PersonalitySnapshot(SQLModel, table=True):
    """Snapshot of pet's personality at a point in time."""

    __tablename__ = "personality_snapshots"
    __table_args__ = {"extend_existing": True}

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    pet_id: str = Field(foreign_key="pets.id", index=True)
    version: int = Field(default=1)
    trait_vector: Dict[str, Any] = Field(default_factory=dict,sa_column=Column(JSON))
    evidence_store: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_current: bool = Field(default=True)

    # Relationships
    pet: Optional[Pet] = Relationship(back_populates="snapshots")

    def to_trait_vector(self) -> TraitVector:
        """Convert stored dict to TraitVector."""
        traits = {}
        for name, data in self.trait_vector.items():
            traits[name] = TraitScore(
                trait_name=name,
                score=data.get("score", 0.0),
                confidence=data.get("confidence", 0.0),
                evidence=data.get("evidence", []),
            )
        return TraitVector(traits=traits)


class VoiceProfileModel(SQLModel, table=True):
    """Stored voice profile for a pet."""

    __tablename__ = "voice_profiles"
    __table_args__ = {"extend_existing": True}

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    pet_id: str = Field(foreign_key="pets.id", index=True)
    voice_name: str
    style_guide: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    do_say: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    dont_say: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    example_phrases: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    persona_summary: str = ""
    quirks: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    signature_actions: List[str] = Field(default_factory=list,sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_current: bool = Field(default=True)

    # Relationships
    pet: Optional[Pet] = Relationship(back_populates="voice_profiles")

    def to_voice_profile(self) -> VoiceProfile:
        """Convert to VoiceProfile pydantic model."""
        return VoiceProfile(
            voice_name=self.voice_name,
            style_guide=self.style_guide,
            do_say=self.do_say,
            dont_say=self.dont_say,
            example_phrases=self.example_phrases,
            persona_summary=self.persona_summary,
            quirks=self.quirks,
            signature_actions=self.signature_actions,
        )


class ConversationSession(SQLModel, table=True):
    """Conversation session with a pet."""

    __tablename__ = "conversation_sessions"
    __table_args__ = {"extend_existing": True}

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    pet_id: str = Field(foreign_key="pets.id", index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    running_summary: Optional[str] = None

    # Relationships
    pet: Optional[Pet] = Relationship(back_populates="conversation_sessions")
    turns: List["ConversationTurn"] = Relationship(back_populates="session")


class ConversationTurn(SQLModel, table=True):
    """Single turn in a conversation."""

    __tablename__ = "conversation_turns"
    __table_args__ = {"extend_existing": True}

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="conversation_sessions.id", index=True)
    pet_id: str = Field(index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_text: str
    user_mode: str = "text"  # "text" or "voice"
    pet_response_text: str
    retrieved_evidence_snippets: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    voice_constraints_used: List[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Relationships
    session: Optional[ConversationSession] = Relationship(back_populates="turns")
