"""
Anthropic API client for League of Legends game analysis and assistance.

Analyzes game screenshots and provides contextual advice for items,
strategy, and gameplay based on the current game state.
"""

from typing import List, Optional
import anthropic


# Will be set dynamically by querying available models
_MODEL_ID: Optional[str] = None


def get_model_id(client: anthropic.Anthropic) -> str:
    """
    Get the best available Haiku model by querying the Anthropic API.

    Queries the models endpoint and selects the latest Haiku model available.
    Falls back to a known model ID if the query fails.

    Args:
        client: Anthropic API client

    Returns:
        Model ID string for the best available Haiku model
    """
    global _MODEL_ID

    # Return cached model ID if already determined
    if _MODEL_ID is not None:
        return _MODEL_ID

    # Fallback model IDs in order of preference
    fallback_models = [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-haiku-20240307",
    ]

    try:
        # Query available models from the API
        models_response = client.models.list(limit=100)
        available_models = [model.id for model in models_response.data]

        print(f"Available models: {len(available_models)} found")

        # Look for Haiku models (prefer newer versions)
        haiku_models = [m for m in available_models if "haiku" in m.lower()]

        if haiku_models:
            # Sort to get the latest version (higher dates come later alphabetically)
            haiku_models.sort(reverse=True)
            _MODEL_ID = haiku_models[0]
            print(f"Selected Haiku model: {_MODEL_ID}")
            return _MODEL_ID

        # If no Haiku found, try Sonnet as fallback (still fast enough)
        sonnet_models = [m for m in available_models if "sonnet" in m.lower()]
        if sonnet_models:
            sonnet_models.sort(reverse=True)
            _MODEL_ID = sonnet_models[0]
            print(f"No Haiku available, using Sonnet: {_MODEL_ID}")
            return _MODEL_ID

        # Use first available model from fallbacks that exists
        for fallback in fallback_models:
            if fallback in available_models:
                _MODEL_ID = fallback
                print(f"Using fallback model: {_MODEL_ID}")
                return _MODEL_ID

        # Last resort: use the first available model
        if available_models:
            _MODEL_ID = available_models[0]
            print(f"Using first available model: {_MODEL_ID}")
            return _MODEL_ID

    except Exception as e:
        print(f"Warning: Could not query models API: {e}")

    # Ultimate fallback if API query fails entirely
    _MODEL_ID = fallback_models[0]
    print(f"Using hardcoded fallback model: {_MODEL_ID}")
    return _MODEL_ID

# System prompt focused on League of Legends assistance
SYSTEM_PROMPT = """You are an expert League of Legends coach and assistant. You analyze screenshots of ongoing LoL games and provide strategic advice.

Your capabilities:
1. Identify champions, items, and game state from screenshots
2. Recommend optimal item builds based on:
   - The player's champion
   - Enemy team composition
   - Current game mode (Classic, ARAM, Arena, etc.)
   - Game phase (early, mid, late game)
3. Provide strategic advice for:
   - Laning phase decisions
   - Team fight positioning
   - Objective control
   - Map awareness

Guidelines:
- Keep responses SHORT and actionable (2-4 sentences max)
- Prioritize the most impactful advice
- When recommending items, explain WHY they're good against the enemy team
- Reference specific champions you see in the screenshots
- If you see the shop is open, focus on item recommendations
- If you see a teamfight or combat, focus on ability usage and positioning
- Be direct - the player needs quick advice they can use immediately

Item recommendation priority:
1. Counter-build based on enemy team's damage types
2. Synergize with your champion's kit
3. Consider game phase (don't recommend late-game items early)
4. Account for gold efficiency

Remember: You're giving real-time advice during an active game. Be fast and useful."""

# System prompt for background analysis (lighter analysis to extract game state)
BACKGROUND_ANALYSIS_PROMPT = """You are analyzing League of Legends gameplay screenshots to extract game state information.

Extract and report:
1. Champion identification (player's champion, visible enemies)
2. Current screen type (game, shop, scoreboard, loading)
3. Game phase estimate (early/mid/late based on items, levels visible)
4. Shop status (is shop menu open?)
5. Any visible objectives (dragon, baron, towers)
6. Team composition hints

Format your response as structured data:
SCREEN: [game/shop/scoreboard/loading/menu]
MY_CHAMPION: [champion name or unknown]
VISIBLE_ENEMIES: [comma-separated list or none]
GAME_PHASE: [early/mid/late/unknown]
SHOP_OPEN: [yes/no]
OBJECTIVES: [any visible objectives]
NOTES: [brief observation]

Be concise. This is for tracking game state, not giving advice."""


def create_client(api_key: str) -> anthropic.Anthropic:
    """Create an Anthropic API client and detect available models."""
    client = anthropic.Anthropic(api_key=api_key)
    # Pre-fetch the model ID during initialization
    get_model_id(client)
    return client


def analyze_screenshots(
    client: anthropic.Anthropic,
    screenshots_base64: List[str],
    user_context: Optional[str] = None,
    game_context: Optional[str] = None
) -> str:
    """
    Send screenshots to Claude for analysis and get LoL-specific assistance.

    Args:
        client: Anthropic API client
        screenshots_base64: List of base64-encoded screenshot images
        user_context: Optional additional context from the user (voice input)
        game_context: Optional game state context from tracker

    Returns:
        Claude's response with assistance
    """
    # Build the message content with images
    content = []

    # Add each screenshot as an image
    for img_base64 in screenshots_base64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": img_base64,
            },
        })

    # Build the analysis request
    prompt_parts = [
        "Analyze these League of Legends gameplay screenshots and provide quick, actionable advice."
    ]

    # Add game context if available
    if game_context:
        prompt_parts.append(f"\n\nCurrent game state:\n{game_context}")

    # Add user's specific question if provided
    if user_context:
        prompt_parts.append(f"\n\nPlayer's question: {user_context}")
    else:
        prompt_parts.append("\n\nProvide the most relevant advice based on what you see.")

    content.append({
        "type": "text",
        "text": "\n".join(prompt_parts)
    })

    # Make the API call
    message = client.messages.create(
        model=get_model_id(client),
        max_tokens=400,  # Slightly longer for detailed item recommendations
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": content
            }
        ]
    )

    # Extract the text response
    response_text = ""
    for block in message.content:
        if block.type == "text":
            response_text += block.text

    return response_text.strip()


def analyze_for_state_tracking(
    client: anthropic.Anthropic,
    screenshot_base64: str
) -> dict:
    """
    Analyze a single screenshot for game state tracking.

    This is a lighter analysis meant to run in the background,
    extracting game state information without providing advice.

    Args:
        client: Anthropic API client
        screenshot_base64: Base64-encoded screenshot image

    Returns:
        Dictionary with extracted game state information
    """
    content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": screenshot_base64,
            },
        },
        {
            "type": "text",
            "text": "Extract game state from this League of Legends screenshot."
        }
    ]

    message = client.messages.create(
        model=get_model_id(client),
        max_tokens=200,  # Short response for state extraction
        system=BACKGROUND_ANALYSIS_PROMPT,
        messages=[
            {
                "role": "user",
                "content": content
            }
        ]
    )

    # Parse the structured response
    response_text = ""
    for block in message.content:
        if block.type == "text":
            response_text += block.text

    return parse_state_response(response_text)


def parse_state_response(response: str) -> dict:
    """Parse the structured state tracking response."""
    state = {
        "screen": "unknown",
        "my_champion": None,
        "visible_enemies": [],
        "game_phase": "unknown",
        "shop_open": False,
        "objectives": [],
        "notes": "",
        "raw_response": response
    }

    for line in response.strip().split("\n"):
        line = line.strip()
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip().upper()
        value = value.strip()

        if key == "SCREEN":
            state["screen"] = value.lower()
        elif key == "MY_CHAMPION":
            if value.lower() not in ["unknown", "none", ""]:
                state["my_champion"] = value
        elif key == "VISIBLE_ENEMIES":
            if value.lower() not in ["none", ""]:
                state["visible_enemies"] = [e.strip() for e in value.split(",") if e.strip()]
        elif key == "GAME_PHASE":
            state["game_phase"] = value.lower()
        elif key == "SHOP_OPEN":
            state["shop_open"] = value.lower() in ["yes", "true", "1"]
        elif key == "OBJECTIVES":
            if value.lower() not in ["none", ""]:
                state["objectives"] = [o.strip() for o in value.split(",") if o.strip()]
        elif key == "NOTES":
            state["notes"] = value

    return state


def get_item_recommendation(
    client: anthropic.Anthropic,
    screenshots_base64: List[str],
    my_champion: str,
    enemy_champions: List[str],
    current_items: List[str],
    game_mode: str = "CLASSIC",
    game_phase: str = "mid",
    gold_available: Optional[int] = None
) -> str:
    """
    Get specific item recommendations based on game state.

    Args:
        client: Anthropic API client
        screenshots_base64: Recent game screenshots
        my_champion: Player's champion name
        enemy_champions: List of enemy champion names
        current_items: List of items player currently has
        game_mode: Game mode (CLASSIC, ARAM, ARENA, etc.)
        game_phase: Current game phase
        gold_available: Optional gold amount if known

    Returns:
        Item recommendation string
    """
    content = []

    # Add screenshots
    for img_base64 in screenshots_base64[-2:]:  # Last 2 screenshots
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": img_base64,
            },
        })

    # Build detailed item request
    prompt_parts = [
        f"ITEM RECOMMENDATION REQUEST",
        f"",
        f"My Champion: {my_champion}",
        f"Game Mode: {game_mode}",
        f"Game Phase: {game_phase}",
        f"",
        f"Enemy Team: {', '.join(enemy_champions) if enemy_champions else 'Unknown'}",
        f"My Current Items: {', '.join(current_items) if current_items else 'None'}",
    ]

    if gold_available:
        prompt_parts.append(f"Gold Available: {gold_available}")

    prompt_parts.extend([
        "",
        "What should I buy next? Consider:",
        "1. Enemy team damage types (AP/AD)",
        "2. My champion's power spikes",
        "3. Current game state from screenshots",
        "",
        "Give me 1-2 specific item recommendations with brief reasoning."
    ])

    content.append({
        "type": "text",
        "text": "\n".join(prompt_parts)
    })

    message = client.messages.create(
        model=get_model_id(client),
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": content
            }
        ]
    )

    response_text = ""
    for block in message.content:
        if block.type == "text":
            response_text += block.text

    return response_text.strip()
