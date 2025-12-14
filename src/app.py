"""
Main application module for DisplayCap Think.
"""

import sys
import threading
import tkinter as tk
from typing import Optional
import concurrent.futures

from .screenshot import capture_sequence, screenshots_to_base64
from .api_client import create_client, analyze_screenshots
from .display import ResponseWindow, StatusIndicator
from .hotkey import HotkeyManager
from .config import load_config, get_api_key
from .speech import SpeechCapture, ContinuousListener


class DisplayCapApp:
    """Main application class for DisplayCap Think."""

    def __init__(self):
        self.config = load_config()
        self.api_key: Optional[str] = None
        self.client = None
        self.hotkey_manager = HotkeyManager()
        self.response_window: Optional[ResponseWindow] = None
        self.is_processing = False
        self._root: Optional[tk.Tk] = None

        # Speech capture
        self.speech_enabled = self.config.get("speech_enabled", True)
        self.speech_capture: Optional[SpeechCapture] = None
        self.continuous_listener: Optional[ContinuousListener] = None
        self.use_continuous_listening = self.config.get("continuous_listening", False)

    def initialize(self) -> bool:
        """
        Initialize the application.

        Returns:
            True if initialization successful, False otherwise
        """
        # Get API key
        self.api_key = get_api_key()
        if not self.api_key:
            print("Error: No API key found!")
            print("Please set the ANTHROPIC_API_KEY environment variable")
            print("Or run: python -m src.app --set-key YOUR_API_KEY")
            return False

        # Create API client
        try:
            self.client = create_client(self.api_key)
        except Exception as e:
            print(f"Error creating API client: {e}")
            return False

        # Set up hotkey
        self.hotkey_manager.set_hotkey(self.config.get("hotkey", "ctrl+shift+space"))

        # Initialize speech capture if enabled
        if self.speech_enabled:
            try:
                self.speech_capture = SpeechCapture()
                print("Speech capture enabled - speak after pressing hotkey")

                # Start continuous listening if configured
                if self.use_continuous_listening:
                    self.continuous_listener = ContinuousListener()
                    self.continuous_listener.start()
                    print("Continuous listening active")
            except Exception as e:
                print(f"Warning: Speech capture unavailable: {e}")
                self.speech_enabled = False

        return True

    def _capture_and_analyze(self):
        """Capture screenshots and speech, then send to AI for analysis."""
        if self.is_processing:
            return

        self.is_processing = True
        speech_text = None

        try:
            # Check for continuous listening buffer first
            if self.continuous_listener and self.continuous_listener.is_running():
                speech_text = self.continuous_listener.get_recent_speech(clear=True)

            # Show status on main thread
            status_msg = "Capturing..." if not self.speech_enabled else "Capturing... (listening)"
            self._root.after(0, lambda: self._show_status(status_msg))

            # Capture screenshots and speech in parallel
            count = self.config.get("screenshot_count", 3)
            interval = self.config.get("screenshot_interval", 0.5)
            speech_timeout = self.config.get("speech_timeout", 3.0)
            speech_phrase_limit = self.config.get("speech_phrase_limit", 5.0)

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Start screenshot capture
                screenshot_future = executor.submit(
                    capture_sequence, count=count, interval=interval
                )

                # Start speech capture if enabled and no continuous buffer
                speech_future = None
                if self.speech_enabled and self.speech_capture and not speech_text:
                    speech_future = executor.submit(
                        self.speech_capture.capture_speech,
                        timeout=speech_timeout,
                        phrase_time_limit=speech_phrase_limit
                    )

                # Get screenshot results
                screenshots = screenshot_future.result()

                # Get speech results if capturing
                if speech_future:
                    captured_text, speech_error = speech_future.result()
                    if captured_text:
                        speech_text = captured_text
                    if speech_error:
                        print(f"Speech warning: {speech_error}")

            # Update status
            self._root.after(0, lambda: self._update_status("Analyzing..."))

            # Convert to base64
            quality = self.config.get("image_quality", 85)
            images_base64 = screenshots_to_base64(screenshots, quality=quality)

            # Send to API with speech context
            response = analyze_screenshots(
                self.client,
                images_base64,
                user_context=speech_text
            )

            # Show response (include speech indicator if we captured speech)
            if speech_text:
                response = f'[Heard: "{speech_text}"]\n\n{response}'

            self._root.after(0, lambda: self._show_response(response))

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self._root.after(0, lambda: self._show_response(error_msg))

        finally:
            self.is_processing = False

    def _show_status(self, message: str):
        """Show status indicator."""
        if self.response_window:
            self.response_window.show(message)

    def _update_status(self, message: str):
        """Update status message."""
        if self.response_window:
            self.response_window.update_message(message)

    def _show_response(self, response: str):
        """Show the AI response in the window."""
        if self.response_window:
            self.response_window.update_message(response)

    def _on_hotkey(self):
        """Handle hotkey press."""
        # Run capture/analyze in background thread
        thread = threading.Thread(target=self._capture_and_analyze, daemon=True)
        thread.start()

    def run(self):
        """Run the application main loop."""
        # Create the main tkinter root window (hidden)
        self._root = tk.Tk()
        self._root.withdraw()  # Hide the main window

        # Create response window with parent
        self.response_window = ResponseWindow(self._root)

        # Start hotkey listener
        self.hotkey_manager.start(self._on_hotkey)

        hotkey = self.hotkey_manager.get_hotkey()
        print(f"DisplayCap Think is running!")
        print(f"Press {hotkey.upper()} to capture and analyze your screen")
        if self.speech_enabled:
            print("Speak your question after pressing the hotkey for better context")
        print("Press Ctrl+C to exit")

        # Run the tkinter main loop
        try:
            self._root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean up and shut down the application."""
        print("\nShutting down...")

        self.hotkey_manager.stop()

        # Stop continuous listener if running
        if self.continuous_listener:
            self.continuous_listener.stop()

        if self.response_window:
            self.response_window.destroy()

        if self._root:
            try:
                self._root.quit()
                self._root.destroy()
            except tk.TclError:
                pass


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="DisplayCap Think - AI Screenshot Assistant"
    )
    parser.add_argument(
        "--set-key",
        metavar="API_KEY",
        help="Set your Anthropic API key"
    )
    parser.add_argument(
        "--hotkey",
        metavar="HOTKEY",
        help="Set the trigger hotkey (e.g., 'ctrl+shift+space', 'f12')"
    )
    parser.add_argument(
        "--no-speech",
        action="store_true",
        help="Disable speech capture"
    )
    parser.add_argument(
        "--continuous-listen",
        action="store_true",
        help="Enable continuous background listening"
    )
    parser.add_argument(
        "--speech-timeout",
        type=float,
        metavar="SECONDS",
        help="Max seconds to wait for speech (default: 3.0)"
    )

    args = parser.parse_args()

    # Handle API key setup
    if args.set_key:
        from .config import set_api_key
        set_api_key(args.set_key)
        print("API key saved successfully!")
        return

    # Handle hotkey configuration
    if args.hotkey:
        from .config import load_config, save_config
        config = load_config()
        config["hotkey"] = args.hotkey
        save_config(config)
        print(f"Hotkey set to: {args.hotkey}")
        return

    # Run the application
    app = DisplayCapApp()

    # Apply command line overrides
    if args.no_speech:
        app.speech_enabled = False
    if args.continuous_listen:
        app.use_continuous_listening = True
    if args.speech_timeout:
        app.config["speech_timeout"] = args.speech_timeout

    if not app.initialize():
        sys.exit(1)

    app.run()


if __name__ == "__main__":
    main()
