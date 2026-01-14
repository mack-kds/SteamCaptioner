# StreamCaptioner

Real-time live captioning system for streaming and broadcast production. Captures audio from multiple channels, transcribes speech using Deepgram AI, and outputs captions to vMix, web browsers, and text files.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

## Features

- **Multi-Channel Audio Capture** - Capture from multi-channel audio interfaces (e.g., Focusrite Scarlett)
- **Real-Time Transcription** - Powered by Deepgram's speech-to-text API with low latency
- **Multiple Output Feeds** - Route different audio channels to separate caption feeds
- **vMix Integration** - Send captions directly to vMix title inputs via HTTP API
- **Web Display** - Accessible web interface for viewers with customizable settings
- **File Output** - Save captions to text files for archival or other uses
- **Accessibility First** - High contrast themes, adjustable font sizes, keyboard navigation

## Screenshots

*Web caption display with dark theme and accessibility controls*

## Requirements

- Python 3.10 or higher
- [Deepgram API key](https://deepgram.com/) (free tier available)
- Multi-channel audio interface (optional, for multiple feeds)
- vMix (optional, for broadcast integration)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/mack-kds/SteamCaptioner.git
   cd StreamCaptioner
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv

   # Windows
   .\venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   Create a `.env` file in the project root:
   ```env
   DEEPGRAM_API_KEY=your_deepgram_api_key_here
   ```

5. **Configure the application**

   Copy the example config and customize:
   ```bash
   cp config.example.json config.json
   ```

## Configuration

Edit `config.json` to match your setup:

```json
{
    "audio": {
        "device_name": "Focusrite",
        "sample_rate": 16000,
        "channels": 2,
        "chunk_size": 4096
    },
    "feeds": [
        {
            "id": "announcements",
            "name": "Announcements",
            "channel": 0,
            "vmix_input": "Announcements_Caption",
            "enabled": true
        },
        {
            "id": "referee",
            "name": "Referee",
            "channel": 1,
            "vmix_input": "Referee_Caption",
            "enabled": true
        }
    ],
    "vmix": {
        "host": "127.0.0.1",
        "port": 8099,
        "enabled": true,
        "file_output_enabled": true,
        "file_output_dir": "output/captions"
    },
    "web": {
        "host": "0.0.0.0",
        "port": 8080
    },
    "caption_history_minutes": 10
}
```

### Configuration Options

| Option | Description |
|--------|-------------|
| `audio.device_name` | Partial match for audio device name |
| `audio.channels` | Number of audio channels to capture |
| `feeds[].channel` | Which audio channel (0-indexed) to use for this feed |
| `feeds[].vmix_input` | vMix title input name to update |
| `vmix.port` | vMix Web Controller port (default: 8099) |
| `web.host` | Web server bind address (`0.0.0.0` for all interfaces) |
| `web.port` | Web server port |

## Usage

### Starting the Application

```bash
# Windows
start.bat

# Or directly with Python
python -m src.main
```

### Using the GUI

1. Select your audio input device from the dropdown
2. Click **Start Captioning** to begin
3. The web interface will be available at the displayed URL

### Web Interface

Open `http://localhost:8080` (or your configured address) in a browser to view captions.

**Features:**
- Switch between caption feeds
- Adjust font size with `+`/`-` keys or settings panel
- Toggle high contrast mode
- Show/hide timestamps
- Enable interim (partial) results for faster feedback

## Development

### Running Tests

```bash
pytest tests/
```

### Project Structure

```
StreamCaptioner/
├── src/
│   ├── audio/          # Audio capture and device management
│   ├── feeds/          # Caption feed management and history
│   ├── gui/            # Tkinter GUI application
│   ├── outputs/        # vMix and file output handlers
│   ├── transcription/  # Deepgram integration
│   ├── web/            # FastAPI server and web interface
│   ├── config.py       # Configuration management
│   └── main.py         # Application entry point
├── tests/              # Unit tests
├── config.example.json # Example configuration
├── requirements.txt    # Python dependencies
└── start.bat          # Windows startup script
```

## Troubleshooting

### No audio devices found
- Ensure your audio interface is connected and recognized by Windows
- Check that no other application has exclusive access to the device

### Deepgram connection issues
- Verify your API key is correct in the `.env` file
- Check your internet connection
- Ensure you have available credits on your Deepgram account

### vMix not receiving captions
- Confirm vMix Web Controller is enabled (port 8099 by default)
- Verify the title input name matches your config exactly
- Check that vMix is running before starting StreamCaptioner

### Web interface not loading
- Check the console for the correct URL (may use your local IP)
- Ensure port 8080 is not blocked by firewall
- Try accessing from `http://localhost:8080`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Deepgram](https://deepgram.com/) for their excellent speech-to-text API
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [vMix](https://www.vmix.com/) for broadcast production software
