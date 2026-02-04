"""Data ingestion pipelines for Wikipedia and YouTube."""

from pet_persona.ingest.wikipedia import WikipediaIngester
from pet_persona.ingest.youtube import YouTubeIngester
from pet_persona.ingest.models import STARTER_DOG_BREEDS, STARTER_CAT_BREEDS

__all__ = [
    "WikipediaIngester",
    "YouTubeIngester",
    "STARTER_DOG_BREEDS",
    "STARTER_CAT_BREEDS",
]
