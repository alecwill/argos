"""Microphone input handling."""

import io
import tempfile
from pathlib import Path
from typing import Optional

from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


class MicrophoneListener:
    """
    Capture audio from microphone.

    Supports both push-to-talk and voice activity detection modes.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device: Optional[int] = None,
    ):
        """
        Initialize microphone listener.

        Args:
            sample_rate: Audio sample rate in Hz
            channels: Number of audio channels
            device: Audio device index (None for default)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device

        self._sd = None
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if sounddevice is available."""
        try:
            import sounddevice as sd
            self._sd = sd
            return True
        except ImportError:
            logger.warning(
                "sounddevice not installed. Voice input unavailable. "
                "Install with: pip install sounddevice"
            )
            return False
        except Exception as e:
            logger.warning(f"Audio system error: {e}")
            return False

    @property
    def is_available(self) -> bool:
        """Check if microphone is available."""
        return self._available

    def record_seconds(self, duration: float) -> Optional[Path]:
        """
        Record audio for a fixed duration.

        Args:
            duration: Recording duration in seconds

        Returns:
            Path to temporary WAV file, or None if unavailable
        """
        if not self._available:
            logger.error("Microphone not available")
            return None

        try:
            import numpy as np
            from scipy.io import wavfile

            logger.info(f"Recording for {duration} seconds...")
            print(f"🎤 Recording for {duration:.1f} seconds...")

            # Record audio
            recording = self._sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.int16,
                device=self.device,
            )
            self._sd.wait()

            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            wavfile.write(temp_file.name, self.sample_rate, recording)

            logger.info(f"Recording saved to: {temp_file.name}")
            print("✅ Recording complete!")
            return Path(temp_file.name)

        except ImportError:
            logger.error(
                "scipy not installed. Install with: pip install scipy"
            )
            return None
        except Exception as e:
            logger.error(f"Recording error: {e}")
            return None

    def record_until_silence(
        self,
        silence_threshold: float = 0.01,
        silence_duration: float = 1.5,
        max_duration: float = 30.0,
    ) -> Optional[Path]:
        """
        Record until silence is detected.

        Args:
            silence_threshold: RMS threshold for silence detection
            silence_duration: Seconds of silence to stop recording
            max_duration: Maximum recording duration

        Returns:
            Path to temporary WAV file, or None if unavailable
        """
        if not self._available:
            logger.error("Microphone not available")
            return None

        try:
            import numpy as np
            from scipy.io import wavfile

            logger.info("Recording... (speak now, will stop onsilence)")
            print("🎤 Recording... (speak now, will stop aftersilence)")

            frames = []
            silence_samples = 0
            silence_samples_needed = int(silence_duration * self.sample_rate / 1024)
            max_samples = int(max_duration * self.sample_rate / 1024)

            def callback(indata, frames_count, time_info, status):
                nonlocal silence_samples
                rms = np.sqrt(np.mean(indata ** 2))

                if rms < silence_threshold:
                    silence_samples += 1
                else:
                    silence_samples = 0

                frames.append(indata.copy())

            # Start recording with callback
            with self._sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.int16,
                device=self.device,
                blocksize=1024,
                callback=callback,
            ):
                while silence_samples < silence_samples_needed and len(frames) < max_samples:
                    self._sd.sleep(100)

            # Combine frames
            recording = np.concatenate(frames, axis=0)

            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            wavfile.write(temp_file.name, self.sample_rate, recording)

            logger.info(f"Recording saved: {len(recording) / self.sample_rate:.1f}s")
            print("✅ Recording complete!")
            return Path(temp_file.name)

        except ImportError:
            logger.error("scipy not installed")
            return None
        except Exception as e:
            logger.error(f"Recording error: {e}")
            return None

    def list_devices(self) -> None:
        """Print available audio devices."""
        if not self._available:
            print("Audio system not available")
            return

        print("\nAvailable audio devices:")
        print(self._sd.query_devices())
