"""Text processing utilities for Pet Persona AI."""

import re
import unicodedata
from typing import List, Optional


def clean_text(text: str) -> str:
    """
    Clean and normalize text content.

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text with normalized whitespace and unicode
    """
    if not text:
        return ""

    # Normalize unicode characters
    text = unicodedata.normalize("NFKC", text)

    # Remove control characters except newlines
    text = "".join(char for char in text if unicodedata.category(char)[0] != "C" or char in "\n\t")

    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def extract_sentences(text: str, max_sentences: Optional[int] = None) -> List[str]:
    """
    Extract sentences from text.

    Args:
        text: Text to extract sentences from
        max_sentences: Maximum number of sentences to return

    Returns:
        List of sentences
    """
    if not text:
        return []

    # Simple sentence splitting on common terminators
    # Handles abbreviations like "Dr.", "Mr.", "etc."
    # Replace abbreviations with placeholders to avoid splitting on them
    abbreviations = ["Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "Jr.", "Sr.", "vs.", "etc.", "e.g.", "i.e."]
    placeholders = {}
    temp_text = text
    for i, abbr in enumerate(abbreviations):
        placeholder = f"\x00ABBR{i}\x00"
        placeholders[placeholder] = abbr
        temp_text = temp_text.replace(abbr, placeholder)

    # Split on sentence terminators
    sentence_pattern = r"\.\s+|\?\s+|!\s+"
    sentences = re.split(sentence_pattern, temp_text)

    # Restore abbreviations
    restored = []
    for s in sentences:
        for placeholder, abbr in placeholders.items():
            s = s.replace(placeholder, abbr)
        restored.append(s)
    sentences = restored

    # Clean up each sentence
    sentences = [s.strip() for s in sentences if s.strip()]

    # Restore periods to sentences that need them
    sentences = [s if s[-1] in ".!?" else s + "." for s in sentences if s]

    if max_sentences:
        sentences = sentences[:max_sentences]

    return sentences


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length, preserving word boundaries.

    Args:
        text: Text to truncate
        max_length: Maximum length of output
        suffix: Suffix to add when truncating

    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text

    # Find a word boundary to truncate at
    truncate_at = max_length - len(suffix)
    if truncate_at <= 0:
        return suffix

    # Find the last space before the truncation point
    last_space = text.rfind(" ", 0, truncate_at)
    if last_space > 0:
        truncate_at = last_space

    return text[:truncate_at].rstrip() + suffix


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """
    Extract keywords from text (simple word extraction).

    Args:
        text: Text to extract keywords from
        min_length: Minimum keyword length

    Returns:
        List of keywords
    """
    if not text:
        return []

    # Simple word extraction - lowercase and filter
    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())

    # Common stop words to filter out
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
        "be", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "shall", "can", "this",
        "that", "these", "those", "it", "its", "they", "them","their",
        "he", "she", "him", "her", "his", "we", "us", "our", "you", "your",
        "i", "me", "my", "not", "no", "yes", "all", "any", "some", "more",
        "most", "other", "into", "over", "such", "than", "too", "very",
        "just", "also", "now", "here", "there", "when", "where", "why",
        "how", "what", "which", "who", "whom", "whose", "each", "every",
        "both", "few", "many", "much", "own", "same", "so", "then", "only",
    }

    keywords = [w for w in words if len(w) >= min_length and wnot in stop_words]

    return keywords


def normalize_breed_name(breed: str) -> str:
    """
    Normalize a breed name for consistent lookups.

    Args:
        breed: Breed name to normalize

    Returns:
        Normalized breed name
    """
    if not breed:
        return ""

    # Lowercase and strip
    normalized = breed.lower().strip()

    # Replace common variations
    replacements = {
        "golden retriever": "golden retriever",
        "labrador retriever": "labrador retriever",
        "lab": "labrador retriever",
        "german shepherd dog": "german shepherd",
        "gsd": "german shepherd",
    }

    return replacements.get(normalized, normalized)
