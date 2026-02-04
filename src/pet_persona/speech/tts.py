"""Text-to-speech synthesis."""

from abc import ABC, abstractmethod
from typing import Optional

from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


class TextToSpeech(ABC):
    """Abstract base class for text-to-speech."""

    @abstractmethod
    def speak(self, text: str) -> bool:
        """
        Speak text aloud.

        Args:
            text: Text to speak

        Returns:
            True if successful, False otherwise
        """
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the TTS system is available."""
        pass


class Pyttsx3TTS(TextToSpeech):
    """
    Text-to-speech using pyttsx3.

    pyttsx3 is a cross-platform TTS library that works offline
    using system TTS engines.
    """

    def __init__(
        self,
        rate: Optional[int] = None,
        volume: float = 1.0,
        voice_id: Optional[str] = None,
    ):
        """
        Initialize pyttsx3 TTS.

        Args:
            rate: Speech rate (words per minute, default ~200)
            volume: Volume level (0.0 to 1.0)
            voice_id: Specific voice ID to use
        """
        self.rate = rate
        self.volume = volume
        self.voice_id = voice_id
        self._engine = None
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if pyttsx3 is available."""
        try:
            import pyttsx3
            return True
        except ImportError:
            logger.warning(
                "pyttsx3 not installed. Install with: pip install pyttsx3"
            )
            return False
        except Exception as e:
            logger.warning(f"TTS initialization error: {e}")
            return False

    @property
    def is_available(self) -> bool:
        """Check if TTS is available."""
        return self._available

    @property
    def engine(self):
        """Get or create TTS engine."""
        if self._engine is None and self._available:
            try:
                import pyttsx3

                self._engine = pyttsx3.init()

                # Configure engine
                if self.rate:
                    self._engine.setProperty("rate", self.rate)
                self._engine.setProperty("volume", self.volume)

                if self.voice_id:
                    self._engine.setProperty("voice", self.voice_id)

                logger.debug("TTS engine initialized")
            except Exception as e:
                logger.error(f"Failed to initialize TTS engine: {e}")
                self._available = False

        return self._engine

    def speak(self, text: str) -> bool:
        """Speak text aloud."""
        if not self._available:
            logger.error("TTS not available")
            return False

        if not text:
            return True

        try:
            logger.debug(f"Speaking: {text[:50]}...")
            self.engine.say(text)
            self.engine.runAndWait()
            return True

        except Exception as e:
            logger.error(f"TTS error: {e}")
            return False

    def list_voices(self) -> None:
        """Print available voices."""
        if not self._available:
            print("TTS not available")
            return

        try:
            voices = self.engine.getProperty("voices")
            print("\nAvailable voices:")
            for voice in voices:
                print(f"  ID: {voice.id}")
                print(f"  Name: {voice.name}")
                print(f"  Languages: {voice.languages}")
                print()
        except Exception as e:
            logger.error(f"Error listing voices: {e}")


class DummyTTS(TextToSpeech):
    """Dummy TTS that just prints text."""

    def __init__(self):
        """Initialize dummy TTS."""
        self._available = True

    @property
    def is_available(self) -> bool:
        """Always available."""
        return True

    def speak(self, text: str) -> bool:
        """Print text instead of speaking."""
        print(f"🔊 [TTS would say]: {text}")
        return True


def get_tts(provider: str = "pyttsx3", **kwargs) -> TextToSpeech:
    """
    Get text-to-speech instance.

    Args:
        provider: TTS provider name
        **kwargs: Provider-specific arguments

    Returns:
        TextToSpeech instance
    """
    if provider == "pyttsx3":
        tts = Pyttsx3TTS(**kwargs)
        if tts.is_available:
            return tts
        logger.warning("Falling back to dummy TTS")

    return DummyTTS()
