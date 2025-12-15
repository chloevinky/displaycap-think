"""
Game state tracker for League of Legends assistant.

Stores and manages information gathered from analyzing game screenshots,
providing contextual data for AI-powered advice.
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import deque
from threading import Lock


@dataclass
class DetectedChampion:
    """A champion detected in the game."""
    name: str
    team: str  # "ally" or "enemy"
    role: Optional[str] = None  # "top", "jungle", "mid", "adc", "support"
    level: Optional[int] = None
    detected_at: float = field(default_factory=time.time)


@dataclass
class DetectedItem:
    """An item detected in the game."""
    name: str
    owner: Optional[str] = None  # Champion name
    slot: Optional[int] = None
    detected_at: float = field(default_factory=time.time)


@dataclass
class GameEvent:
    """A significant game event detected from screenshots."""
    event_type: str  # "kill", "dragon", "baron", "tower", "objective", "teamfight"
    description: str
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreenshotAnalysis:
    """Results from analyzing a single screenshot."""
    timestamp: float
    image_base64: str
    detected_champions: List[str] = field(default_factory=list)
    detected_items: List[str] = field(default_factory=list)
    game_phase: Optional[str] = None  # "early", "mid", "late", "teamfight"
    gold_difference: Optional[int] = None
    objectives_visible: List[str] = field(default_factory=list)
    minimap_info: Optional[str] = None
    shop_open: bool = False
    current_screen: str = "game"  # "game", "shop", "scoreboard", "loading", "menu"
    raw_analysis: str = ""


class GameStateTracker:
    """
    Tracks the state of a League of Legends game over time.

    Stores information gathered from screenshot analysis to provide
    contextual advice when the user requests help.
    """

    def __init__(self, max_history: int = 60):
        """
        Initialize the game state tracker.

        Args:
            max_history: Maximum number of screenshot analyses to keep
                        (at 2 sec intervals, 60 = 2 minutes of history)
        """
        self._lock = Lock()

        # Game identification
        self.game_mode: Optional[str] = None  # "CLASSIC", "ARAM", "ARENA", etc.
        self.map_name: Optional[str] = None
        self.game_start_time: Optional[float] = None

        # Player info
        self.my_champion: Optional[str] = None
        self.my_role: Optional[str] = None
        self.my_summoner_spells: List[str] = []

        # Team compositions
        self.ally_champions: Dict[str, DetectedChampion] = {}
        self.enemy_champions: Dict[str, DetectedChampion] = {}

        # Items tracking
        self.my_items: List[str] = []
        self.enemy_items: Dict[str, List[str]] = {}  # champion -> items

        # Game events history
        self.events: deque = deque(maxlen=100)

        # Screenshot analysis history
        self.analysis_history: deque = deque(maxlen=max_history)

        # Current game phase tracking
        self.current_phase: str = "unknown"  # "loading", "early", "mid", "late"
        self.estimated_game_time: Optional[int] = None  # minutes

        # Objective tracking
        self.dragons_taken: int = 0
        self.barons_taken: int = 0
        self.towers_destroyed: int = 0

        # State flags
        self.is_in_shop: bool = False
        self.is_dead: bool = False
        self.last_update: float = 0

    def start_new_game(self, game_mode: str = "CLASSIC"):
        """Reset tracker for a new game."""
        with self._lock:
            self.game_mode = game_mode
            self.game_start_time = time.time()
            self.my_champion = None
            self.my_role = None
            self.my_summoner_spells = []
            self.ally_champions.clear()
            self.enemy_champions.clear()
            self.my_items.clear()
            self.enemy_items.clear()
            self.events.clear()
            self.analysis_history.clear()
            self.current_phase = "loading"
            self.estimated_game_time = 0
            self.dragons_taken = 0
            self.barons_taken = 0
            self.towers_destroyed = 0
            self.is_in_shop = False
            self.is_dead = False
            self.last_update = time.time()

    def add_screenshot_analysis(self, analysis: ScreenshotAnalysis):
        """Add a new screenshot analysis to history."""
        with self._lock:
            self.analysis_history.append(analysis)
            self.last_update = time.time()

            # Update state based on analysis
            if analysis.shop_open:
                self.is_in_shop = True
            else:
                self.is_in_shop = False

            if analysis.game_phase:
                self.current_phase = analysis.game_phase

            # Track detected champions
            for champ in analysis.detected_champions:
                # Simple heuristic: if we don't know our champion yet,
                # the first one detected is likely ours
                if not self.my_champion and champ:
                    self.my_champion = champ

    def update_enemy_champion(self, name: str, role: Optional[str] = None):
        """Update or add an enemy champion."""
        with self._lock:
            if name not in self.enemy_champions:
                self.enemy_champions[name] = DetectedChampion(
                    name=name,
                    team="enemy",
                    role=role
                )
            elif role:
                self.enemy_champions[name].role = role

    def update_ally_champion(self, name: str, role: Optional[str] = None):
        """Update or add an ally champion."""
        with self._lock:
            if name not in self.ally_champions:
                self.ally_champions[name] = DetectedChampion(
                    name=name,
                    team="ally",
                    role=role
                )
            elif role:
                self.ally_champions[name].role = role

    def update_my_items(self, items: List[str]):
        """Update current player's items."""
        with self._lock:
            self.my_items = items.copy()

    def add_event(self, event_type: str, description: str, **details):
        """Record a game event."""
        with self._lock:
            self.events.append(GameEvent(
                event_type=event_type,
                description=description,
                details=details
            ))

    def get_recent_analyses(self, count: int = 5) -> List[ScreenshotAnalysis]:
        """Get the most recent screenshot analyses."""
        with self._lock:
            return list(self.analysis_history)[-count:]

    def get_recent_images_base64(self, count: int = 3) -> List[str]:
        """Get base64 encoded images from recent analyses."""
        with self._lock:
            recent = list(self.analysis_history)[-count:]
            return [a.image_base64 for a in recent if a.image_base64]

    def get_context_summary(self) -> str:
        """
        Get a summary of current game state for AI context.

        Returns a formatted string with all relevant game information.
        """
        with self._lock:
            lines = ["=== Current Game State ==="]

            # Game info
            if self.game_mode:
                lines.append(f"Mode: {self.game_mode}")

            if self.estimated_game_time:
                lines.append(f"Game Time: ~{self.estimated_game_time} minutes")

            lines.append(f"Phase: {self.current_phase}")

            # My champion
            if self.my_champion:
                lines.append(f"\nMy Champion: {self.my_champion}")
                if self.my_role:
                    lines.append(f"Role: {self.my_role}")

            # My items
            if self.my_items:
                lines.append(f"My Items: {', '.join(self.my_items)}")

            # Current state
            if self.is_in_shop:
                lines.append("\n*** CURRENTLY IN SHOP ***")

            if self.is_dead:
                lines.append("*** CURRENTLY DEAD ***")

            # Enemy team
            if self.enemy_champions:
                lines.append("\nEnemy Team:")
                for champ in self.enemy_champions.values():
                    role_str = f" ({champ.role})" if champ.role else ""
                    lines.append(f"  - {champ.name}{role_str}")

            # Ally team
            if self.ally_champions:
                lines.append("\nAlly Team:")
                for champ in self.ally_champions.values():
                    role_str = f" ({champ.role})" if champ.role else ""
                    lines.append(f"  - {champ.name}{role_str}")

            # Objectives
            if self.dragons_taken or self.barons_taken:
                lines.append(f"\nObjectives: {self.dragons_taken} dragons, {self.barons_taken} barons")

            # Recent events
            recent_events = list(self.events)[-5:]
            if recent_events:
                lines.append("\nRecent Events:")
                for event in recent_events:
                    lines.append(f"  - {event.description}")

            # Recent analysis insights
            recent = list(self.analysis_history)[-3:]
            if recent:
                lines.append("\nRecent Screen Analysis:")
                for analysis in recent:
                    if analysis.raw_analysis:
                        # Truncate long analyses
                        summary = analysis.raw_analysis[:200]
                        if len(analysis.raw_analysis) > 200:
                            summary += "..."
                        lines.append(f"  - {summary}")

            return "\n".join(lines)

    def get_item_recommendation_context(self) -> str:
        """
        Get context specifically for item recommendations.

        Returns a focused summary for when the player is in the shop.
        """
        with self._lock:
            lines = ["=== Item Recommendation Context ==="]

            if self.game_mode:
                lines.append(f"Game Mode: {self.game_mode}")

            if self.my_champion:
                lines.append(f"Playing: {self.my_champion}")

            if self.my_items:
                lines.append(f"Current Items: {', '.join(self.my_items)}")
            else:
                lines.append("Current Items: None")

            lines.append(f"Game Phase: {self.current_phase}")

            if self.enemy_champions:
                lines.append("\nEnemy Champions to Counter:")
                enemy_tags = []
                for champ in self.enemy_champions.values():
                    enemy_tags.append(champ.name)
                lines.append(f"  {', '.join(enemy_tags)}")

            # Add detected enemy items for counter-building
            if self.enemy_items:
                lines.append("\nEnemy Items Detected:")
                for champ, items in self.enemy_items.items():
                    if items:
                        lines.append(f"  {champ}: {', '.join(items)}")

            return "\n".join(lines)

    def estimate_game_phase(self, game_time_minutes: int) -> str:
        """Estimate game phase based on time."""
        if game_time_minutes < 15:
            return "early"
        elif game_time_minutes < 25:
            return "mid"
        else:
            return "late"

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        with self._lock:
            return {
                "game_mode": self.game_mode,
                "my_champion": self.my_champion,
                "my_role": self.my_role,
                "my_items": self.my_items,
                "enemy_champions": [c.name for c in self.enemy_champions.values()],
                "ally_champions": [c.name for c in self.ally_champions.values()],
                "current_phase": self.current_phase,
                "is_in_shop": self.is_in_shop,
                "is_dead": self.is_dead,
                "estimated_game_time": self.estimated_game_time,
                "dragons_taken": self.dragons_taken,
                "barons_taken": self.barons_taken,
                "analysis_count": len(self.analysis_history),
                "last_update": self.last_update,
            }


class GameStateManager:
    """
    Singleton manager for game state across the application.

    Provides a central point for tracking and accessing game state.
    """

    _instance: Optional['GameStateManager'] = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._tracker = GameStateTracker()
            return cls._instance

    @property
    def tracker(self) -> GameStateTracker:
        return self._tracker

    def reset(self):
        """Reset the game state tracker."""
        self._tracker = GameStateTracker()

    @classmethod
    def get_instance(cls) -> 'GameStateManager':
        """Get or create the singleton instance."""
        return cls()
