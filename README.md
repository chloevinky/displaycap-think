# DisplayCap Think

An AI-powered screenshot assistant for Windows that provides quick help for whatever you're working on.

## Features

- **Hotkey Triggered**: Press `Ctrl+Shift+Space` to activate
- **Smart Capture**: Takes 3 screenshots over 1 second to capture context
- **Voice Input**: Automatically captures your spoken question for better context
- **AI Analysis**: Uses Claude Haiku to understand your current task
- **Quick Assistance**: Provides short, actionable help displayed on your secondary monitor
- **Non-Intrusive**: Response window appears on secondary monitor, never captured in screenshots

## Requirements

- Windows 10/11
- Python 3.8+
- Anthropic API key
- Microphone (for voice input - optional but recommended)

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

2. Press `Ctrl+Shift+Space` while working on any task

3. **Speak your question** (optional but recommended):
   - After pressing the hotkey, speak your question or describe what you need help with
   - The app listens for up to 3 seconds
   - Example: "How do I fix this error?" or "What does this function do?"

4. The app will:
   - Capture 3 screenshots of your primary monitor
   - Transcribe your spoken question (if any)
   - Send both to Claude for analysis
   - Display helpful assistance on your secondary monitor

5. Press `Escape` or click X to dismiss the response window

6. Press `Ctrl+C` in the terminal to exit the app

## Configuration

### Change Hotkey

```bash
python run.py --hotkey "f12"
python run.py --hotkey "ctrl+alt+h"
```

### Speech Options

```bash
# Disable speech capture
python run.py --no-speech

# Enable continuous background listening (captures what you said before hotkey)
python run.py --continuous-listen

# Set speech timeout (seconds to wait for speech)
python run.py --speech-timeout 5.0
```

### Config File Location

- Windows: `%APPDATA%\displaycap-think\config.json`
- Linux/Mac: `~/.config/displaycap-think/config.json`

### Available Settings

```json
{
    "hotkey": "ctrl+shift+space",
    "screenshot_count": 3,
    "screenshot_interval": 0.5,
    "image_quality": 85,
    "max_response_tokens": 300,
    "speech_enabled": true,
    "continuous_listening": false,
    "speech_timeout": 3.0,
    "speech_phrase_limit": 5.0
}
```

## How It Works

1. **Screenshot Capture**: Uses `mss` library to capture the primary monitor
2. **Rapid Sequence**: Takes multiple shots to capture changing content/context
3. **Voice Capture**: Simultaneously listens for your spoken question (using Google Speech Recognition)
4. **Image Processing**: Compresses and encodes images for efficient API transfer
5. **AI Analysis**: Claude Haiku analyzes both screenshots and your question
6. **Quick Response**: Provides brief, actionable assistance (2-4 sentences)
7. **Smart Display**: Shows response on secondary monitor to avoid capture loops

## Privacy

- Screenshots are sent directly to the Anthropic API
- Voice is transcribed using Google Speech Recognition (sent to Google servers)
- No screenshots or audio are stored locally
- No data is logged or retained by this application

## Troubleshooting

**"No API key found"**
- Set the `ANTHROPIC_API_KEY` environment variable or use `--set-key`

**Hotkey not working**
- Try running as administrator (required for global hotkeys on some systems)
- Check if another application is using the same hotkey

**Window not appearing on secondary monitor**
- Ensure your secondary monitor is detected by Windows
- The app will fallback to the primary monitor if no secondary is found

**Speech not working**
- Ensure your microphone is connected and working
- Check Windows privacy settings: Settings > Privacy > Microphone
- Run with `--no-speech` to disable voice input entirely

**"Speech service error"**
- This uses Google's free speech recognition API which requires internet
- Check your internet connection

## License

MIT License
