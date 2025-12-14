"""
Screenshot capture module - captures screenshots from the primary monitor.
"""

import time
import base64
import io
from typing import List, Tuple
import mss
from PIL import Image


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


def capture_screenshot() -> Image.Image:
    """Capture a single screenshot of the primary monitor."""
    monitor = get_primary_monitor()

    with mss.mss() as sct:
        screenshot = sct.grab(monitor)
        # Convert to PIL Image
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return img


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
