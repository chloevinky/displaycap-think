# LoL Assistant

An AI-powered League of Legends coaching assistant that provides real-time advice during your games.

## Features

- **Live Game Tracking**: Automatically captures your game window every 2 seconds
- **Smart Context**: Tracks enemy champions, items, and game state over time
- **Contextual Advice**: Press a hotkey to get AI-powered advice tailored to your current situation
- **Item Recommendations**: Get optimal item suggestions based on enemy team composition
- **Voice Input**: Speak your question for more specific advice
- **Game Data Integration**: Uses Riot's Data Dragon API for current patch information
- **LoL-Themed UI**: Dark theme matching the League of Legends client aesthetic

## How It Works

1. **Continuous Monitoring**: The app captures your game window every 2 seconds in the background
2. **State Tracking**: Periodically analyzes screenshots to track:
   - Your champion
   - Enemy champions visible
   - Game phase (early/mid/late)
   - Whether you're in the shop
3. **Instant Advice**: When you press the hotkey, the app uses the accumulated context to provide relevant advice
4. **Smart Recommendations**: If you're in the shop, it focuses on item recommendations based on enemy team

## Requirements

- Windows 10/11
- Python 3.8+
- Anthropic API key
- Microphone (optional, for voice input)

## Installation

1. Clone or download this repository

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set your Anthropic API key (choose one method):

   **Option A**: Environment variable (recommended)
   ```bash
   set ANTHROPIC_API_KEY=your-api-key-here
   ```

   **Option B**: Save to config file
   ```bash
   python run.py --set-key your-api-key-here
   ```

## Usage

1. Start the application:
   ```bash
   python run.py
   ```

2. Launch League of Legends and start a game

3. Press `Ctrl+Shift+Space` when you need advice:
   - In lane: Get tips on trading, wave management, or roaming
   - In shop: Get item recommendations based on enemy team
   - In teamfight: Get positioning and ability usage tips

4. **Speak your question** (optional):
   - After pressing the hotkey, speak your specific question
   - Example: "What should I buy against their AP?"
   - Example: "Should I fight or farm?"

5. Press `Escape` to dismiss the advice window

6. Press `Ctrl+C` in the terminal to exit

## Command Line Options

### Basic Configuration
```bash
# Set API key
python run.py --set-key YOUR_API_KEY

# Change hotkey
python run.py --hotkey "f12"
python run.py --hotkey "ctrl+alt+a"
```

### Auto-Capture Settings
```bash
# Disable automatic screenshot capture
python run.py --no-auto-capture

# Change capture interval (default: 2.0 seconds)
python run.py --capture-interval 3.0

# Disable the status overlay
python run.py --no-overlay
```

### Speech Options
```bash
# Disable speech capture
python run.py --no-speech

# Enable continuous background listening
python run.py --continuous-listen

# Set speech timeout
python run.py --speech-timeout 5.0
```

## Configuration

### Config File Location

- Windows: `%APPDATA%\lol-assistant\config.json`
- Linux/Mac: `~/.config/lol-assistant/config.json`

### Available Settings

```json
{
    "hotkey": "ctrl+shift+space",
    "screenshot_count": 3,
    "screenshot_interval": 0.5,
    "image_quality": 85,
    "auto_capture_enabled": true,
    "auto_capture_interval": 2.0,
    "max_response_tokens": 400,
    "speech_enabled": true,
    "continuous_listening": false,
    "speech_timeout": 3.0,
    "speech_phrase_limit": 5.0,
    "auto_detect_lol_window": true,
    "background_analysis_enabled": true,
    "background_analysis_interval": 10,
    "game_state_history_size": 60,
    "show_game_status": true
}
```

### Settings Explained

| Setting | Description |
|---------|-------------|
| `auto_capture_enabled` | Enable/disable automatic background capture |
| `auto_capture_interval` | Seconds between auto-captures (default: 2.0) |
| `auto_detect_lol_window` | Try to capture LoL window specifically |
| `background_analysis_enabled` | Analyze screenshots to extract game state |
| `background_analysis_interval` | Run analysis every N captures |
| `game_state_history_size` | Number of screenshots to keep in memory |
| `show_game_status` | Show the tracking overlay in corner |

## Advice Types

The assistant provides different types of advice based on context:

### In-Game Advice
- Lane trading strategies
- Wave management tips
- Roaming suggestions
- Objective timing
- Teamfight positioning

### Item Recommendations
When you're in the shop, the assistant focuses on item builds:
- Counter-build against enemy team composition
- Synergy with your champion's kit
- Power spike items for current game phase
- Gold-efficient purchases

### Strategic Tips
- Map awareness reminders
- Objective priorities
- Win condition guidance

## Architecture

```
src/
├── app.py           # Main application & orchestration
├── api_client.py    # Anthropic API integration
├── config.py        # Configuration management
├── display.py       # UI windows (LoL-themed)
├── game_state.py    # Game state tracking
├── hotkey.py        # Global hotkey handling
├── lol_api.py       # Data Dragon & LCU API clients
├── screenshot.py    # Screen capture & auto-capture
└── speech.py        # Voice input handling
```

## Data Sources

### Data Dragon API
- Champion information (names, roles, stats)
- Item data (names, costs, stats)
- Current game patch version

### LCU API (when available)
- Live game detection
- Current game mode
- Champion select information

## Privacy

- Screenshots are sent to Anthropic's API for analysis
- Voice is transcribed using Google Speech Recognition
- Game data is cached locally in the config directory
- No screenshots or audio are permanently stored
- No data is sent to third parties beyond Anthropic (AI) and Google (speech)

## Troubleshooting

### "No API key found"
Set the `ANTHROPIC_API_KEY` environment variable or use `--set-key`

### LoL window not detected
- Make sure League of Legends is running
- The app will capture the primary monitor as fallback
- Check that the game is not minimized

### Hotkey not working
- Try running as administrator (required for global hotkeys)
- Check if another application is using the same hotkey
- Try a different hotkey with `--hotkey`

### Advice window not appearing
- Check if it's on your secondary monitor
- Press the hotkey again to show it
- Disable secondary monitor positioning by modifying display.py

### Speech not working
- Ensure your microphone is connected and working
- Check Windows privacy settings: Settings > Privacy > Microphone
- Run with `--no-speech` to disable voice input

### High CPU usage
- Increase `auto_capture_interval` to capture less frequently
- Disable background analysis with `background_analysis_enabled: false`
- Use `--no-auto-capture` to disable auto-capture entirely

## License

MIT License
