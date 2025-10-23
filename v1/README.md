# 🎤 Realtime Voice Live Translator (RVLT)

Real-time, two-way voice translation (UKR $\leftrightarrow$ ENG) for calls using Azure AI Speech Services [cite: .env, requirements.txt].
This setup uses two independent processes for simultaneous understanding (🟢 EN $\to$ UK) and answering (🟣 UK $\to$ EN).



## 1. Azure & Python:

In the Azure Portal, create a Speech Service resource. Get the Key and Region.

Create a .env file and add your credentials [cite: .env]:
```ini
.env
AZURE_SPEECH_KEY="YOUR_AZURE_KEY"
AZURE_SPEECH_REGION="uksouth" # Or your region
```

Create a virtual environment and install dependencies:
```
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Audio Drivers:
```
Install two virtual audio cables: VB-CABLE A and VB-CABLE B from [VB-Audio Software](https://vb-audio.com/Cable/)


1. Configure Zoom / Teams / Meet...:

Speaker (Output): CABLE Input (VB-Audio Virtual Cable) (This is Cable A)

Microphone (Input): CABLE-B Input (VB-Audio Cable B)

2. Configure Windows ("Listen" to Original Audio):

Go to Sound Control Panel $\to$ Recording tab.

Find CABLE Output (A), click Properties $\to$ Listen tab.

Check "Listen to this device".

Set "Playback through" to your physical headphones (e.g., Навушники (2- HD65) ).

This routes Zoom's audio to both the AI (for translation) and your ears (for the original voice).
```
## 3. ⚙️ Configuration & Diagnostics

### 1. Check Config:

Verify your device names in app/config.py. The script uses partial names to find them.
```
app/config.py (Check these names)

PROFILES = {
    "understand": {"input_device": "CABLE Output (VB-Audio Virtual ", "output_device": "Навушники (2- HD65)", ... },
    "answer":     {"input_device": "Головной телефон (2- HD65)",   "output_device": "CABLE-B Input (VB-Audio", ... }
}
```

### 2. Run Diagnostics (If needed):
```
python -m app.diag_audio --list (Shows exact names to use in config) 
python -m app.diag_audio --full (It checks both the headphone output and microphone input from your profiles.)
python -m app.diag_audio --test-headphones  (checks understand profile output)
python -m app.diag_audio --test-mic  (checks answer profile input)
python -m app.diag_audio --test-zoom-in  (checks understand profile input).

```
## 4. 🚀 Launch

Ensure your audio settings (Step 2) are active.

Run the batch file:

```
.\run_translator.bat
```


This opens two console windows:

> "Translator (Understand EN->UK)": 🟢 Listens to Zoom, translates to your headphones [.

> "Translator (Answer UK->EN)": 🟣 Listens to your mic, translates to Zoom .