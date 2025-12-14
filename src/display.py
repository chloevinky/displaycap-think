"""
Display module - shows AI responses in a window on the secondary monitor.
"""

import tkinter as tk
from tkinter import font as tkfont
from tkinter import scrolledtext
from typing import Optional, Callable
from screeninfo import get_monitors


class ResponseWindow:
    """A floating window to display AI responses on the secondary monitor."""

    def __init__(self, parent: tk.Tk):
        """
        Initialize the response window.

        Args:
            parent: The parent Tk root window
        """
        self._parent = parent
        self._window: Optional[tk.Toplevel] = None
        self._text_widget: Optional[scrolledtext.ScrolledText] = None
        self._title_label: Optional[tk.Label] = None
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
            x = target.x + target.width - 520  # 520px from right edge
            y = target.y + 50  # 50px from top
            return (x, y)

        # Fallback position
        return (100, 100)

    def _create_window(self):
        """Create the toplevel window."""
        if self._window is not None:
            return

        self._window = tk.Toplevel(self._parent)
        self._window.title("AI Assistant")

        # Window styling
        self._window.configure(bg="#1e1e2e")
        self._window.attributes("-topmost", True)  # Always on top

        # Set window size - larger and more practical
        window_width = 480
        window_height = 350

        # Position on secondary monitor
        x, y = self._get_secondary_monitor_position()
        self._window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Make window semi-transparent (Windows)
        try:
            self._window.attributes("-alpha", 0.95)
        except tk.TclError:
            pass  # Alpha not supported on all systems

        # Create main frame with padding
        main_frame = tk.Frame(self._window, bg="#1e1e2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Header frame with title
        header_frame = tk.Frame(main_frame, bg="#1e1e2e")
        header_frame.pack(fill=tk.X, pady=(0, 8))

        # Title label
        title_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self._title_label = tk.Label(
            header_frame,
            text="AI Assistant",
            font=title_font,
            bg="#1e1e2e",
            fg="#89b4fa"
        )
        self._title_label.pack(side=tk.LEFT)

        # Close button
        close_btn = tk.Label(
            header_frame,
            text="X",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#6c7086",
            cursor="hand2",
            padx=8
        )
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind("<Button-1>", lambda e: self.hide())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#f38ba8"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#6c7086"))

        # Scrollable text widget for response
        text_font = tkfont.Font(family="Consolas", size=10)
        self._text_widget = scrolledtext.ScrolledText(
            main_frame,
            font=text_font,
            bg="#181825",
            fg="#cdd6f4",
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=10,
            pady=10,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#313244",
            highlightcolor="#45475a",
            insertbackground="#cdd6f4",
            selectbackground="#45475a",
            selectforeground="#cdd6f4"
        )
        self._text_widget.pack(fill=tk.BOTH, expand=True)

        # Make text widget read-only initially
        self._text_widget.config(state=tk.DISABLED)

        # Style the scrollbar
        self._text_widget.vbar.config(
            troughcolor="#181825",
            bg="#313244",
            activebackground="#45475a"
        )

        # Hint label at bottom
        hint_frame = tk.Frame(main_frame, bg="#1e1e2e")
        hint_frame.pack(fill=tk.X, pady=(8, 0))

        hint_font = tkfont.Font(family="Segoe UI", size=8)
        hint = tk.Label(
            hint_frame,
            text="Press Escape to dismiss",
            font=hint_font,
            bg="#1e1e2e",
            fg="#585b70"
        )
        hint.pack(side=tk.RIGHT)

        # Bind escape key to close
        self._window.bind("<Escape>", lambda e: self.hide())
        self._window.protocol("WM_DELETE_WINDOW", self.hide)

        # Prevent window from being minimized when clicking on it
        self._window.bind("<FocusIn>", lambda e: self._window.lift())

    def show(self, message: str = "Analyzing..."):
        """Show the window with a message."""
        self._create_window()

        self._set_text(message)

        if self._window:
            self._window.deiconify()
            self.is_visible = True
            self._window.lift()
            # Don't force focus - let user keep working
            self._window.attributes("-topmost", True)

    def _set_text(self, message: str):
        """Set the text content."""
        if self._text_widget:
            self._text_widget.config(state=tk.NORMAL)
            self._text_widget.delete("1.0", tk.END)
            self._text_widget.insert("1.0", message)
            self._text_widget.config(state=tk.DISABLED)
            # Scroll to top
            self._text_widget.see("1.0")

    def update_message(self, message: str):
        """Update the displayed message."""
        self._set_text(message)
        if self._window:
            self._window.update()

    def hide(self):
        """Hide the window."""
        if self._window:
            self._window.withdraw()
            self.is_visible = False
        if self._on_dismiss:
            self._on_dismiss()

    def destroy(self):
        """Destroy the window completely."""
        if self._window:
            self._window.destroy()
            self._window = None
            self._text_widget = None
            self._title_label = None
            self.is_visible = False

    def set_on_dismiss(self, callback: Callable):
        """Set a callback for when the window is dismissed."""
        self._on_dismiss = callback


class StatusIndicator:
    """A small status indicator window shown during capture/processing."""

    def __init__(self, parent: tk.Tk):
        """
        Initialize the status indicator.

        Args:
            parent: The parent Tk root window
        """
        self._parent = parent
        self._window: Optional[tk.Toplevel] = None
        self._label: Optional[tk.Label] = None

    def show(self, message: str = "Capturing..."):
        """Show a small status indicator."""
        if self._window:
            self.destroy()

        self._window = tk.Toplevel(self._parent)
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        self._window.configure(bg="#89b4fa")

        try:
            self._window.attributes("-alpha", 0.9)
        except tk.TclError:
            pass

        self._label = tk.Label(
            self._window,
            text=message,
            font=("Segoe UI", 9),
            bg="#89b4fa",
            fg="#1e1e2e",
            padx=15,
            pady=8
        )
        self._label.pack()

        # Position at top-center of primary monitor
        monitors = get_monitors()
        primary = next((m for m in monitors if m.is_primary), monitors[0] if monitors else None)

        if primary:
            x = primary.x + (primary.width // 2) - 75
            y = primary.y + 10
            self._window.geometry(f"+{x}+{y}")

    def update(self, message: str):
        """Update the status message."""
        if self._label:
            self._label.config(text=message)
        if self._window:
            self._window.update()

    def destroy(self):
        """Destroy the status indicator."""
        if self._window:
            self._window.destroy()
            self._window = None
            self._label = None
