"""
Display module - shows AI responses in a window on the secondary monitor.
"""

import tkinter as tk
from tkinter import font as tkfont
from typing import Optional, Callable
from screeninfo import get_monitors


class ResponseWindow:
    """A floating window to display AI responses on the secondary monitor."""

    def __init__(self):
        self.root: Optional[tk.Tk] = None
        self.label: Optional[tk.Label] = None
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
            x = target.x + target.width - 450  # 450px from right edge
            y = target.y + 50  # 50px from top
            return (x, y)

        # Fallback position
        return (100, 100)

    def _create_window(self):
        """Create the tkinter window."""
        if self.root is not None:
            return

        self.root = tk.Tk()
        self.root.title("AI Assistant")

        # Window styling
        self.root.configure(bg="#1a1a2e")
        self.root.attributes("-topmost", True)  # Always on top
        self.root.overrideredirect(False)  # Show title bar for easy closing

        # Set window size
        window_width = 400
        window_height = 200

        # Position on secondary monitor
        x, y = self._get_secondary_monitor_position()
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Make window semi-transparent (Windows)
        try:
            self.root.attributes("-alpha", 0.95)
        except tk.TclError:
            pass  # Alpha not supported on all systems

        # Create main frame
        frame = tk.Frame(self.root, bg="#1a1a2e", padx=15, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Title label
        title_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        title = tk.Label(
            frame,
            text="AI Assistant",
            font=title_font,
            bg="#1a1a2e",
            fg="#7b68ee"
        )
        title.pack(anchor="w")

        # Response text
        text_font = tkfont.Font(family="Segoe UI", size=11)
        self.label = tk.Label(
            frame,
            text="Analyzing...",
            font=text_font,
            bg="#1a1a2e",
            fg="#ffffff",
            wraplength=370,
            justify=tk.LEFT,
            anchor="nw"
        )
        self.label.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Dismiss hint
        hint_font = tkfont.Font(family="Segoe UI", size=8)
        hint = tk.Label(
            frame,
            text="Press Escape or click X to dismiss",
            font=hint_font,
            bg="#1a1a2e",
            fg="#666666"
        )
        hint.pack(anchor="e", pady=(10, 0))

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
        self.root.configure(bg="#7b68ee")

        try:
            self.root.attributes("-alpha", 0.9)
        except tk.TclError:
            pass

        self.label = tk.Label(
            self.root,
            text=message,
            font=("Segoe UI", 9),
            bg="#7b68ee",
            fg="#ffffff",
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
