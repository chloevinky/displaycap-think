"""
Display module - shows AI responses in a window on the secondary monitor.

Styled for League of Legends assistant with game-appropriate theming.
"""

import tkinter as tk
from tkinter import font as tkfont
from typing import Optional, Callable
from screeninfo import get_monitors


# LoL-inspired color scheme
COLORS = {
    "bg_dark": "#010A13",       # Very dark blue (LoL client background)
    "bg_panel": "#0A1428",      # Dark blue panel
    "gold": "#C8AA6E",          # LoL gold accent
    "gold_light": "#F0E6D2",    # Light gold for text
    "blue_accent": "#0AC8B9",   # Cyan/teal accent
    "text_primary": "#F0E6D2",  # Main text color
    "text_secondary": "#A09B8C", # Muted text
    "border": "#1E2328",        # Border color
    "success": "#0AC8B9",       # Success/positive
    "warning": "#C89B3C",       # Warning
    "danger": "#C8524F",        # Error/danger
}


class ResponseWindow:
    """A floating window to display AI responses on the secondary monitor."""

    def __init__(self):
        self.root: Optional[tk.Tk] = None
        self.label: Optional[tk.Label] = None
        self.status_label: Optional[tk.Label] = None
        self.is_visible = False
        self._on_dismiss: Optional[Callable] = None

    def _get_secondary_monitor_position(self) -> tuple:
        """Get the position for the secondary monitor, or fallback to primary."""
        monitors = get_monitors()

        # Try to find a secondary monitor
        secondary = None
        primary = None

        for monitor in monitors:
            if monitor.is_primary:
                primary = monitor
            else:
                secondary = monitor
                break

        # Use secondary if available, otherwise use primary
        target = secondary if secondary else primary

        if target:
            # Position the window in the center-right of the target monitor
            x = target.x + target.width - 480  # 480px from right edge
            y = target.y + 50  # 50px from top
            return (x, y)

        # Fallback position
        return (100, 100)

    def _create_window(self):
        """Create the tkinter window."""
        if self.root is not None:
            return

        self.root = tk.Tk()
        self.root.title("LoL Assistant")

        # Window styling - LoL dark theme
        self.root.configure(bg=COLORS["bg_dark"])
        self.root.attributes("-topmost", True)  # Always on top
        self.root.overrideredirect(False)  # Show title bar for easy closing

        # Set window size
        window_width = 450
        window_height = 250

        # Position on secondary monitor
        x, y = self._get_secondary_monitor_position()
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Make window semi-transparent (Windows)
        try:
            self.root.attributes("-alpha", 0.95)
        except tk.TclError:
            pass  # Alpha not supported on all systems

        # Create main frame with border effect
        outer_frame = tk.Frame(self.root, bg=COLORS["gold"], padx=1, pady=1)
        outer_frame.pack(fill=tk.BOTH, expand=True)

        inner_frame = tk.Frame(outer_frame, bg=COLORS["bg_panel"], padx=15, pady=12)
        inner_frame.pack(fill=tk.BOTH, expand=True)

        # Header with title and status
        header_frame = tk.Frame(inner_frame, bg=COLORS["bg_panel"])
        header_frame.pack(fill=tk.X)

        # Title label with LoL styling
        title_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        title = tk.Label(
            header_frame,
            text="LoL Assistant",
            font=title_font,
            bg=COLORS["bg_panel"],
            fg=COLORS["gold"]
        )
        title.pack(side=tk.LEFT)

        # Status indicator
        status_font = tkfont.Font(family="Segoe UI", size=9)
        self.status_label = tk.Label(
            header_frame,
            text="Ready",
            font=status_font,
            bg=COLORS["bg_panel"],
            fg=COLORS["blue_accent"]
        )
        self.status_label.pack(side=tk.RIGHT)

        # Separator line
        separator = tk.Frame(inner_frame, bg=COLORS["gold"], height=1)
        separator.pack(fill=tk.X, pady=(8, 10))

        # Response text area
        text_font = tkfont.Font(family="Segoe UI", size=11)
        self.label = tk.Label(
            inner_frame,
            text="Press hotkey to get advice...",
            font=text_font,
            bg=COLORS["bg_panel"],
            fg=COLORS["text_primary"],
            wraplength=420,
            justify=tk.LEFT,
            anchor="nw"
        )
        self.label.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Dismiss hint
        hint_font = tkfont.Font(family="Segoe UI", size=8)
        hint = tk.Label(
            inner_frame,
            text="Press Escape to dismiss | Ctrl+Shift+Space for advice",
            font=hint_font,
            bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"]
        )
        hint.pack(anchor="e")

        # Bind escape key to close
        self.root.bind("<Escape>", lambda e: self.hide())
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

    def show(self, message: str = "Analyzing..."):
        """Show the window with a message."""
        self._create_window()

        if self.label:
            self.label.config(text=message)

        if self.root:
            self.root.deiconify()
            self.is_visible = True
            self.root.lift()
            self.root.focus_force()

    def update_message(self, message: str):
        """Update the displayed message."""
        if self.label:
            self.label.config(text=message)
        if self.root:
            self.root.update()

    def update_status(self, status: str, color: Optional[str] = None):
        """Update the status indicator."""
        if self.status_label:
            self.status_label.config(
                text=status,
                fg=color or COLORS["blue_accent"]
            )
        if self.root:
            self.root.update()

    def set_tracking_status(self, is_tracking: bool, lol_detected: bool = False):
        """Update status to show tracking state."""
        if is_tracking:
            if lol_detected:
                self.update_status("Tracking Game", COLORS["success"])
            else:
                self.update_status("Tracking (LoL not found)", COLORS["warning"])
        else:
            self.update_status("Ready", COLORS["blue_accent"])

    def hide(self):
        """Hide the window."""
        if self.root:
            self.root.withdraw()
            self.is_visible = False
        if self._on_dismiss:
            self._on_dismiss()

    def destroy(self):
        """Destroy the window completely."""
        if self.root:
            self.root.destroy()
            self.root = None
            self.label = None
            self.status_label = None
            self.is_visible = False

    def set_on_dismiss(self, callback: Callable):
        """Set a callback for when the window is dismissed."""
        self._on_dismiss = callback

    def run_mainloop(self):
        """Run the tkinter main loop (blocking)."""
        if self.root:
            self.root.mainloop()


class StatusIndicator:
    """A small status indicator window shown during capture/processing."""

    def __init__(self):
        self.root: Optional[tk.Toplevel] = None
        self.label: Optional[tk.Label] = None

    def show(self, parent: tk.Tk, message: str = "Capturing..."):
        """Show a small status indicator."""
        if self.root:
            self.destroy()

        self.root = tk.Toplevel(parent)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=COLORS["gold"])

        try:
            self.root.attributes("-alpha", 0.95)
        except tk.TclError:
            pass

        # Inner frame with padding
        inner = tk.Frame(self.root, bg=COLORS["bg_panel"], padx=2, pady=2)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        self.label = tk.Label(
            inner,
            text=message,
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_panel"],
            fg=COLORS["gold"],
            padx=15,
            pady=8
        )
        self.label.pack()

        # Position at top-center of primary monitor
        monitors = get_monitors()
        primary = next((m for m in monitors if m.is_primary), monitors[0] if monitors else None)

        if primary:
            x = primary.x + (primary.width // 2) - 75
            y = primary.y + 10
            self.root.geometry(f"+{x}+{y}")

    def update(self, message: str):
        """Update the status message."""
        if self.label:
            self.label.config(text=message)
        if self.root:
            self.root.update()

    def destroy(self):
        """Destroy the status indicator."""
        if self.root:
            self.root.destroy()
            self.root = None
            self.label = None


class GameStatusOverlay:
    """
    Small overlay showing current game tracking status.

    Displayed in a corner to show:
    - Whether auto-capture is active
    - Whether LoL window was detected
    - Number of screenshots captured
    """

    def __init__(self):
        self.root: Optional[tk.Toplevel] = None
        self.capture_label: Optional[tk.Label] = None
        self.lol_label: Optional[tk.Label] = None

    def show(self, parent: tk.Tk):
        """Show the game status overlay."""
        if self.root:
            return

        self.root = tk.Toplevel(parent)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=COLORS["bg_dark"])

        try:
            self.root.attributes("-alpha", 0.85)
        except tk.TclError:
            pass

        # Create content
        frame = tk.Frame(self.root, bg=COLORS["bg_panel"], padx=8, pady=6)
        frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Title
        title_font = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        title = tk.Label(
            frame,
            text="LoL Assistant",
            font=title_font,
            bg=COLORS["bg_panel"],
            fg=COLORS["gold"]
        )
        title.pack(anchor="w")

        # Capture status
        status_font = tkfont.Font(family="Segoe UI", size=8)
        self.capture_label = tk.Label(
            frame,
            text="Captures: 0",
            font=status_font,
            bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"]
        )
        self.capture_label.pack(anchor="w")

        # LoL detection status
        self.lol_label = tk.Label(
            frame,
            text="LoL: Not detected",
            font=status_font,
            bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"]
        )
        self.lol_label.pack(anchor="w")

        # Position at bottom-right of primary monitor
        monitors = get_monitors()
        primary = next((m for m in monitors if m.is_primary), monitors[0] if monitors else None)

        if primary:
            x = primary.x + primary.width - 150
            y = primary.y + primary.height - 100
            self.root.geometry(f"+{x}+{y}")

    def update(self, capture_count: int, lol_detected: bool):
        """Update the overlay status."""
        if self.capture_label:
            self.capture_label.config(text=f"Captures: {capture_count}")

        if self.lol_label:
            if lol_detected:
                self.lol_label.config(
                    text="LoL: Tracking",
                    fg=COLORS["success"]
                )
            else:
                self.lol_label.config(
                    text="LoL: Not detected",
                    fg=COLORS["text_secondary"]
                )

        if self.root:
            self.root.update()

    def hide(self):
        """Hide the overlay."""
        if self.root:
            self.root.withdraw()

    def destroy(self):
        """Destroy the overlay."""
        if self.root:
            self.root.destroy()
            self.root = None
            self.capture_label = None
            self.lol_label = None
