"""
Screenshot capture module for League of Legends assistant.

Captures screenshots from the LoL game window or primary monitor,
with support for automatic periodic capture for live game tracking.
"""

import time
import base64
import io
import threading
from typing import List, Tuple, Optional, Callable
import mss
from PIL import Image

# Try to import Windows-specific libraries for window detection
try:
    import ctypes
    from ctypes import wintypes
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False


def get_primary_monitor() -> dict:
    """Get the primary monitor's geometry."""
    with mss.mss() as sct:
        # Monitor 0 is the "all monitors" combined, monitor 1 is typically primary
        # We need to find the actual primary monitor
        monitors = sct.monitors

        # Monitor at index 1 is usually the primary on Windows
        if len(monitors) > 1:
            return monitors[1]
        return monitors[0]


def find_lol_window() -> Optional[dict]:
    """
    Find the League of Legends game window.

    Returns window geometry dict compatible with mss, or None if not found.
    """
    if not WINDOWS_AVAILABLE:
        return None

    try:
        # Windows API functions
        user32 = ctypes.windll.user32

        # League of Legends window titles
        window_titles = [
            "League of Legends",
            "League of Legends (TM) Client",
            "League of Legends Game Client",
        ]

        for title in window_titles:
            hwnd = user32.FindWindowW(None, title)
            if hwnd:
                # Get window rect
                rect = wintypes.RECT()
                if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    # Check if window has reasonable size
                    width = rect.right - rect.left
                    height = rect.bottom - rect.top
                    if width > 100 and height > 100:
                        return {
                            "left": rect.left,
                            "top": rect.top,
                            "width": width,
                            "height": height,
                        }
    except Exception:
        pass

    return None


def capture_screenshot(target_window: Optional[dict] = None) -> Image.Image:
    """
    Capture a single screenshot.

    Args:
        target_window: Optional window geometry dict. If None, captures primary monitor.

    Returns:
        PIL Image object
    """
    if target_window is None:
        target_window = get_primary_monitor()

    with mss.mss() as sct:
        screenshot = sct.grab(target_window)
        # Convert to PIL Image
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return img


def capture_lol_screenshot() -> Tuple[Image.Image, bool]:
    """
    Capture a screenshot of the League of Legends window.

    Returns:
        Tuple of (PIL Image, is_lol_window_found)
        If LoL window not found, captures primary monitor instead.
    """
    lol_window = find_lol_window()

    if lol_window:
        img = capture_screenshot(lol_window)
        return img, True
    else:
        # Fallback to primary monitor
        img = capture_screenshot()
        return img, False


def capture_sequence(count: int = 3, interval: float = 0.5) -> List[Image.Image]:
    """
    Capture a sequence of screenshots.

    Args:
        count: Number of screenshots to capture (default: 3)
        interval: Time between captures in seconds (default: 0.5s for 3 in 1 second)

    Returns:
        List of PIL Image objects
    """
    screenshots = []

    for i in range(count):
        img = capture_screenshot()
        screenshots.append(img)

        # Don't sleep after the last capture
        if i < count - 1:
            time.sleep(interval)

    return screenshots


def capture_lol_sequence(count: int = 3, interval: float = 0.5) -> Tuple[List[Image.Image], bool]:
    """
    Capture a sequence of screenshots from LoL window.

    Returns:
        Tuple of (List of PIL Images, is_lol_window_found)
    """
    screenshots = []
    lol_window = find_lol_window()
    found = lol_window is not None

    for i in range(count):
        if lol_window:
            img = capture_screenshot(lol_window)
        else:
            img = capture_screenshot()
        screenshots.append(img)

        if i < count - 1:
            time.sleep(interval)

    return screenshots, found


def image_to_base64(img: Image.Image, quality: int = 85, max_size: Tuple[int, int] = (1920, 1080)) -> str:
    """
    Convert a PIL Image to base64 string, with optional resizing for API efficiency.

    Args:
        img: PIL Image object
        quality: JPEG quality (1-100)
        max_size: Maximum dimensions to resize to

    Returns:
        Base64 encoded string of the image
    """
    # Resize if larger than max_size while maintaining aspect ratio
    if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Convert to JPEG for smaller file size
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)

    return base64.standard_b64encode(buffer.read()).decode("utf-8")


def screenshots_to_base64(screenshots: List[Image.Image], quality: int = 85) -> List[str]:
    """
    Convert a list of screenshots to base64 strings.

    Args:
        screenshots: List of PIL Image objects
        quality: JPEG quality for compression

    Returns:
        List of base64 encoded strings
    """
    return [image_to_base64(img, quality) for img in screenshots]


class AutoCaptureManager:
    """
    Manages automatic periodic screenshot capture for live game tracking.

    Captures screenshots at regular intervals and calls a callback with
    the captured image for processing.
    """

    def __init__(
        self,
        interval: float = 2.0,
        callback: Optional[Callable[[Image.Image, bool], None]] = None,
        auto_detect_lol: bool = True
    ):
        """
        Initialize the auto-capture manager.

        Args:
            interval: Seconds between captures (default: 2.0)
            callback: Function to call with (image, is_lol_window) after each capture
            auto_detect_lol: Whether to try capturing LoL window specifically
        """
        self.interval = interval
        self.callback = callback
        self.auto_detect_lol = auto_detect_lol

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Statistics
        self.captures_total = 0
        self.captures_lol_window = 0
        self.last_capture_time: Optional[float] = None

    def _capture_loop(self):
        """Main capture loop running in background thread."""
        while self._running:
            try:
                start_time = time.time()

                # Capture screenshot
                if self.auto_detect_lol:
                    img, is_lol = capture_lol_screenshot()
                else:
                    img = capture_screenshot()
                    is_lol = False

                # Update statistics
                with self._lock:
                    self.captures_total += 1
                    if is_lol:
                        self.captures_lol_window += 1
                    self.last_capture_time = time.time()

                # Call callback if set
                if self.callback:
                    try:
                        self.callback(img, is_lol)
                    except Exception as e:
                        print(f"Auto-capture callback error: {e}")

                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0, self.interval - elapsed)

                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception as e:
                print(f"Auto-capture error: {e}")
                time.sleep(self.interval)

    def start(self):
        """Start automatic capture."""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()
            print(f"Auto-capture started (every {self.interval}s)")

    def stop(self):
        """Stop automatic capture."""
        with self._lock:
            self._running = False

        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
            print("Auto-capture stopped")

    def is_running(self) -> bool:
        """Check if auto-capture is running."""
        return self._running

    def set_interval(self, interval: float):
        """Change the capture interval."""
        with self._lock:
            self.interval = max(0.5, interval)  # Minimum 0.5s

    def set_callback(self, callback: Callable[[Image.Image, bool], None]):
        """Set or change the capture callback."""
        self.callback = callback

    def get_stats(self) -> dict:
        """Get capture statistics."""
        with self._lock:
            return {
                "total_captures": self.captures_total,
                "lol_window_captures": self.captures_lol_window,
                "last_capture": self.last_capture_time,
                "interval": self.interval,
                "running": self._running,
            }
