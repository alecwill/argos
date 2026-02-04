"""Speech-to-text transcription."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


class SpeechToText(ABC):
    """Abstract base class for speech-to-text."""

    @abstractmethod
    def transcribe(self, audio_path: Path) -> Optional[str]:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file (WAV format)

        Returns:
            Transcribed text or None if failed
        """
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the STT system is available."""
        pass


class FasterWhisperSTT(SpeechToText):
    """
    Speech-to-text using faster-whisper.

    Faster-whisper is a reimplementation of OpenAI's Whisper
    that's optimized for CPU inference.
    """

    def __init__(
        self,
        model_size: str = "base",
        language: str = "en",
        device: str = "cpu",
    ):
        """
        Initialize faster-whisper STT.

        Args:
            model_size: Model size (tiny, base, small, medium,large)
            language: Language code
            device: Device to run on (cpu, cuda)
        """
        self.model_size = model_size
        self.language = language
        self.device = device
        self._model = None
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if faster-whisper is available."""
        try:
            from faster_whisper import WhisperModel
            return True
        except ImportError:
            logger.warning(
                "faster-whisper not installed. Install with: pip install faster-whisper"
            )
            return False

    @property
    def is_available(self) -> bool:
        """Check if STT is available."""
        return self._available

    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None and self._available:
            try:
                from faster_whisper import WhisperModel

                logger.info(f"Loading faster-whisper model: {self.model_size}")
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type="int8" if self.device == "cpu" else "float16",
                )
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                self._available = False
        return self._model

    def transcribe(self, audio_path: Path) -> Optional[str]:
        """Transcribe audio file to text."""
        if not self._available:
            logger.error("STT not available")
            return None

        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return None

        try:
            logger.debug(f"Transcribing: {audio_path}")

            segments, info = self.model.transcribe(
                str(audio_path),
                language=self.language,
                beam_size=5,
                vad_filter=True,
            )

            # Combine all segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            transcription = " ".join(text_parts)

            logger.info(f"Transcribed: {transcription[:50]}...")
            return transcription

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None


class DummySTT(SpeechToText):
    """Dummy STT for testing without actual transcription."""

    def __init__(self):
        """Initialize dummy STT."""
        self._available = True

    @property
    def is_available(self) -> bool:
        """Always available for testing."""
        return True

    def transcribe(self, audio_path: Path) -> Optional[str]:
        """Return placeholder text."""
        logger.warning("Using dummy STT - no actual transcription")
        return "[Voice input placeholder - install faster-whisper for real STT]"


def get_stt(provider: str = "faster_whisper", **kwargs) -> SpeechToText:
    """
    Get speech-to-text instance.

    Args:
        provider: STT provider name
        **kwargs: Provider-specific arguments

    Returns:
        SpeechToText instance
    """
    if provider == "faster_whisper":
        stt = FasterWhisperSTT(**kwargs)
        if stt.is_available:
            return stt
        logger.warning("Falling back to dummy STT")

    return DummySTT()
