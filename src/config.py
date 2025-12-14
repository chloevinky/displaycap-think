"""
Configuration management for DisplayCap Think.
"""

import os
import json
from pathlib import Path
from typing import Optional


DEFAULT_CONFIG = {
    "hotkey": "ctrl+shift+space",
    "screenshot_count": 3,
    "screenshot_interval": 0.5,  # seconds between captures (3 shots in 1 second = 0.5s interval)
    "image_quality": 85,
    "max_response_tokens": 300,
}


def get_config_path() -> Path:
    """Get the path to the config file."""
    # Use AppData on Windows, ~/.config on Linux/Mac
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".config"

    config_dir = base / "displaycap-think"
    config_dir.mkdir(parents=True, exist_ok=True)

    return config_dir / "config.json"


def load_config() -> dict:
    """Load configuration from file or return defaults."""
    config_path = get_config_path()

    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                user_config = json.load(f)
                # Merge with defaults
                config = DEFAULT_CONFIG.copy()
                config.update(user_config)
                return config
        except (json.JSONDecodeError, IOError):
            pass

    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """Save configuration to file."""
    config_path = get_config_path()

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def get_api_key() -> Optional[str]:
    """
    Get the Anthropic API key from environment or config.

    Checks in order:
    1. ANTHROPIC_API_KEY environment variable
    2. Config file

    Returns:
        API key string or None if not found
    """
    # First check environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return api_key

    # Then check config file
    config = load_config()
    return config.get("api_key")


def set_api_key(api_key: str):
    """Save API key to config file."""
    config = load_config()
    config["api_key"] = api_key
    save_config(config)
