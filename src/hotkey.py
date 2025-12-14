"""
Hotkey detection module - listens for global hotkeys to trigger actions.
"""

import keyboard
from typing import Callable, Optional
import threading


class HotkeyManager:
    """Manages global hotkey registration and callbacks."""

    def __init__(self):
        self._hotkey_handle: Optional[Callable] = None
        self._is_listening = False
        self._callback: Optional[Callable] = None
        self._hotkey: str = "ctrl+shift+space"

    def set_hotkey(self, hotkey: str):
        """
        Set the hotkey combination.

        Args:
            hotkey: Hotkey string (e.g., 'ctrl+shift+space', 'f12', 'alt+a')
        """
        was_listening = self._is_listening

        if was_listening:
            self.stop()

        self._hotkey = hotkey

        if was_listening and self._callback:
            self.start(self._callback)

    def start(self, callback: Callable):
        """
        Start listening for the hotkey.

        Args:
            callback: Function to call when hotkey is pressed
        """
        if self._is_listening:
            return

        self._callback = callback
        self._is_listening = True

        # Register the hotkey
        keyboard.add_hotkey(
            self._hotkey,
            self._on_hotkey_pressed,
            suppress=False  # Don't suppress the key event
        )

    def _on_hotkey_pressed(self):
        """Internal handler for hotkey press."""
        if self._callback:
            # Run callback in a separate thread to avoid blocking
            thread = threading.Thread(target=self._callback, daemon=True)
            thread.start()

    def stop(self):
        """Stop listening for hotkeys."""
        if not self._is_listening:
            return

        try:
            keyboard.remove_hotkey(self._hotkey)
        except KeyError:
            pass  # Hotkey wasn't registered

        self._is_listening = False

    def get_hotkey(self) -> str:
        """Get the current hotkey combination."""
        return self._hotkey

    def is_listening(self) -> bool:
        """Check if currently listening for hotkeys."""
        return self._is_listening


def wait_for_key(key: str = "escape"):
    """
    Block until a specific key is pressed.

    Args:
        key: The key to wait for (default: 'escape')
    """
    keyboard.wait(key)
