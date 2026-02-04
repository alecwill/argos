"""
Pet Persona AI - Generate unique pet personalities and voices.

This package provides tools to:
- Build baseline personality profiles for dog and cat breeds
- Create personalized pet profiles from user input
- Generate consistent "voice" profiles for pets
- Enable interactive conversations with pets via text or voice
"""

__version__ = "0.1.0"
__author__ = "Pet Persona AI Team"

from pet_persona.config import Settings, get_settings

__all__ = ["Settings", "get_settings", "__version__"]
