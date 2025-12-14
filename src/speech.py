"""
Speech recognition module - captures and transcribes user speech.
Uses sounddevice for audio capture (easier to install than PyAudio on Windows).
"""

import io
import wave
import speech_recognition as sr
from typing import Optional, Tuple
import threading
import queue
import numpy as np
import sounddevice as sd


class SoundDeviceMicrophone:
    """Custom audio source using sounddevice instead of PyAudio."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.SAMPLE_WIDTH = 2  # 16-bit audio
        self.SAMPLE_RATE = sample_rate
        self.CHUNK = 1024
        self._audio_data = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def record(self, duration: float) -> bytes:
        """Record audio for specified duration."""
        frames = int(duration * self.sample_rate)
        recording = sd.rec(
            frames,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.int16,
            blocking=True
        )
        return recording.tobytes()


def record_audio_to_wav(duration: float, sample_rate: int = 16000) -> bytes:
    """Record audio and return as WAV file bytes."""
    frames = int(duration * sample_rate)
    recording = sd.rec(
        frames,
        samplerate=sample_rate,
        channels=1,
        dtype=np.int16,
        blocking=True
    )

    # Convert to WAV format in memory
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(recording.tobytes())

    buffer.seek(0)
    return buffer.read()


class SpeechCapture:
    """Handles speech-to-text capture using the microphone."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self._is_listening = False
        self._result_queue: queue.Queue = queue.Queue()
        self.sample_rate = 16000

        # Adjust recognition settings
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = False  # Disable for sounddevice

    def capture_speech(
        self,
        timeout: float = 3.0,
        phrase_time_limit: float = 5.0
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Listen for speech and transcribe it.

        Args:
            timeout: Max seconds to wait for speech to start (used as initial record time)
            phrase_time_limit: Max seconds of speech to capture

        Returns:
            Tuple of (transcribed_text, error_message)
        """
        try:
            # Record audio for the combined duration
            total_duration = min(timeout + phrase_time_limit, 8.0)  # Cap at 8 seconds
            wav_data = record_audio_to_wav(total_duration, self.sample_rate)

            # Convert to AudioData for speech_recognition
            audio = sr.AudioData(wav_data, self.sample_rate, 2)

            # Transcribe using Google's free speech recognition
            try:
                text = self.recognizer.recognize_google(audio)
                return text, None
            except sr.UnknownValueError:
                return None, None  # Speech was unintelligible or no speech
            except sr.RequestError as e:
                return None, f"Speech service error: {e}"

        except sd.PortAudioError as e:
            return None, f"Audio device error: {e}"
        except Exception as e:
            return None, f"Microphone error: {e}"

    def capture_speech_async(
        self,
        timeout: float = 3.0,
        phrase_time_limit: float = 5.0,
        callback=None
    ):
        """
        Capture speech asynchronously.

        Args:
            timeout: Max seconds to wait for speech to start
            phrase_time_limit: Max seconds of speech to capture
            callback: Function to call with (text, error) when done
        """
        def _capture():
            text, error = self.capture_speech(timeout, phrase_time_limit)
            if callback:
                callback(text, error)
            self._result_queue.put((text, error))

        thread = threading.Thread(target=_capture, daemon=True)
        thread.start()
        return thread

    def get_result(self, timeout: float = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Get the result from an async capture.

        Args:
            timeout: Max seconds to wait for result

        Returns:
            Tuple of (transcribed_text, error_message)
        """
        try:
            return self._result_queue.get(timeout=timeout)
        except queue.Empty:
            return None, "Timeout waiting for speech result"


class ContinuousListener:
    """
    Continuously listens in the background and buffers recent speech.
    This allows capturing what the user said just before pressing the hotkey.
    """

    def __init__(self, buffer_seconds: float = 10.0):
        self.recognizer = sr.Recognizer()
        self.buffer_seconds = buffer_seconds
        self._is_running = False
        self._recent_text: list = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self.sample_rate = 16000

    def start(self):
        """Start continuous background listening."""
        if self._is_running:
            return

        self._is_running = True
        self._stop_event.clear()

        thread = threading.Thread(target=self._listen_loop, daemon=True)
        thread.start()

    def _listen_loop(self):
        """Main listening loop."""
        try:
            while not self._stop_event.is_set():
                try:
                    # Record in 3-second chunks
                    wav_data = record_audio_to_wav(3.0, self.sample_rate)
                    audio = sr.AudioData(wav_data, self.sample_rate, 2)

                    # Transcribe
                    try:
                        text = self.recognizer.recognize_google(audio)
                        if text:
                            with self._lock:
                                self._recent_text.append(text)
                                # Keep only recent entries
                                if len(self._recent_text) > 5:
                                    self._recent_text.pop(0)
                    except (sr.UnknownValueError, sr.RequestError):
                        pass

                except Exception:
                    # Brief pause on error before retrying
                    if not self._stop_event.wait(1.0):
                        continue

        except Exception:
            pass  # Exit gracefully

        self._is_running = False

    def stop(self):
        """Stop continuous listening."""
        self._stop_event.set()
        self._is_running = False

    def get_recent_speech(self, clear: bool = True) -> Optional[str]:
        """
        Get recently captured speech.

        Args:
            clear: Whether to clear the buffer after reading

        Returns:
            Combined recent speech or None
        """
        with self._lock:
            if not self._recent_text:
                return None

            text = " ".join(self._recent_text)

            if clear:
                self._recent_text.clear()

            return text

    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._is_running
