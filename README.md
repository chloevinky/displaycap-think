# DisplayCap Think

An AI-powered screenshot assistant for Windows that provides quick help for whatever you're working on.

## Features

- **Hotkey Triggered**: Press `Ctrl+Shift+Space` to activate
- **Smart Capture**: Takes 3 screenshots over 1 second to capture context
- **AI Analysis**: Uses Claude Haiku to understand your current task
- **Quick Assistance**: Provides short, actionable help displayed on your secondary monitor
- **Non-Intrusive**: Response window appears on secondary monitor, never captured in screenshots

## Requirements

- Windows 10/11
- Python 3.8+
- Anthropic API key

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

3. The app will:
   - Capture 3 screenshots of your primary monitor
   - Send them to Claude for analysis
   - Display helpful assistance on your secondary monitor

4. Press `Escape` or click X to dismiss the response window

5. Press `Ctrl+C` in the terminal to exit the app

## Configuration

### Change Hotkey

```bash
python run.py --hotkey "f12"
python run.py --hotkey "ctrl+alt+h"
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
    "max_response_tokens": 300
}
```

## How It Works

1. **Screenshot Capture**: Uses `mss` library to capture the primary monitor
2. **Rapid Sequence**: Takes multiple shots to capture changing content/context
3. **Image Processing**: Compresses and encodes images for efficient API transfer
4. **AI Analysis**: Claude Haiku analyzes the screenshots to understand your task
5. **Quick Response**: Provides brief, actionable assistance (2-4 sentences)
6. **Smart Display**: Shows response on secondary monitor to avoid capture loops

## Privacy

- Screenshots are sent directly to the Anthropic API
- No screenshots are stored locally
- No data is logged or retained

## Troubleshooting

**"No API key found"**
- Set the `ANTHROPIC_API_KEY` environment variable or use `--set-key`

**Hotkey not working**
- Try running as administrator (required for global hotkeys on some systems)
- Check if another application is using the same hotkey

**Window not appearing on secondary monitor**
- Ensure your secondary monitor is detected by Windows
- The app will fallback to the primary monitor if no secondary is found

## License

MIT License
