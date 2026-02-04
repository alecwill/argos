"""Data models for ingestion pipelines."""

from typing import List

# Starter dog breeds for initial ingestion
STARTER_DOG_BREEDS: List[str] = [
    "Labrador Retriever",
    "German Shepherd",
    "Golden Retriever",
    "French Bulldog",
    "Bulldog",
    "Poodle",
    "Beagle",
    "Rottweiler",
    "German Shorthaired Pointer",
    "Dachshund",
    "Pembroke Welsh Corgi",
    "Australian Shepherd",
    "Yorkshire Terrier",
    "Cavalier King Charles Spaniel",
    "Doberman Pinscher",
    "Boxer",
    "Miniature Schnauzer",
    "Great Dane",
    "Shih Tzu",
    "Siberian Husky",
]

# Starter cat breeds for initial ingestion
STARTER_CAT_BREEDS: List[str] = [
    "Persian",
    "Maine Coon",
    "Ragdoll",
    "British Shorthair",
    "Abyssinian",
    "Siamese",
    "Bengal",
    "Russian Blue",
    "Scottish Fold",
    "Sphynx",
    "American Shorthair",
    "Birman",
    "Burmese",
    "Norwegian Forest Cat",
    "Devon Rex",
    "Oriental Shorthair",
    "Exotic Shorthair",
    "Siberian",
    "Ragamuffin",
    "Tonkinese",
]

# Wikipedia page title patterns for breeds
WIKIPEDIA_DOG_TITLE_PATTERNS = [
    "{breed}",
    "{breed} (dog)",
    "{breed} dog",
]

WIKIPEDIA_CAT_TITLE_PATTERNS = [
    "{breed}",
    "{breed} (cat)",
    "{breed} cat",
]

# YouTube search query patterns
YOUTUBE_SEARCH_PATTERNS = [
    "{breed} temperament",
    "{breed} personality",
    "living with {breed}",
    "{breed} breed information",
    "{breed} characteristics",
]
