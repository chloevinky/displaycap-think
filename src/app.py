"""
Main application module for DisplayCap Think.
"""

import sys
import threading
import tkinter as tk
from typing import Optional

from .screenshot import capture_sequence, screenshots_to_base64
from .api_client import create_client, analyze_screenshots
from .display import ResponseWindow, StatusIndicator
from .hotkey import HotkeyManager
from .config import load_config, get_api_key


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

        return True

    def _capture_and_analyze(self):
        """Capture screenshots and send to AI for analysis."""
        if self.is_processing:
            return

        self.is_processing = True

        try:
            # Show status on main thread
            self._root.after(0, lambda: self._show_status("Capturing..."))

            # Capture screenshots
            count = self.config.get("screenshot_count", 3)
            interval = self.config.get("screenshot_interval", 0.5)

            screenshots = capture_sequence(count=count, interval=interval)

            # Update status
            self._root.after(0, lambda: self._update_status("Analyzing..."))

            # Convert to base64
            quality = self.config.get("image_quality", 85)
            images_base64 = screenshots_to_base64(screenshots, quality=quality)

            # Send to API
            response = analyze_screenshots(self.client, images_base64)

            # Show response
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

        # Create response window
        self.response_window = ResponseWindow()

        # Start hotkey listener
        self.hotkey_manager.start(self._on_hotkey)

        hotkey = self.hotkey_manager.get_hotkey()
        print(f"DisplayCap Think is running!")
        print(f"Press {hotkey.upper()} to capture and analyze your screen")
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

    if not app.initialize():
        sys.exit(1)

    app.run()


if __name__ == "__main__":
    main()
