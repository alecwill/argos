"""Embedding model for text vectorization."""

from abc import ABC, abstractmethod
from functools import lru_cache
from typing import List, Optional

import numpy as np

from pet_persona.config import get_settings
from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


class EmbeddingModel(ABC):
    """Abstract base class for embedding models."""

    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """
        Embed a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array
        """
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Embed multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            2D numpy array of embeddings (n_texts x embedding_dim)
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get embedding dimension."""
        pass


class SentenceTransformerEmbedding(EmbeddingModel):
    """Embedding model using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize sentence transformer embedding model.

        Args:
            model_name: HuggingFace model name
        """
        self.model_name = model_name
        self._model = None
        self._dimension = None

    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
                logger.info(f"Loaded model with dimension: {self._dimension}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
        return self._model

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is None:
            _ = self.model  # Trigger lazy loading
        return self._dimension

    def embed(self, text: str) -> np.ndarray:
        """Embed a single text."""
        return self.model.encode(text, convert_to_numpy=True)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Embed multiple texts."""
        if not texts:
            return np.array([])
        return self.model.encode(texts, convert_to_numpy=True,show_progress_bar=False)


class TFIDFEmbedding(EmbeddingModel):
    """Fallback TF-IDF based embedding model."""

    def __init__(self, max_features: int = 512):
        """
        Initialize TF-IDF embedding model.

        Args:
            max_features: Maximum vocabulary size
        """
        self.max_features = max_features
        self._vectorizer = None
        self._fitted = False

    @property
    def vectorizer(self):
        """Get or create vectorizer."""
        if self._vectorizer is None:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer

                self._vectorizer = TfidfVectorizer(
                    max_features=self.max_features,
                    stop_words="english",
                    ngram_range=(1, 2),
                )
            except ImportError:
                raise ImportError(
                    "scikit-learn not installed. "
                    "Install with: pip install scikit-learn"
                )
        return self._vectorizer

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self.max_features

    def fit(self, texts: List[str]) -> None:
        """Fit the vectorizer on a corpus."""
        if texts:
            self.vectorizer.fit(texts)
            self._fitted = True
            logger.info(f"Fitted TF-IDF vectorizer on {len(texts)} texts")

    def embed(self, text: str) -> np.ndarray:
        """Embed a single text."""
        if not self._fitted:
            # Fit on the single text if not fitted
            self.fit([text])

        vec = self.vectorizer.transform([text])
        return vec.toarray()[0]

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Embed multiple texts."""
        if not texts:
            return np.array([])

        if not self._fitted:
            self.fit(texts)

        vecs = self.vectorizer.transform(texts)
        return vecs.toarray()


@lru_cache()
def get_embedding_model(model_name: Optional[str] = None) -> EmbeddingModel:
    """
    Get embedding model instance.

    Tries sentence-transformers first, falls back to TF-IDF.

    Args:
        model_name: Model name (uses config default if None)

    Returns:
        EmbeddingModel instance
    """
    if model_name is None:
        model_name = get_settings().embedding_model

    try:
        return SentenceTransformerEmbedding(model_name)
    except ImportError:
        logger.warning(
            "sentence-transformers not available, using TF-IDFfallback. "
            "For better results, install sentence-transformers."
        )
        return TFIDFEmbedding()
