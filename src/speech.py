"""
Speech recognition module - captures and transcribes user speech.
"""

import speech_recognition as sr
from typing import Optional, Tuple
import threading
import queue


class SpeechCapture:
    """Handles speech-to-text capture using the microphone."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self._is_listening = False
        self._result_queue: queue.Queue = queue.Queue()

        # Adjust for ambient noise sensitivity
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8  # Seconds of silence before phrase is complete

    def calibrate(self, duration: float = 1.0):
        """
        Calibrate for ambient noise levels.

        Args:
            duration: Seconds to listen for ambient noise
        """
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
        except OSError:
            pass  # No microphone available

    def capture_speech(
        self,
        timeout: float = 3.0,
        phrase_time_limit: float = 5.0
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Listen for speech and transcribe it.

        Args:
            timeout: Max seconds to wait for speech to start
            phrase_time_limit: Max seconds of speech to capture

        Returns:
            Tuple of (transcribed_text, error_message)
        """
        try:
            with sr.Microphone() as source:
                # Quick ambient noise adjustment
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)

                # Listen for speech
                try:
                    audio = self.recognizer.listen(
                        source,
                        timeout=timeout,
                        phrase_time_limit=phrase_time_limit
                    )
                except sr.WaitTimeoutError:
                    return None, None  # No speech detected, not an error

                # Transcribe using Google's free speech recognition
                try:
                    text = self.recognizer.recognize_google(audio)
                    return text, None
                except sr.UnknownValueError:
                    return None, None  # Speech was unintelligible
                except sr.RequestError as e:
                    return None, f"Speech service error: {e}"

        except OSError as e:
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

        # Settings for background listening
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.0

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
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1.0)

                while not self._stop_event.is_set():
                    try:
                        audio = self.recognizer.listen(
                            source,
                            timeout=2.0,
                            phrase_time_limit=5.0
                        )

                        # Transcribe in background
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

                    except sr.WaitTimeoutError:
                        continue

        except OSError:
            pass  # Microphone not available

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
