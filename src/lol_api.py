"""
League of Legends API client for fetching game data from Data Dragon and LCU.

Data Dragon: Riot's static game data API (champions, items, runes, etc.)
LCU (League Client Update): Local API for live game data when client is running
"""

import os
import json
import time
import base64
import ssl
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


# Data Dragon base URLs
DDRAGON_BASE = "https://ddragon.leagueoflegends.com"
DDRAGON_VERSIONS_URL = f"{DDRAGON_BASE}/api/versions.json"

# LCU API runs locally
LCU_BASE = "https://127.0.0.1"


@dataclass
class ChampionData:
    """Champion information."""
    id: str
    name: str
    title: str
    tags: List[str]  # e.g., ["Fighter", "Tank"]
    stats: Dict[str, float] = field(default_factory=dict)


@dataclass
class ItemData:
    """Item information."""
    id: str
    name: str
    description: str
    gold: int
    tags: List[str]
    stats: Dict[str, float] = field(default_factory=dict)
    from_items: List[str] = field(default_factory=list)
    into_items: List[str] = field(default_factory=list)


@dataclass
class GameModeInfo:
    """Game mode information."""
    mode: str  # CLASSIC, ARAM, etc.
    map_name: str
    description: str


class DataDragonClient:
    """Client for Riot's Data Dragon API - static game data."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or self._get_default_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.current_version: Optional[str] = None
        self.champions: Dict[str, ChampionData] = {}
        self.items: Dict[str, ItemData] = {}
        self.game_modes: Dict[str, GameModeInfo] = {}

        # Cache timestamps
        self._cache_expiry = 24 * 60 * 60  # 24 hours

    def _get_default_cache_dir(self) -> Path:
        """Get the default cache directory."""
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", Path.home()))
        else:
            base = Path.home() / ".config"
        return base / "lol-assistant" / "cache"

    def _fetch_json(self, url: str) -> Optional[Dict]:
        """Fetch JSON from URL."""
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except (urllib.error.URLError, json.JSONDecodeError) as e:
            print(f"Error fetching {url}: {e}")
            return None

    def _load_cache(self, cache_name: str) -> Optional[Dict]:
        """Load data from cache if not expired."""
        cache_file = self.cache_dir / f"{cache_name}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                    if time.time() - cached.get('timestamp', 0) < self._cache_expiry:
                        return cached.get('data')
            except (json.JSONDecodeError, IOError):
                pass
        return None

    def _save_cache(self, cache_name: str, data: Dict):
        """Save data to cache."""
        cache_file = self.cache_dir / f"{cache_name}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'timestamp': time.time(), 'data': data}, f)
        except IOError as e:
            print(f"Error saving cache: {e}")

    def fetch_latest_version(self) -> Optional[str]:
        """Fetch the latest game version."""
        # Check cache first
        cached = self._load_cache('version')
        if cached:
            self.current_version = cached.get('version')
            return self.current_version

        versions = self._fetch_json(DDRAGON_VERSIONS_URL)
        if versions and len(versions) > 0:
            self.current_version = versions[0]
            self._save_cache('version', {'version': self.current_version})
            return self.current_version
        return None

    def fetch_champions(self) -> Dict[str, ChampionData]:
        """Fetch all champion data."""
        if not self.current_version:
            self.fetch_latest_version()

        if not self.current_version:
            return {}

        # Check cache
        cached = self._load_cache('champions')
        if cached:
            self.champions = {
                k: ChampionData(**v) for k, v in cached.items()
            }
            return self.champions

        url = f"{DDRAGON_BASE}/cdn/{self.current_version}/data/en_US/champion.json"
        data = self._fetch_json(url)

        if data and 'data' in data:
            for champ_id, champ_data in data['data'].items():
                self.champions[champ_id] = ChampionData(
                    id=champ_id,
                    name=champ_data.get('name', champ_id),
                    title=champ_data.get('title', ''),
                    tags=champ_data.get('tags', []),
                    stats=champ_data.get('stats', {})
                )

            # Cache the data
            cache_data = {k: vars(v) for k, v in self.champions.items()}
            self._save_cache('champions', cache_data)

        return self.champions

    def fetch_items(self) -> Dict[str, ItemData]:
        """Fetch all item data."""
        if not self.current_version:
            self.fetch_latest_version()

        if not self.current_version:
            return {}

        # Check cache
        cached = self._load_cache('items')
        if cached:
            self.items = {
                k: ItemData(**v) for k, v in cached.items()
            }
            return self.items

        url = f"{DDRAGON_BASE}/cdn/{self.current_version}/data/en_US/item.json"
        data = self._fetch_json(url)

        if data and 'data' in data:
            for item_id, item_data in data['data'].items():
                # Skip non-purchasable items
                if not item_data.get('gold', {}).get('purchasable', True):
                    continue

                self.items[item_id] = ItemData(
                    id=item_id,
                    name=item_data.get('name', f'Item {item_id}'),
                    description=item_data.get('plaintext', ''),
                    gold=item_data.get('gold', {}).get('total', 0),
                    tags=item_data.get('tags', []),
                    stats=item_data.get('stats', {}),
                    from_items=item_data.get('from', []),
                    into_items=item_data.get('into', [])
                )

            # Cache the data
            cache_data = {k: vars(v) for k, v in self.items.items()}
            self._save_cache('items', cache_data)

        return self.items

    def initialize(self) -> bool:
        """Initialize the client by fetching all data."""
        print("Fetching League of Legends game data...")

        version = self.fetch_latest_version()
        if not version:
            print("Warning: Could not fetch game version, using cached data if available")
            return False

        print(f"Game version: {version}")

        self.fetch_champions()
        print(f"Loaded {len(self.champions)} champions")

        self.fetch_items()
        print(f"Loaded {len(self.items)} items")

        return True

    def get_champion_by_name(self, name: str) -> Optional[ChampionData]:
        """Find a champion by name (case-insensitive)."""
        name_lower = name.lower()
        for champ in self.champions.values():
            if champ.name.lower() == name_lower or champ.id.lower() == name_lower:
                return champ
        return None

    def get_item_by_name(self, name: str) -> Optional[ItemData]:
        """Find an item by name (case-insensitive)."""
        name_lower = name.lower()
        for item in self.items.values():
            if item.name.lower() == name_lower:
                return item
        return None

    def get_items_for_champion(self, champion: ChampionData, game_mode: str = "CLASSIC") -> List[ItemData]:
        """Get recommended items for a champion based on their tags."""
        recommended = []

        # Map champion tags to item tags
        tag_mapping = {
            "Fighter": ["Damage", "Health", "LifeSteal"],
            "Tank": ["Health", "Armor", "SpellBlock"],
            "Mage": ["SpellDamage", "Mana", "CooldownReduction"],
            "Assassin": ["Damage", "CriticalStrike", "LifeSteal"],
            "Marksman": ["Damage", "CriticalStrike", "AttackSpeed"],
            "Support": ["Health", "Mana", "CooldownReduction", "GoldPer"],
        }

        relevant_tags = set()
        for champ_tag in champion.tags:
            if champ_tag in tag_mapping:
                relevant_tags.update(tag_mapping[champ_tag])

        for item in self.items.values():
            if any(tag in item.tags for tag in relevant_tags):
                recommended.append(item)

        # Sort by gold cost (assuming higher cost = better)
        recommended.sort(key=lambda x: x.gold, reverse=True)

        return recommended[:20]  # Top 20 recommendations

    def get_counter_items(self, enemy_champions: List[ChampionData]) -> List[ItemData]:
        """Get items that counter specific enemy champions."""
        counter_items = []

        # Analyze enemy team composition
        has_ap = any("Mage" in c.tags for c in enemy_champions)
        has_ad = any("Marksman" in c.tags or "Fighter" in c.tags or "Assassin" in c.tags for c in enemy_champions)
        has_healing = any("LifeSteal" in str(c.stats) for c in enemy_champions)

        for item in self.items.values():
            # Armor items vs AD
            if has_ad and "Armor" in item.tags:
                counter_items.append(item)
            # Magic resist vs AP
            if has_ap and "SpellBlock" in item.tags:
                counter_items.append(item)

        return counter_items[:10]

    def get_summary_for_ai(self) -> str:
        """Get a summary of game data for AI context."""
        summary = f"League of Legends Patch {self.current_version}\n"
        summary += f"Champions available: {len(self.champions)}\n"
        summary += f"Items available: {len(self.items)}\n\n"

        # Group champions by role
        roles = {}
        for champ in self.champions.values():
            for tag in champ.tags:
                if tag not in roles:
                    roles[tag] = []
                roles[tag].append(champ.name)

        summary += "Champion roles:\n"
        for role, champs in sorted(roles.items()):
            summary += f"  {role}: {len(champs)} champions\n"

        return summary


class LCUClient:
    """
    Client for League Client Update API - live game data.

    The LCU API runs locally when the League client is open.
    It requires authentication via a lockfile created by the client.
    """

    def __init__(self):
        self.port: Optional[int] = None
        self.auth_token: Optional[str] = None
        self.connected = False

    def wait_for_client(
        self,
        timeout: float = 300.0,
        poll_interval: float = 2.0,
        verbose: bool = True
    ) -> bool:
        """
        Wait for the League client to become available.

        Args:
            timeout: Maximum time to wait in seconds (default: 5 minutes)
            poll_interval: Time between connection attempts in seconds (default: 2s)
            verbose: Whether to print status messages

        Returns:
            True if connected successfully, False if timed out
        """
        if self.connected:
            return True

        start_time = time.time()
        attempt = 0

        if verbose:
            print(f"Waiting for League client (timeout: {int(timeout)}s)...")

        while time.time() - start_time < timeout:
            attempt += 1

            if self.connect():
                if verbose:
                    elapsed = time.time() - start_time
                    print(f"Connected to League client after {elapsed:.1f}s")
                return True

            # Show periodic status updates
            if verbose and attempt % 5 == 0:
                elapsed = time.time() - start_time
                remaining = timeout - elapsed
                print(f"  Still waiting... ({int(remaining)}s remaining)")

            time.sleep(poll_interval)

        if verbose:
            print(f"Timed out waiting for League client after {timeout}s")

        return False

    def _find_lockfile(self) -> Optional[Path]:
        """Find the League client lockfile."""
        # Common installation paths
        possible_paths = [
            Path("C:/Riot Games/League of Legends/lockfile"),
            Path("D:/Riot Games/League of Legends/lockfile"),
            Path(os.path.expanduser("~")) / "Riot Games/League of Legends/lockfile",
        ]

        for path in possible_paths:
            if path.exists():
                return path

        return None

    def connect(self) -> bool:
        """Attempt to connect to the LCU API."""
        lockfile = self._find_lockfile()

        if not lockfile:
            return False

        try:
            with open(lockfile, 'r') as f:
                content = f.read()
                parts = content.split(':')
                if len(parts) >= 4:
                    self.port = int(parts[2])
                    self.auth_token = parts[3]
                    self.connected = True
                    return True
        except (IOError, ValueError, IndexError):
            pass

        return False

    def _make_request(self, endpoint: str) -> Optional[Dict]:
        """Make a request to the LCU API."""
        if not self.connected:
            return None

        url = f"{LCU_BASE}:{self.port}{endpoint}"
        auth = base64.b64encode(f"riot:{self.auth_token}".encode()).decode()

        # Create SSL context that doesn't verify (LCU uses self-signed cert)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            req = urllib.request.Request(
                url,
                headers={
                    'Authorization': f'Basic {auth}',
                    'Accept': 'application/json'
                }
            )
            with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                return json.loads(response.read().decode('utf-8'))
        except (urllib.error.URLError, json.JSONDecodeError):
            return None

    def get_current_summoner(self) -> Optional[Dict]:
        """Get current logged-in summoner info."""
        return self._make_request("/lol-summoner/v1/current-summoner")

    def get_gameflow_phase(self) -> Optional[str]:
        """Get current game phase (e.g., None, ChampSelect, InGame)."""
        result = self._make_request("/lol-gameflow/v1/gameflow-phase")
        return result if isinstance(result, str) else None

    def get_champ_select_session(self) -> Optional[Dict]:
        """Get champion select session info."""
        return self._make_request("/lol-champ-select/v1/session")

    def get_active_game(self) -> Optional[Dict]:
        """Get info about the active game."""
        return self._make_request("/lol-gameflow/v1/session")

    def is_in_game(self) -> bool:
        """Check if currently in a game."""
        phase = self.get_gameflow_phase()
        return phase in ["InProgress", "WaitingForStats", "PreEndOfGame", "EndOfGame"]

    def is_in_champ_select(self) -> bool:
        """Check if currently in champion select."""
        phase = self.get_gameflow_phase()
        return phase == "ChampSelect"


class LoLDataManager:
    """
    Main manager for all League of Legends data.

    Combines Data Dragon (static data) and LCU (live data) clients.
    """

    def __init__(self):
        self.ddragon = DataDragonClient()
        self.lcu = LCUClient()
        self.initialized = False

    def initialize(
        self,
        wait_for_client: bool = True,
        wait_timeout: float = 300.0,
        wait_poll_interval: float = 2.0
    ) -> bool:
        """
        Initialize all data sources.

        Args:
            wait_for_client: Whether to wait for the League client to become available
            wait_timeout: Maximum time to wait for client in seconds (default: 5 minutes)
            wait_poll_interval: Time between connection attempts in seconds (default: 2s)

        Returns:
            True if Data Dragon initialization succeeded (LCU is optional)
        """
        # Always try to get Data Dragon data
        dd_success = self.ddragon.initialize()

        # Connect to LCU - either wait or try once
        if wait_for_client:
            lcu_success = self.lcu.wait_for_client(
                timeout=wait_timeout,
                poll_interval=wait_poll_interval,
                verbose=True
            )
        else:
            lcu_success = self.lcu.connect()
            if lcu_success:
                print("Connected to League client")
            else:
                print("League client not detected (live game features disabled)")

        self.initialized = dd_success
        return dd_success

    def get_game_context(self) -> Dict[str, Any]:
        """Get current game context for AI analysis."""
        context = {
            "patch_version": self.ddragon.current_version,
            "total_champions": len(self.ddragon.champions),
            "total_items": len(self.ddragon.items),
            "client_connected": self.lcu.connected,
            "in_game": False,
            "in_champ_select": False,
            "game_mode": None,
            "my_champion": None,
            "enemy_team": [],
            "ally_team": [],
        }

        if self.lcu.connected:
            context["in_game"] = self.lcu.is_in_game()
            context["in_champ_select"] = self.lcu.is_in_champ_select()

            if context["in_champ_select"]:
                session = self.lcu.get_champ_select_session()
                if session:
                    context["game_mode"] = session.get("gameType", "CLASSIC")

            if context["in_game"]:
                game_data = self.lcu.get_active_game()
                if game_data:
                    context["game_mode"] = game_data.get("gameData", {}).get("queue", {}).get("gameMode", "CLASSIC")

        return context

    def get_ai_context_string(self) -> str:
        """Get formatted context string for AI prompts."""
        ctx = self.get_game_context()

        lines = [
            f"=== League of Legends Game Data ===",
            f"Patch: {ctx['patch_version']}",
            f"Champions: {ctx['total_champions']} | Items: {ctx['total_items']}",
        ]

        if ctx['client_connected']:
            lines.append(f"Client: Connected")
            if ctx['in_game']:
                lines.append(f"Status: IN GAME ({ctx['game_mode']})")
            elif ctx['in_champ_select']:
                lines.append(f"Status: CHAMPION SELECT ({ctx['game_mode']})")
            else:
                lines.append(f"Status: In client")
        else:
            lines.append("Client: Not detected")

        return "\n".join(lines)

    @property
    def champions(self) -> Dict[str, ChampionData]:
        return self.ddragon.champions

    @property
    def items(self) -> Dict[str, ItemData]:
        return self.ddragon.items
