# RT Bilingual PTT Translator

A Windows-first real-time Push-to-Talk (PTT) translator for bilingual communication. Translates **Ukrainian→English** speech in real-time using Azure Speech SDK and Voicemeeter for audio routing.

## ✨ Features

- **Hybrid PTT Translation**: Press a hotkey to speak in Ukrainian, get instant English translation via TTS
- **Low-latency Pipeline**: Optimized audio path with explicit resampling (48 kHz ↔ 16 kHz)
- **Voicemeeter Integration**: Automatic mic/TTS strip switching during PTT
- **Azure Speech SDK**: High-quality STT, translation, and TTS
- **Timing Diagnostics**: Built-in P50/P95 latency tracking
- **Audio Debugging**: Optional WAV dumps for troubleshooting

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PTT Pressed                              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Physical Mic   │───→│ Voicemeeter  │───→│  Capture @ 48k  │
│  (strip 0)      │    │  (muted)     │    │  mono int16     │
└─────────────────┘    └──────────────┘    └─────────────────┘
                                                    ↓
                                            ┌──────────────┐
                                            │ Downsample   │
                                            │  48k → 16k   │
                                            └──────────────┘
                                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│             Azure Speech STT + Translation (UK→EN)              │
└─────────────────────────────────────────────────────────────────┘
                                                    ↓
                                            ┌──────────────┐
                                            │  Azure TTS   │
                                            │  @ 48k mono  │
                                            └──────────────┘
                                                    ↓
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Meeting App    │←───│ Voicemeeter  │←───│  TTS Output     │
│  (via B1 bus)   │    │  Virtual In  │    │  (strip 1)      │
└─────────────────┘    │  (unmuted)   │    └─────────────────┘
                       └──────────────┘
```

**Latency Budget** (target):
- Capture → STT: 20-40 ms
- STT → Translation: 200-500 ms (Azure RTF)
- Translation → TTS: 300-800 ms (Azure synthesis)
- **Total**: ~500-1300 ms end-to-end

## 📋 Prerequisites

### Required Software

1. **Windows 10/11** (primary target OS)
2. **Python 3.10+** (3.11 recommended)
3. **Voicemeeter Banana** ([Download](https://vb-audio.com/Voicemeeter/banana.htm))
   - Install and configure:
     - **Strip 0**: Physical microphone
     - **Strip 1**: Virtual input for Azure TTS
     - **Bus B1**: Output to meeting app (Teams/Zoom/Discord)
     - **Bus A1**: Headphones for monitoring
4. **VB-Audio Virtual Cable** (optional, included with Voicemeeter)

### Azure Resources

- **Azure Speech Service** resource
  - Get your `SPEECH_KEY` and `SPEECH_REGION` from [Azure Portal](https://portal.azure.com)
  - Free tier: 5 hours of STT/TTS per month

## 🚀 Quick Start

### 1. Clone and Setup

```powershell
# Clone repository
git clone https://github.com/kuksa-serhii/RVLT.git
cd RVLT

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

```powershell
# Copy example env file
copy .env.example .env

# Edit .env with your Azure credentials
notepad .env
```

Update `.env`:
```ini
SPEECH_KEY=your_azure_speech_key_here
SPEECH_REGION=westeurope  # or your region
```

### 3. Test Setup

```powershell
# List available audio devices
python -m app.cli list-devices

# Run self-test
python -m app.cli self-test
```

### 4. Run PTT Translator

```powershell
# Start with defaults (F8 key for PTT)
python -m app.cli run-ptt

# Custom PTT key and devices
python -m app.cli run-ptt --ptt-key F9 \
    --mic-device "Voicemeeter Output" \
    --tts-device "Voicemeeter Aux Input"
```

## 🎮 Usage

1. **Start the application**: `python -m app.cli run-ptt`
2. **Press and hold PTT key** (default `F8`): Speak in Ukrainian
3. **Release key**: Translation is synthesized and played to meeting
4. **Monitor logs**: Check `logs/run.log` for timing stats

### CLI Commands

```powershell
# List all audio devices
python -m app.cli list-devices

# Run self-test
python -m app.cli self-test

# Run PTT translator with options
python -m app.cli run-ptt [OPTIONS]

Options:
  --ptt-key TEXT         PTT hotkey (default: F8)
  --mic-device TEXT      Microphone device name
  --tts-device TEXT      TTS output device name
  --lang-in TEXT         Input language (default: uk-UA)
  --lang-out TEXT        Output language (default: en-GB)
  --log-level LEVEL      Logging level (DEBUG|INFO|WARNING|ERROR)
  --no-translate         Debug: STT only, no TTS
```

## ⚙️ Configuration

### Environment Variables (`.env`)

```ini
# Required
SPEECH_KEY=your_key
SPEECH_REGION=westeurope

# Optional
STT_LANG_PTT=uk-UA
TTS_VOICE_EN=en-GB-RyanNeural
PTT_KEY=F8
```

### Advanced Config (`config.yaml`)

Create optional `config.yaml` for advanced settings:

```yaml
audio:
  device_sr_in: 48000
  frame_ms: 20

voicemeeter:
  strip_mic: 0
  strip_tts: 1
  bus_meeting: "B1"

ptt:
  ptt_key: "F8"
  debounce_ms: 50
  vad_enabled: true

logging:
  log_level: "INFO"
  dump_audio: false
```

## 🔧 Voicemeeter Setup

1. **Open Voicemeeter Banana**
2. **Hardware Input 1** (Strip 0):
   - Select your physical microphone
   - Route to A1 (headphones) and B1 (meeting)
3. **Virtual Input 1** (Strip 1):
   - This receives Azure TTS output
   - Route to B1 (meeting) only
   - Keep MUTED by default
4. **Hardware Out A1**: Your headphones
5. **Virtual Output B1**: Select as microphone in Teams/Zoom

**Important**: The app will automatically mute/unmute strips during PTT.

## 🐛 Troubleshooting

### Audio Issues

**Problem**: No audio captured
- Check microphone is working in Windows Sound settings
- Verify Voicemeeter strip routing with `self-test`
- Enable debug: `--log-level DEBUG`

**Problem**: Echo/feedback
- Ensure TTS output (strip 1) is NOT routed to your headphones (A1)
- Check that meeting app is NOT recording system audio
- Verify separate input/output devices

**Problem**: Choppy/distorted audio
- Reduce `frame_ms` in config (try 10 ms)
- Check CPU usage during translation
- Disable VAD: set `vad_enabled: false` in config

### Azure Issues

**Problem**: STT not recognizing speech
- Verify `SPEECH_KEY` and `SPEECH_REGION` are correct
- Check Azure subscription is active (free tier limits)
- Test with `--no-translate` flag to isolate STT

**Problem**: TTS timeout
- Check internet connectivity
- Try different Azure region (lower latency)
- Monitor Azure service status

### Voicemeeter Issues

**Problem**: Cannot connect to Voicemeeter
- Ensure Voicemeeter is running BEFORE starting app
- Restart Voicemeeter and try again
- Check Windows permissions (run as admin if needed)

## 📊 Performance Tips

1. **Reduce Latency**:
   - Use shorter `frame_ms` (10-15 ms)
   - Choose Azure region closest to you
   - Disable audio dump: `dump_audio: false`

2. **Improve Accuracy**:
   - Speak clearly and at moderate pace
   - Use external mic (better quality than laptop)
   - Adjust VAD aggressiveness (0-3)

3. **Avoid Echo Loops**:
   - NEVER route TTS output back to mic input
   - Use separate devices for capture/playback
   - Monitor strip levels in Voicemeeter

## 🧪 Development

### Running Tests

```powershell
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Specific test file
pytest tests/test_resample.py -v
```

### Project Structure

```
rt-bilingual-ptt-translator/
├── app/
│   ├── __init__.py
│   ├── cli.py              # CLI interface
│   ├── config.py           # Configuration management
│   ├── audio_devices.py    # Audio I/O with sounddevice
│   ├── resample.py         # Sample rate conversion
│   ├── ptt.py              # PTT keyboard handler
│   ├── voicemeeter_ctrl.py # Voicemeeter API wrapper
│   ├── azure_speech.py     # Azure STT/TTS
│   ├── pipeline.py         # Main translation pipeline
│   └── utils.py            # Logging and diagnostics
├── tests/
│   ├── test_resample.py
│   ├── test_config.py
│   └── test_voicemeeter_ctrl.py
├── .env.example
├── .gitignore
├── requirements.txt
├── LICENSE
└── README.md
```

## 🔐 Safety & Ethics

- **Recording Consent**: Always inform meeting participants if translation is active
- **Data Privacy**: Audio is processed by Azure Speech Service (see [Azure Privacy](https://privacy.microsoft.com/))
- **Meeting Policies**: Check your organization's policies on translation tools

## 🛣️ Roadmap / Future Enhancements

- [ ] **Streaming TTS**: Reduce time-to-first-phoneme (chunked synthesis)
- [ ] **BLE/HID PTT**: Support external buttons (foot pedal, BLE remote)
- [ ] **LLM Polish**: Optional text refinement before TTS (grammar, formality)
- [ ] **Bidirectional Mode**: EN→UA for understanding (private monitor)
- [ ] **Web UI**: Browser-based control panel
- [ ] **Multi-language**: Support additional language pairs

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Azure Speech SDK](https://learn.microsoft.com/azure/ai-services/speech-service/)
- [Voicemeeter by VB-Audio](https://vb-audio.com/Voicemeeter/)
- [pysoxr](https://github.com/dofuuz/python-soxr) for high-quality resampling
- Community contributors

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/kuksa-serhii/RVLT/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kuksa-serhii/RVLT/discussions)

---

**Made with ❤️ for bilingual communication**
