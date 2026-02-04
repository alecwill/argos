"""Personality updater for continual learning."""

import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pet_persona.db.models import (
    BreedBaseline,
    Pet,
    QuestionnaireResponse,
    TraitScore,
    TraitVector,
)
from pet_persona.db.repo import Repository
from pet_persona.db.session import get_session
from pet_persona.ingest.wikipedia import WikipediaIngester
from pet_persona.profile.questionnaire import QuestionnaireProcessor
from pet_persona.profile.snapshots import SnapshotManager
from pet_persona.traits import score_traits
from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


class PersonalityUpdater:
    """
    Update pet personality based on new inputs.

    Implements continual learning through weighted blending of:
    - Breed baseline traits
    - User questionnaire responses
    - User stories and notes
    - Historical snapshots (with time decay)
    """

    def __init__(
        self,
        baseline_weight: float = 0.3,
        user_weight: float = 0.5,
        history_weight: float = 0.2,
        decay_half_life_days: float = 30.0,
    ):
        """
        Initialize personality updater.

        Args:
            baseline_weight: Weight for breed baseline traits
            user_weight: Weight for user-provided information
            history_weight: Weight for historical personality data
            decay_half_life_days: Time decay half-life in days
        """
        self.baseline_weight = baseline_weight
        self.user_weight = user_weight
        self.history_weight = history_weight
        self.decay_half_life_days = decay_half_life_days

        self.questionnaire_processor = QuestionnaireProcessor()
        self.snapshot_manager = SnapshotManager()
        self.wikipedia_ingester = WikipediaIngester()

    def _compute_time_decay(self, created_at: datetime) -> float:
        """
        Compute time decay factor for a snapshot.

        Uses exponential decay with configurable half-life.

        Args:
            created_at: Timestamp of the data

        Returns:
            Decay factor between 0 and 1
        """
        age = datetime.utcnow() - created_at
        age_days = age.total_seconds() / 86400

        # Exponential decay: factor = 0.5^(age/half_life)
        decay = math.pow(0.5, age_days / self.decay_half_life_days)
        return max(0.1, decay)  # Minimum factor of 0.1

    def _get_breed_baseline(self, pet: Pet) -> Optional[TraitVector]:
        """
        Get or create breed baseline trait vector.

        Args:
            pet: Pet object

        Returns:
            TraitVector for breed baseline or None
        """
        # Try to load existing baseline
        baseline = self.wikipedia_ingester.load_baseline(pet.breed, pet.species)

        if baseline is None:
            logger.info(f"No baseline found for {pet.species} {pet.breed}, ingesting...")
            baseline = self.wikipedia_ingester.ingest_breed(pet.breed, pet.species)

        if baseline and baseline.extracted_traits:
            return TraitVector(traits=baseline.extracted_traits)

        return None

    def _score_user_documents(self, repo: Repository, pet_id: str) -> TraitVector:
        """
        Score traits from user documents.

        Args:
            repo: Repository instance
            pet_id: Pet ID

        Returns:
            TraitVector from user documents
        """
        documents = repo.get_documents_by_pet(pet_id)

        texts = []
        for doc in documents:
            if doc.doc_type in ("user_story", "questionnaire"):
                texts.append(doc.content)

        if not texts:
            return TraitVector()

        scores = score_traits(texts)
        return TraitVector(traits=scores)

    def _score_questionnaire(
        self, responses: List[QuestionnaireResponse]
    ) -> TraitVector:
        """
        Score traits from questionnaire responses.

        Args:
            responses: List of questionnaire responses

        Returns:
            TraitVector from questionnaire
        """
        if not responses:
            return TraitVector()

        scores = self.questionnaire_processor.score_from_responses(responses)
        return TraitVector(traits=scores)

    def update_personality(
        self,
        pet_id: str,
        new_stories: Optional[List[str]] = None,
        questionnaire_responses: Optional[List[Dict[str, Any]]] = None,
    ) -> TraitVector:
        """
        Update a pet's personality based on all available data.

        This is the main entry point for personality updates.

        Args:
            pet_id: Pet ID
            new_stories: Optional new stories to add
            questionnaire_responses: Optional new questionnaire responses

        Returns:
            Updated TraitVector
        """
        with get_session() as session:
            repo = Repository(session)

            # Get pet
            pet = repo.get_pet(pet_id)
            if not pet:
                raise ValueError(f"Pet not found: {pet_id}")

            logger.info(f"Updating personality for {pet.name} ({pet.species} {pet.breed})")

            # Add new stories as documents
            if new_stories:
                for i, story in enumerate(new_stories):
                    repo.create_document(
                        pet_id=pet_id,
                        doc_type="user_story",
                        title=f"Story {i + 1}",
                        content=story,
                    )

            # Process questionnaire responses
            qr_trait_vector = TraitVector()
            if questionnaire_responses:
                responses = [
                    QuestionnaireResponse(**r) for r in questionnaire_responses
                ]
                qr_trait_vector = self._score_questionnaire(responses)
                pet.questionnaire_responses = questionnaire_responses
                session.add(pet)

            # Get components for blending
            components = []

            # 1. Breed baseline
            baseline_vector = self._get_breed_baseline(pet)
            if baseline_vector and baseline_vector.traits:
                components.append(
                    ("baseline", baseline_vector, self.baseline_weight)
                )
                logger.debug(f"Added baseline with {len(baseline_vector.traits)} traits")

            # 2. User documents (stories)
            user_vector = self._score_user_documents(repo, pet_id)
            if user_vector.traits:
                components.append(("user_docs", user_vector, self.user_weight * 0.5))
                logger.debug(f"Added user docs with {len(user_vector.traits)} traits")

            # 3. Questionnaire
            if qr_trait_vector.traits:
                components.append(
                    ("questionnaire", qr_trait_vector, self.user_weight * 0.5)
                )
                logger.debug(
                    f"Added questionnaire with {len(qr_trait_vector.traits)} traits"
                )

            # 4. Historical personality (with decay)
            current_snapshot = repo.get_current_snapshot(pet_id)
            if current_snapshot:
                decay = self._compute_time_decay(current_snapshot.created_at)
                history_vector = current_snapshot.to_trait_vector()
                if history_vector.traits:
                    components.append(
                        ("history", history_vector, self.history_weight * decay)
                    )
                    logger.debug(
                        f"Added history with {len(history_vector.traits)} traits, "
                        f"decay={decay:.2f}"
                    )

            # Blend all components
            final_vector = self._blend_components(components)

            # Create new snapshot
            evidence_store = {
                "sources": [name for name, _, _ in components],
                "weights": {name: weight for name, _, weight in components},
            }

            snapshot_manager = SnapshotManager(repo)
            snapshot_manager.create_snapshot(
                pet_id=pet_id,
                trait_vector=final_vector,
                evidence_store=evidence_store,
            )

            logger.info(
                f"Updated personality with {len(final_vector.traits)} traits "
                f"from {len(components)} sources"
            )

            return final_vector

    def _blend_components(
        self, components: List[tuple]
    ) -> TraitVector:
        """
        Blend multiple trait vector components.

        Args:
            components: List of (name, TraitVector, weight) tuples

        Returns:
            Blended TraitVector
        """
        if not components:
            return TraitVector()

        # Normalize weights
        total_weight = sum(w for _, _, w in components)
        if total_weight == 0:
            return TraitVector()

        # Collect all trait IDs
        all_traits = set()
        for _, vector, _ in components:
            all_traits.update(vector.traits.keys())

        # Blend each trait
        blended_traits = {}

        for trait_id in all_traits:
            weighted_scores = []
            weighted_confidences = []
            all_evidence = []
            total_contrib_weight = 0

            for name, vector, weight in components:
                if trait_id in vector.traits:
                    ts = vector.traits[trait_id]
                    normalized_weight = weight / total_weight
                    weighted_scores.append(ts.score * normalized_weight)
                    weighted_confidences.append(ts.confidence * normalized_weight)
                    all_evidence.extend(ts.evidence[:2])  # Limit evidence per source
                    total_contrib_weight += normalized_weight

            if total_contrib_weight > 0:
                # Normalize by contributing weight
                final_score = sum(weighted_scores) / total_contrib_weight
                final_confidence = sum(weighted_confidences) /total_contrib_weight

                # Get trait name from catalog
                from pet_persona.traits import get_trait_catalog

                catalog = get_trait_catalog()
                trait_def = catalog.get_trait(trait_id)
                trait_name = trait_def.name if trait_def else trait_id

                blended_traits[trait_id] = TraitScore(
                    trait_name=trait_name,
                    score=round(final_score, 3),
                    confidence=round(final_confidence, 3),
                    evidence=all_evidence[:5],  # Limit total evidence
                )

        return TraitVector(traits=blended_traits)
