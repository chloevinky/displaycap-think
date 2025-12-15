"""
Main application module for LoL Assistant.

An AI-powered League of Legends assistant that:
- Automatically captures game screenshots every 2 seconds
- Tracks game state from the captured images
- Provides contextual advice when the user presses a hotkey
"""

import sys
import time
import threading
import tkinter as tk
from typing import Optional
import concurrent.futures
from PIL import Image

from .screenshot import (
    capture_lol_sequence,
    screenshots_to_base64,
    image_to_base64,
    AutoCaptureManager
)
from .api_client import create_client, analyze_screenshots, analyze_for_state_tracking, detect_latest_haiku_model
from .display import ResponseWindow, GameStatusOverlay, COLORS
from .hotkey import HotkeyManager
from .config import load_config, get_api_key
from .speech import SpeechCapture, ContinuousListener
from .game_state import GameStateTracker, ScreenshotAnalysis, GameStateManager
from .lol_api import LoLDataManager


class LoLAssistantApp:
    """Main application class for LoL Assistant."""

    def __init__(self):
        self.config = load_config()
        self.api_key: Optional[str] = None
        self.client = None
        self.hotkey_manager = HotkeyManager()
        self.response_window: Optional[ResponseWindow] = None
        self.status_overlay: Optional[GameStatusOverlay] = None
        self.is_processing = False
        self._root: Optional[tk.Tk] = None

        # Speech capture
        self.speech_enabled = self.config.get("speech_enabled", True)
        self.speech_capture: Optional[SpeechCapture] = None
        self.continuous_listener: Optional[ContinuousListener] = None
        self.use_continuous_listening = self.config.get("continuous_listening", False)

        # LoL-specific components
        self.lol_data = LoLDataManager()
        self.game_state = GameStateManager.get_instance().tracker
        self.auto_capture: Optional[AutoCaptureManager] = None

        # Background analysis tracking
        self._capture_count = 0
        self._background_analysis_interval = self.config.get("background_analysis_interval", 10)
        self._last_lol_detected = False

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
            print("[INIT] Creating Anthropic API client...")
            self.client = create_client(self.api_key)
        except Exception as e:
            print(f"[ERROR] Failed to create API client: {e}")
            return False

        # Detect latest haiku model
        detect_latest_haiku_model(self.client)

        # Initialize LoL data (Data Dragon API)
        print("[INIT] Initializing LoL Assistant...")
        self.lol_data.initialize()

        # Set up hotkey
        self.hotkey_manager.set_hotkey(self.config.get("hotkey", "ctrl+shift+space"))

        # Initialize speech capture if enabled
        if self.speech_enabled:
            try:
                print("[VOICE] Initializing speech capture...")
                self.speech_capture = SpeechCapture()
                print("[VOICE] Speech capture enabled - speak after pressing hotkey")

                # Start continuous listening if configured
                if self.use_continuous_listening:
                    print("[VOICE] Starting continuous listening...")
                    self.continuous_listener = ContinuousListener()
                    self.continuous_listener.start()
                    print("[VOICE] Continuous listening active")
            except Exception as e:
                print(f"[VOICE] Warning: Speech capture unavailable: {e}")
                self.speech_enabled = False
        else:
            print("[VOICE] Voice input disabled")

        # Initialize auto-capture
        if self.config.get("auto_capture_enabled", True):
            interval = self.config.get("auto_capture_interval", 2.0)
            print(f"[CAPTURE] Initializing auto-capture (interval: {interval}s)...")
            self.auto_capture = AutoCaptureManager(
                interval=interval,
                callback=self._on_auto_capture,
                auto_detect_lol=self.config.get("auto_detect_lol_window", True)
            )
        else:
            print("[CAPTURE] Auto-capture disabled")

        return True

    def _on_auto_capture(self, image: Image.Image, is_lol_window: bool):
        """
        Callback for automatic screenshot capture.

        Stores the screenshot and optionally runs background analysis.
        """
        self._capture_count += 1
        self._last_lol_detected = is_lol_window

        # Print periodic capture status (every 10 captures to avoid spam)
        if self._capture_count % 10 == 0:
            lol_status = "LoL detected" if is_lol_window else "monitoring"
            print(f"[CAPTURE] #{self._capture_count} ({lol_status})")

        # Convert to base64 for storage
        quality = self.config.get("image_quality", 85)
        img_base64 = image_to_base64(image, quality=quality)

        # Create analysis record
        analysis = ScreenshotAnalysis(
            timestamp=time.time(),
            image_base64=img_base64,
            current_screen="game" if is_lol_window else "unknown"
        )

        # Add to game state tracker
        self.game_state.add_screenshot_analysis(analysis)

        # Run background analysis periodically
        if (self.config.get("background_analysis_enabled", True) and
            self._capture_count % self._background_analysis_interval == 0):
            # Run analysis in background thread to not block capture
            threading.Thread(
                target=self._run_background_analysis,
                args=(img_base64,),
                daemon=True
            ).start()

        # Update UI on main thread
        if self._root and self.status_overlay:
            self._root.after(0, lambda: self._update_overlay())

    def _run_background_analysis(self, img_base64: str):
        """Run background analysis on a screenshot to extract game state."""
        try:
            print("[ANALYZE] Running background state analysis...")
            state = analyze_for_state_tracking(self.client, img_base64)

            # Update game state tracker with extracted info
            if state.get("my_champion"):
                self.game_state.my_champion = state["my_champion"]
                print(f"[ANALYZE] Detected champion: {state['my_champion']}")

            for enemy in state.get("visible_enemies", []):
                self.game_state.update_enemy_champion(enemy)

            if state.get("game_phase") != "unknown":
                self.game_state.current_phase = state["game_phase"]

            self.game_state.is_in_shop = state.get("shop_open", False)

            # Update the latest analysis with parsed info
            recent = self.game_state.get_recent_analyses(1)
            if recent:
                recent[0].raw_analysis = state.get("notes", "")
                recent[0].shop_open = state.get("shop_open", False)
                recent[0].game_phase = state.get("game_phase")

            print(f"[ANALYZE] State: screen={state.get('screen')}, phase={state.get('game_phase')}, shop={state.get('shop_open')}")

        except Exception as e:
            print(f"[ANALYZE] Error: {e}")

    def _update_overlay(self):
        """Update the status overlay UI."""
        if self.status_overlay and self.auto_capture:
            stats = self.auto_capture.get_stats()
            self.status_overlay.update(
                capture_count=stats.get("total_captures", 0),
                lol_detected=self._last_lol_detected
            )

    def _capture_and_analyze(self):
        """Capture screenshots and analyze with full game context for advice."""
        if self.is_processing:
            return

        self.is_processing = True
        speech_text = None

        try:
            print("[HOTKEY] Processing hotkey request...")

            # Check for continuous listening buffer first
            if self.continuous_listener and self.continuous_listener.is_running():
                speech_text = self.continuous_listener.get_recent_speech(clear=True)
                if speech_text:
                    print(f"[VOICE] Got buffered speech: \"{speech_text}\"")

            # Show status on main thread
            status_msg = "Analyzing game..." if not self.speech_enabled else "Analyzing... (listening)"
            self._root.after(0, lambda: self._show_status(status_msg))

            # Get recent screenshots from game state tracker (already captured)
            print("[CAPTURE] Retrieving recent screenshots...")
            recent_images = self.game_state.get_recent_images_base64(count=3)

            # If we don't have recent captures, capture now
            if not recent_images:
                print("[CAPTURE] No cached images, capturing now...")
                count = self.config.get("screenshot_count", 3)
                interval = self.config.get("screenshot_interval", 0.5)
                screenshots, _ = capture_lol_sequence(count=count, interval=interval)
                quality = self.config.get("image_quality", 85)
                recent_images = screenshots_to_base64(screenshots, quality=quality)
            else:
                print(f"[CAPTURE] Using {len(recent_images)} cached screenshots")

            # Capture speech in parallel if enabled and no continuous buffer
            speech_timeout = self.config.get("speech_timeout", 3.0)
            speech_phrase_limit = self.config.get("speech_phrase_limit", 5.0)

            if self.speech_enabled and self.speech_capture and not speech_text:
                print(f"[VOICE] Listening for speech (timeout: {speech_timeout}s)...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    speech_future = executor.submit(
                        self.speech_capture.capture_speech,
                        timeout=speech_timeout,
                        phrase_time_limit=speech_phrase_limit
                    )
                    captured_text, speech_error = speech_future.result()
                    if captured_text:
                        speech_text = captured_text
                        print(f"[VOICE] Captured: \"{speech_text}\"")
                    else:
                        print("[VOICE] No speech detected")
                    if speech_error:
                        print(f"[VOICE] Warning: {speech_error}")

            # Update status
            self._root.after(0, lambda: self._update_status("Getting advice..."))

            # Build game context from tracker
            game_context = self.game_state.get_context_summary()

            # Add LoL API data context
            if self.lol_data.initialized:
                game_context += f"\n\n{self.lol_data.get_ai_context_string()}"

            # If shop is open, add item recommendation context
            if self.game_state.is_in_shop:
                game_context += f"\n\n{self.game_state.get_item_recommendation_context()}"

            # Send to API for analysis
            print("[API] Sending request to Claude...")
            response = analyze_screenshots(
                self.client,
                recent_images,
                user_context=speech_text,
                game_context=game_context
            )
            print("[API] Response received")

            # Show response (include speech indicator if we captured speech)
            if speech_text:
                response = f'[Question: "{speech_text}"]\n\n{response}'

            self._root.after(0, lambda: self._show_response(response))
            print("[DONE] Analysis complete")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"[ERROR] {error_msg}")
            self._root.after(0, lambda: self._show_response(error_msg))

        finally:
            self.is_processing = False

    def _show_status(self, message: str):
        """Show status indicator."""
        if self.response_window:
            self.response_window.show(message)
            self.response_window.update_status("Processing...", COLORS["warning"])

    def _update_status(self, message: str):
        """Update status message."""
        if self.response_window:
            self.response_window.update_message(message)

    def _show_response(self, response: str):
        """Show the AI response in the window."""
        if self.response_window:
            self.response_window.update_message(response)
            self.response_window.update_status(
                "Tracking Game" if self._last_lol_detected else "Ready",
                COLORS["success"] if self._last_lol_detected else COLORS["blue_accent"]
            )

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

        # Create status overlay if enabled
        if self.config.get("show_game_status", True):
            self.status_overlay = GameStatusOverlay()
            # Note: overlay.show() needs to be called after response_window creates its root
            self.response_window._create_window()
            if self.response_window.root:
                self.status_overlay.show(self.response_window.root)

        # Start auto-capture
        if self.auto_capture:
            print("[START] Starting auto-capture...")
            self.auto_capture.start()
            self.game_state.start_new_game()  # Start fresh game state

        # Start hotkey listener
        print("[START] Starting hotkey listener...")
        self.hotkey_manager.start(self._on_hotkey)

        hotkey = self.hotkey_manager.get_hotkey()
        print("")
        print("=" * 50)
        print("  LoL Assistant is running!")
        print("=" * 50)
        print(f"  Hotkey: {hotkey.upper()}")
        print(f"  Voice input: {'ENABLED' if self.speech_enabled else 'DISABLED'}")
        if self.auto_capture:
            print(f"  Auto-capture: every {self.auto_capture.interval}s")
        print("  Press Ctrl+C to exit")
        print("=" * 50)
        print("")

        # Run the tkinter main loop
        try:
            self._root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean up and shut down the application."""
        print("\n[SHUTDOWN] Shutting down LoL Assistant...")

        # Stop auto-capture
        if self.auto_capture:
            print("[SHUTDOWN] Stopping auto-capture...")
            self.auto_capture.stop()

        print("[SHUTDOWN] Stopping hotkey listener...")
        self.hotkey_manager.stop()

        # Stop continuous listener if running
        if self.continuous_listener:
            print("[SHUTDOWN] Stopping continuous listener...")
            self.continuous_listener.stop()

        if self.status_overlay:
            self.status_overlay.destroy()

        if self.response_window:
            self.response_window.destroy()

        if self._root:
            try:
                self._root.quit()
                self._root.destroy()
            except tk.TclError:
                pass

        print("[SHUTDOWN] Complete. Goodbye!")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="LoL Assistant - AI-powered League of Legends Coach"
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
        help="Disable voice input (skip waiting for speech after hotkey)"
    )
    parser.add_argument(
        "--continuous-listen",
        action="store_true",
        help="Enable continuous background listening (buffers recent speech)"
    )
    parser.add_argument(
        "--speech-timeout",
        type=float,
        metavar="SECONDS",
        help="Max seconds to wait for speech to start (default: 3.0)"
    )
    parser.add_argument(
        "--no-auto-capture",
        action="store_true",
        help="Disable automatic screenshot capture"
    )
    parser.add_argument(
        "--capture-interval",
        type=float,
        metavar="SECONDS",
        help="Interval between auto-captures (default: 2.0)"
    )
    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="Disable the status overlay"
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
    app = LoLAssistantApp()

    # Apply command line overrides
    if args.no_speech:
        app.speech_enabled = False
    if args.continuous_listen:
        app.use_continuous_listening = True
    if args.speech_timeout:
        app.config["speech_timeout"] = args.speech_timeout
    if args.no_auto_capture:
        app.config["auto_capture_enabled"] = False
    if args.capture_interval:
        app.config["auto_capture_interval"] = args.capture_interval
    if args.no_overlay:
        app.config["show_game_status"] = False

    if not app.initialize():
        sys.exit(1)

    app.run()


if __name__ == "__main__":
    main()
