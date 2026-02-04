"""Vector store for document retrieval."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from pet_persona.retrieval.embeddings import EmbeddingModel, get_embedding_model
from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Result from vector search."""

    doc_id: str
    content: str
    score: float
    metadata: Dict[str, Any]


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a document to the store.

        Args:
            doc_id: Unique document identifier
            content: Document text content
            metadata: Optional metadata dict
        """
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Search for similar documents.

        Args:
            query: Search query text
            k: Number of results to return
            filter_metadata: Optional metadata filter

        Returns:
            List of SearchResult objects
        """
        pass

    @abstractmethod
    def delete(self, doc_id: str) -> bool:
        """
        Delete a document from the store.

        Args:
            doc_id: Document identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all documents from the store."""
        pass

    @property
    @abstractmethod
    def count(self) -> int:
        """Get number of documents in the store."""
        pass


class InMemoryVectorStore(VectorStore):
    """Simple in-memory vector store using numpy."""

    def __init__(self, embedding_model: Optional[EmbeddingModel] = None):
        """
        Initialize in-memory vector store.

        Args:
            embedding_model: Embedding model (uses default if None)
        """
        self.embedding_model = embedding_model or get_embedding_model()
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.embeddings: Dict[str, np.ndarray] = {}

    def add(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a document to the store."""
        embedding = self.embedding_model.embed(content)
        self.documents[doc_id] = {
            "content": content,
            "metadata": metadata or {},
        }
        self.embeddings[doc_id] = embedding
        logger.debug(f"Added document to vector store: {doc_id}")

    def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar documents."""
        if not self.embeddings:
            return []

        query_embedding = self.embedding_model.embed(query)

        # Calculate similarities
        similarities: List[Tuple[str, float]] = []
        for doc_id, doc_embedding in self.embeddings.items():
            # Apply metadata filter
            if filter_metadata:
                doc_meta = self.documents[doc_id]["metadata"]
                if not all(
                    doc_meta.get(k) == v for k, v in filter_metadata.items()
                ):
                    continue

            # Cosine similarity
            similarity = np.dot(query_embedding, doc_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding) + 1e-8
            )
            similarities.append((doc_id, float(similarity)))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Return top k results
        results = []
        for doc_id, score in similarities[:k]:
            doc = self.documents[doc_id]
            results.append(
                SearchResult(
                    doc_id=doc_id,
                    content=doc["content"],
                    score=score,
                    metadata=doc["metadata"],
                )
            )

        return results

    def delete(self, doc_id: str) -> bool:
        """Delete a document from the store."""
        if doc_id in self.documents:
            del self.documents[doc_id]
            del self.embeddings[doc_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all documents."""
        self.documents.clear()
        self.embeddings.clear()

    @property
    def count(self) -> int:
        """Get document count."""
        return len(self.documents)


class FAISSVectorStore(VectorStore):
    """Vector store using FAISS for efficient similarity search."""

    def __init__(
        self,
        embedding_model: Optional[EmbeddingModel] = None,
        index_path: Optional[Path] = None,
    ):
        """
        Initialize FAISS vector store.

        Args:
            embedding_model: Embedding model (uses default if None)
            index_path: Optional path to save/load index
        """
        self.embedding_model = embedding_model or get_embedding_model()
        self.index_path = index_path
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.id_to_idx: Dict[str, int] = {}
        self.idx_to_id: Dict[int, str] = {}
        self._index = None
        self._next_idx = 0

        # Try to import FAISS
        try:
            import faiss
            self._faiss = faiss
        except ImportError:
            logger.warning(
                "FAISS not available, falling back to in-memory store. "
                "For better performance, install faiss-cpu."
            )
            self._faiss = None

    @property
    def index(self):
        """Get or create FAISS index."""
        if self._index is None and self._faiss is not None:
            dimension = self.embedding_model.dimension
            self._index = self._faiss.IndexFlatIP(dimension)  # Inner product (cosine)
            logger.debug(f"Created FAISS index with dimension {dimension}")
        return self._index

    def add(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a document to the store."""
        if self._faiss is None:
            # Fallback to simple storage
            self.documents[doc_id] = {
                "content": content,
                "metadata": metadata or {},
                "embedding": self.embedding_model.embed(content),
            }
            return

        embedding = self.embedding_model.embed(content)

        # Normalize for cosine similarity
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        embedding = embedding.reshape(1, -1).astype(np.float32)

        # Add to index
        self.index.add(embedding)

        # Store mapping
        self.documents[doc_id] = {
            "content": content,
            "metadata": metadata or {},
        }
        self.id_to_idx[doc_id] = self._next_idx
        self.idx_to_id[self._next_idx] = doc_id
        self._next_idx += 1

        logger.debug(f"Added document to FAISS store: {doc_id}")

    def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar documents."""
        if not self.documents:
            return []

        if self._faiss is None:
            # Fallback to brute force
            return self._search_brute_force(query, k, filter_metadata)

        query_embedding = self.embedding_model.embed(query)
        query_embedding = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)

        # Search with extra results for filtering
        search_k = min(k * 3, self.index.ntotal) if filter_metadata else k
        scores, indices = self.index.search(query_embedding, search_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:  # Invalid index
                continue

            doc_id = self.idx_to_id.get(int(idx))
            if doc_id is None:
                continue

            doc = self.documents.get(doc_id)
            if doc is None:
                continue

            # Apply metadata filter
            if filter_metadata:
                if not all(
                    doc["metadata"].get(k) == v for k, v in filter_metadata.items()
                ):
                    continue

            results.append(
                SearchResult(
                    doc_id=doc_id,
                    content=doc["content"],
                    score=float(score),
                    metadata=doc["metadata"],
                )
            )

            if len(results) >= k:
                break

        return results

    def _search_brute_force(
        self,
        query: str,
        k: int,
        filter_metadata: Optional[Dict[str, Any]],
    ) -> List[SearchResult]:
        """Fallback brute force search."""
        query_embedding = self.embedding_model.embed(query)

        similarities = []
        for doc_id, doc in self.documents.items():
            if filter_metadata:
                if not all(
                    doc["metadata"].get(k) == v for k, v in filter_metadata.items()
                ):
                    continue

            doc_embedding = doc["embedding"]
            similarity = np.dot(query_embedding, doc_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding) + 1e-8
            )
            similarities.append((doc_id, float(similarity)))

        similarities.sort(key=lambda x: x[1], reverse=True)

        return [
            SearchResult(
                doc_id=doc_id,
                content=self.documents[doc_id]["content"],
                score=score,
                metadata=self.documents[doc_id]["metadata"],
            )
            for doc_id, score in similarities[:k]
        ]

    def delete(self, doc_id: str) -> bool:
        """Delete a document (marks as deleted, doesn't removefrom index)."""
        if doc_id in self.documents:
            del self.documents[doc_id]
            # Note: FAISS doesn't support efficient deletion
            # Would need to rebuild index for true deletion
            return True
        return False

    def clear(self) -> None:
        """Clear all documents and reset index."""
        self.documents.clear()
        self.id_to_idx.clear()
        self.idx_to_id.clear()
        self._index = None
        self._next_idx = 0

    @property
    def count(self) -> int:
        """Get document count."""
        return len(self.documents)

    def save(self, path: Optional[Path] = None) -> None:
        """Save the index and documents to disk."""
        path = path or self.index_path
        if path is None:
            raise ValueError("No path specified for saving")

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        if self._faiss is not None and self._index is not None:
            index_file = path / "faiss.index"
            self._faiss.write_index(self._index, str(index_file))

        # Save documents and mappings
        meta_file = path / "metadata.json"
        with open(meta_file, "w") as f:
            json.dump(
                {
                    "documents": self.documents,
                    "id_to_idx": self.id_to_idx,
                    "idx_to_id": {str(k): v for k, v in self.idx_to_id.items()},
                    "next_idx": self._next_idx,
                },
                f,
            )

        logger.info(f"Saved vector store to {path}")

    def load(self, path: Optional[Path] = None) -> None:
        """Load the index and documents from disk."""
        path = path or self.index_path
        if path is None:
            raise ValueError("No path specified for loading")

        path = Path(path)

        # Load FAISS index
        if self._faiss is not None:
            index_file = path / "faiss.index"
            if index_file.exists():
                self._index = self._faiss.read_index(str(index_file))

        # Load documents and mappings
        meta_file = path / "metadata.json"
        if meta_file.exists():
            with open(meta_file, "r") as f:
                data = json.load(f)
                self.documents = data["documents"]
                self.id_to_idx = data["id_to_idx"]
                self.idx_to_id = {int(k): v for k, v in data["idx_to_id"].items()}
                self._next_idx = data["next_idx"]

        logger.info(f"Loaded vector store from {path} ({self.count} documents)")
