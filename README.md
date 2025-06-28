Pyhton 3.9 is preffered for this project


# Peshawar Mall AI Assistant 🛍️🤖

An intelligent voice-enabled shopping mall assistant that helps customers find products, store locations, and mall information using natural language processing and SQL database queries.

## Features ✨

- **🎤 Voice Interaction**: Advanced Voice Activity Detection (VAD) for hands-free communication
- **🗣️ Speech Recognition**: High-quality audio transcription using Faster Whisper
- **🧠 AI-Powered Responses**: Intelligent query processing with Llama 3.1 405B model
- **🗄️ Database Integration**: Real-time MySQL database queries for accurate information
- **🔊 Text-to-Speech**: Natural voice responses using Microsoft Edge TTS
- **🌐 Web Interface**: Flask-based API with CORS support
- **🔒 Security**: Request validation and session management

## Architecture 🏗️

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Frontend  │───▶│   Flask Server   │───▶│  MySQL Database │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ├── Voice Activity Detection
                              ├── Speech Recognition (Whisper)
                              ├── AI Processing (Llama API)
                              └── Text-to-Speech (Edge TTS)
```

## Prerequisites 📋

- Python 3.8+
- MySQL Server
- Microphone access
- Internet connection (for AI API)

## Installation 🚀

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/peshawar-mall-assistant.git
   cd peshawar-mall-assistant
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   # RapidAPI Credentials for Llama 3.1
   RAPIDAPI_KEY=your_rapidapi_key_here
   RAPIDAPI_HOST=meta-llama-3-1-405b.p.rapidapi.com
   
   # Database Configuration
   DB_HOST=localhost
   DB_USER=your_db_username
   DB_PASSWORD=your_db_password
   DB_NAME=shoppingmall
   ```

4. **Set up the database**
   - Create a MySQL database named `shoppingmall`
   - Import your mall data schema (products, stores, mall_information, etc.)

5. **Install system dependencies**
   ```bash
   # For audio processing (Ubuntu/Debian)
   sudo apt-get install portaudio19-dev python3-pyaudio
   
   # For macOS
   brew install portaudio
   ```

## Usage 💡

### Web Application
1. **Start the Flask server**
   ```bash
   python app.py
   ```

2. **Open your browser**
   Navigate to `http://127.0.0.1:5000`

3. **Start conversation**
   - Click "Start Conversation" to initialize the voice recorder
   - Speak your query (e.g., "What's the price of Samsung TV?")
   - Listen to the AI response

### Command Line Version
```bash
python main.py
```

## API Endpoints 🔌

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/api/initialize-recorder` | POST | Initialize VAD recorder |
| `/api/start-vad-recording` | POST | Start voice recording |
| `/api/stop-recording` | POST | Stop active recording |
| `/api/end-session` | POST | End conversation session |
| `/api/text-to-speech` | POST | Generate audio from text |
| `/api/chat` | POST | Text-based chat interface |

## Configuration ⚙️

### Voice Activity Detection
```python
# In app.py - ImprovedVADRecorder class
self.speech_frames_threshold = 8    # Sensitivity for speech detection
self.silence_frames_threshold = 35  # Silence duration before stopping
self.min_speech_duration = 0.5      # Minimum speech length (seconds)
```

### Database Schema
The system expects these main tables:
- `product` - Product information (name, price, etc.)
- `store` - Store details (name, location, contact)
- `mall_information` - General mall info
- `category` - Product categories

## Security Features 🔐

- **Request Validation**: Custom header validation (`X-From-Client`)
- **Session Management**: Active session tracking
- **CORS Protection**: Configured for specific origins
- **SQL Injection Prevention**: Parameterized queries

## Example Queries 💬

- "What's the price of iPhone 14?"
- "Where is the Nike store located?"
- "Show me all electronics stores"
- "What are the mall opening hours?"
- "Find stores on the second floor"

## Development 🛠️

### Project Structure
```
peshawar-mall-assistant/
├── app.py                 # Flask web server
├── main.py               # Command-line interface
├── config.py             # Configuration management
├── database_utils.py     # Database operations
├── llama_api.py          # AI model integration
├── transcription_utils.py # Speech recognition
├── text_to_speech.py     # TTS functionality
├── audio_utils.py        # Audio processing utilities
├── recognizer.py         # Alternative speech recognition
├── templates/            # HTML templates
└── static/              # CSS, JS, assets
```

### Adding New Features
1. **Database Queries**: Modify `database_utils.py`
2. **AI Responses**: Update prompts in `llama_api.py`
3. **Voice Processing**: Enhance `ImprovedVADRecorder` class
4. **Web Interface**: Edit templates and add new endpoints

## Troubleshooting 🔧

### Common Issues

1. **Audio not working**
   ```bash
   # Test microphone
   python -c "import pyaudio; print('PyAudio works!')"
   ```

2. **Database connection errors**
   - Verify MySQL server is running
   - Check credentials in `.env` file
   - Ensure database exists

3. **API errors**
   - Validate RapidAPI key and subscription
   - Check internet connection
   - Monitor API usage limits

4. **Voice Activity Detection issues**
   - Adjust `speech_frames_threshold` and `silence_frames_threshold`
   - Test in quiet environment
   - Check microphone permissions

## Performance Optimization 🚀

- **Audio Processing**: Uses 16kHz sampling rate for optimal balance
- **Database**: Connection pooling and query optimization
- **AI Responses**: Temperature set to 0.1 for consistent results
- **Memory Management**: Automatic cleanup of temporary audio files

## Contributing 🤝

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments 🙏

- **Faster Whisper** for accurate speech recognition
- **Microsoft Edge TTS** for natural voice synthesis
- **Meta Llama 3.1** for intelligent query processing
- **WebRTC VAD** for voice activity detection
- **Flask** for web framework

## Support 💬

For support and questions:
- Create an issue on GitHub
- Check the [troubleshooting section](#troubleshooting-)
- Review the API documentation

---

**Made with ❤️ for Peshawar Mall customers**
