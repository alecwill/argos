"""Personality snapshot management."""

from datetime import datetime
from typing import List, Optional

from pet_persona.db.models import PersonalitySnapshot, TraitVector
from pet_persona.db.repo import Repository
from pet_persona.db.session import get_session
from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


class SnapshotManager:
    """Manage personality snapshots for pets."""

    def __init__(self, repo: Optional[Repository] = None):
        """
        Initialize snapshot manager.

        Args:
            repo: Repository instance (creates one if None)
        """
        self._repo = repo
        self._session = None

    @property
    def repo(self) -> Repository:
        """Get repository, creating session if needed."""
        if self._repo is None:
            from pet_persona.db.session import get_session_direct
            self._session = get_session_direct()
            self._repo = Repository(self._session)
        return self._repo

    def create_snapshot(
        self,
        pet_id: str,
        trait_vector: TraitVector,
        evidence_store: Optional[dict] = None,
    ) -> PersonalitySnapshot:
        """
        Create a new personality snapshot.

        This will mark any existing current snapshot as not current.

        Args:
            pet_id: Pet ID
            trait_vector: Personality trait vector
            evidence_store: Optional evidence storage

        Returns:
            New PersonalitySnapshot
        """
        snapshot = self.repo.create_personality_snapshot(
            pet_id=pet_id,
            trait_vector=trait_vector,
            evidence_store=evidence_store or {},
        )
        if self._session:
            self._session.commit()
        logger.info(f"Created snapshot v{snapshot.version} forpet {pet_id}")
        return snapshot

    def get_current(self, pet_id: str) -> Optional[PersonalitySnapshot]:
        """
        Get the current personality snapshot for a pet.

        Args:
            pet_id: Pet ID

        Returns:
            Current PersonalitySnapshot or None
        """
        return self.repo.get_current_snapshot(pet_id)

    def get_history(self, pet_id: str) -> List[PersonalitySnapshot]:
        """
        Get all personality snapshots for a pet.

        Args:
            pet_id: Pet ID

        Returns:
            List of snapshots, newest first
        """
        return self.repo.get_snapshot_history(pet_id)

    def get_trait_vector(self, pet_id: str) -> Optional[TraitVector]:
        """
        Get the current trait vector for a pet.

        Args:
            pet_id: Pet ID

        Returns:
            TraitVector or None if no snapshot exists
        """
        snapshot = self.get_current(pet_id)
        if snapshot:
            return snapshot.to_trait_vector()
        return None

    def compare_snapshots(
        self, pet_id: str, version1: int, version2: int
    ) -> dict:
        """
        Compare two personality snapshots.

        Args:
            pet_id: Pet ID
            version1: First version number
            version2: Second version number

        Returns:
            Dict with comparison results
        """
        history = self.get_history(pet_id)
        snapshots = {s.version: s for s in history}

        if version1 not in snapshots or version2 not in snapshots:
            return {"error": "Version not found"}

        snap1 = snapshots[version1]
        snap2 = snapshots[version2]

        tv1 = snap1.to_trait_vector()
        tv2 = snap2.to_trait_vector()

        # Find trait differences
        all_traits = set(tv1.traits.keys()) | set(tv2.traits.keys())
        changes = {}

        for trait_id in all_traits:
            score1 = tv1.traits.get(trait_id)
            score2 = tv2.traits.get(trait_id)

            if score1 and score2:
                diff = score2.score - score1.score
                if abs(diff) > 0.05:  # Significant change threshold
                    changes[trait_id] = {
                        "before": score1.score,
                        "after": score2.score,
                        "change": round(diff, 3),
                    }
            elif score1:
                changes[trait_id] = {
                    "before": score1.score,
                    "after": None,
                    "change": "removed",
                }
            else:
                changes[trait_id] = {
                    "before": None,
                    "after": score2.score,
                    "change": "added",
                }

        return {
            "version1": version1,
            "version2": version2,
            "changes": changes,
            "total_traits_v1": len(tv1.traits),
            "total_traits_v2": len(tv2.traits),
        }
