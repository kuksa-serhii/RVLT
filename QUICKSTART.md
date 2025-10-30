# 🚀 Quick Start Guide

## Installation (5 minutes)

### 1. Install Prerequisites

**Voicemeeter Banana** (if not already installed):
1. Download from https://vb-audio.com/Voicemeeter/banana.htm
2. Run installer and restart if prompted
3. Launch Voicemeeter Banana

**Python 3.10+**:
1. Download from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"

### 2. Get Azure Speech Credentials

1. Go to [Azure Portal](https://portal.azure.com)
2. Create a Speech Service resource (free tier available)
3. Copy your **Key** and **Region** from the "Keys and Endpoint" section

### 3. Setup Project

```powershell
# Clone repository
git clone https://github.com/kuksa-serhii/RVLT.git
cd RVLT

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
notepad .env
```

In `.env`, update:
```ini
SPEECH_KEY=your_actual_key_here
SPEECH_REGION=your_region  # e.g., westeurope, eastus
```

### 4. Configure Voicemeeter

**Important setup:**

1. Open Voicemeeter Banana
2. **Hardware Input 1 (Strip 0)**: Select your microphone
   - Check: A1 ✓, B1 ✓
3. **Virtual Input 1 (Strip 1)**: Leave as "VoiceMeeter AUX" 
   - Check: B1 ✓ ONLY
   - Keep MUTED
4. **A1 Output**: Select your headphones
5. **B1 Output**: Will be used as "microphone" in meeting apps

### 5. First Run

```powershell
# Test audio devices
python -m app.cli list-devices

# Run self-test
python -m app.cli self-test

# Start translator (F8 to speak)
python -m app.cli run-ptt
```

## Usage

1. **In your meeting app** (Teams/Zoom/Discord):
   - Select **"VoiceMeeter Output (B1)"** as microphone

2. **Press F8** and speak in **Ukrainian**
3. **Release F8** - English translation plays to meeting

## Common Issues

### "Voicemeeter connection failed"
→ Ensure Voicemeeter Banana is running, then start the app

### "SPEECH_KEY must be set"
→ Check `.env` file has your actual Azure key

### "No input devices found"
→ Check Windows Sound settings, ensure mic is enabled

### Echo/feedback
→ Ensure Virtual Input 1 (strip 1) is NOT routed to A1 (headphones)

## Next Steps

- Read full [README.md](README.md) for advanced configuration
- Check logs in `logs/run.log` for troubleshooting
- Join discussions for help

---

**Need Help?** Open an issue on GitHub!
