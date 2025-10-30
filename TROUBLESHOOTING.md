# 🔧 Troubleshooting Guide

## Installation Issues

### "pip install fails with SSL error"
```powershell
# Update pip first
python -m pip install --upgrade pip
# Try with trusted host
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

### "keyboard module requires admin rights"
- Run PowerShell as Administrator
- Or use alternative: modify `app/ptt.py` to use `pynput` instead

### "voicemeeterlib not found"
```powershell
pip install voicemeeterlib==2.5.0
# Or try alternative:
pip install voicemeeter-remote
```

## Configuration Issues

### "SPEECH_KEY must be set to a valid Azure Speech key"
**Solution:**
1. Verify `.env` file exists in project root
2. Check key format: should be 32 characters hex string
3. No quotes needed in `.env` file
4. Restart terminal after editing `.env`

### "Voicemeeter does not appear to be installed"
**Solution:**
1. Download from: https://vb-audio.com/Voicemeeter/banana.htm
2. Install and restart computer
3. Launch Voicemeeter Banana before running app
4. Check installation paths:
   - `C:\Program Files (x86)\VB\Voicemeeter`
   - `C:\Program Files\VB\Voicemeeter`

## Runtime Issues

### "Failed to connect to Voicemeeter after retries"
**Checklist:**
- [ ] Voicemeeter Banana is running (not just installed)
- [ ] No other apps are blocking Voicemeeter API
- [ ] Try restarting Voicemeeter
- [ ] Run app as Administrator
- [ ] Check Windows Firewall not blocking

**Debug:**
```powershell
python -m app.cli self-test
```

### "No speech recognized" / STT not working
**Possible causes:**
1. **Wrong Azure credentials**
   - Verify SPEECH_KEY and SPEECH_REGION in `.env`
   - Test in Azure Portal Speech Studio
   
2. **Audio not reaching STT**
   ```powershell
   # Enable audio dumps to debug
   python -m app.cli run-ptt --log-level DEBUG
   ```
   - Check `debug_dumps/` for WAV files
   - Verify audio levels in Voicemeeter
   
3. **Wrong language**
   - Ensure speaking in Ukrainian if `STT_LANG_PTT=uk-UA`
   - Check voice is clear and loud enough

4. **Network issues**
   - Verify internet connection
   - Check Azure service status
   - Try different Azure region

### "TTS not playing" / No audio output
**Checklist:**
- [ ] Verify TTS device is correct: `python -m app.cli list-devices`
- [ ] Check Voicemeeter strip 1 is routed to B1
- [ ] Verify strip 1 is unmuted during PTT
- [ ] Check meeting app has "VoiceMeeter Output" as mic

**Debug:**
```powershell
# Check if audio is synthesized
python -m app.cli run-ptt --log-level DEBUG
# Look for "TTS synthesized X bytes" in logs
```

### Echo / Feedback loop
**Root cause:** TTS output is being captured by mic input

**Solution:**
1. In Voicemeeter:
   - Strip 1 (TTS) should ONLY route to B1
   - **Do NOT** route strip 1 to A1 (headphones)
2. Check meeting app:
   - Input: "VoiceMeeter Output (B1)"
   - **NOT** "Stereo Mix" or "What You Hear"
3. Disable system audio loopback

### "Audio choppy/distorted"
**Solutions:**

1. **Reduce frame size:**
   ```yaml
   # config.yaml
   audio:
     frame_ms: 10  # Try 10 or 15 instead of 20
   ```

2. **Check CPU usage:**
   - Close unnecessary apps
   - Lower quality settings in meeting app

3. **Buffer adjustments:**
   - In Voicemeeter: Menu → System Settings
   - Try different buffer sizes (256, 512, 1024)

4. **Disable VAD:**
   ```yaml
   # config.yaml
   ptt:
     vad_enabled: false
   ```

### "PTT key not responding"
**Solutions:**

1. **Check key name:**
   ```powershell
   # Try different key
   python -m app.cli run-ptt --ptt-key F9
   ```
   Valid keys: F1-F12, ctrl+space, alt+t, etc.

2. **Permission issue:**
   - Run as Administrator
   - Check antivirus not blocking keyboard hooks

3. **Key already bound:**
   - Close other apps that use same hotkey
   - Try different key

### "ImportError: DLL load failed"
**Windows-specific:**
```powershell
# Install Visual C++ Redistributable
# Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe

# Or install Windows SDK
```

## Performance Issues

### "High latency (>2 seconds)"
**Optimizations:**

1. **Reduce frame size:**
   ```yaml
   audio:
     frame_ms: 10
   ```

2. **Choose closer Azure region:**
   - Check latency: `ping westeurope.api.cognitive.microsoft.com`
   - Try different regions in `.env`

3. **Disable audio dumps:**
   ```yaml
   logging:
     dump_audio: false
   ```

4. **Check network:**
   - Use wired connection instead of WiFi
   - Close bandwidth-heavy apps

### "Memory leak / Growing RAM usage"
**Investigation:**
```powershell
# Monitor with Process Explorer or Task Manager
# Look for growing Python.exe memory

# Check logs for errors
type logs\run.log | findstr ERROR
```

**Mitigation:**
- Restart app every few hours
- Report issue on GitHub with logs

## Testing Issues

### "pytest: command not found"
```powershell
# Ensure virtual environment is activated
.venv\Scripts\activate

# Install pytest
pip install pytest pytest-cov
```

### "Tests fail with 'Module not found'"
```powershell
# Run from project root
cd C:\Users\555\OneDrive\Документи\GitHub\RVLT

# Ensure app module is importable
python -c "import app; print(app.__version__)"
```

### "Voicemeeter tests fail on CI"
**Expected behavior:**
- Voicemeeter tests will skip on CI (no Voicemeeter installed)
- Local tests use mocks
- This is normal

## Advanced Debugging

### Enable full debug logging
```powershell
python -m app.cli run-ptt --log-level DEBUG
```

### Capture audio dumps
```yaml
# config.yaml
logging:
  dump_audio: true
  dump_path: "debug_dumps"
```
Then check `debug_dumps/*.wav` files

### Monitor Voicemeeter levels
1. Open Voicemeeter
2. Watch strip levels during PTT
3. Verify input on strip 0, output on strip 1

### Test Azure credentials separately
```python
# test_azure.py
import os
from azure.cognitiveservices.speech import SpeechConfig

config = SpeechConfig(
    subscription=os.getenv("SPEECH_KEY"),
    region=os.getenv("SPEECH_REGION")
)
print(f"Azure region: {config.region}")
```

## Getting Help

1. **Check logs:** `logs/run.log`
2. **Run self-test:** `python -m app.cli self-test`
3. **Enable debug:** `--log-level DEBUG`
4. **Search issues:** [GitHub Issues](https://github.com/kuksa-serhii/RVLT/issues)
5. **Ask for help:** Create new issue with:
   - Full error message
   - Steps to reproduce
   - System info (Windows version, Python version)
   - Relevant logs

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Configuration validation failed` | Missing/invalid config | Check `.env` file |
| `Not connected to Voicemeeter` | Voicemeeter not running | Start Voicemeeter first |
| `Device not found` | Wrong device name | Run `list-devices` |
| `Azure Speech SDK not available` | Missing dependency | `pip install azure-cognitiveservices-speech` |
| `keyboard library not available` | Missing/permission issue | Run as admin or `pip install keyboard` |
| `Failed to initialize Azure STT` | Wrong credentials | Check SPEECH_KEY/SPEECH_REGION |

---

**Still stuck?** Open an issue with debug logs!
