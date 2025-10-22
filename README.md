🎤 Realtime Voice Live Translator (RVLT)

Real-time, two-way voice translation (UKR $\leftrightarrow$ ENG) for calls using Azure AI Speech Services [cite: .env, requirements.txt].
This setup uses two independent processes for simultaneous understanding (🟢 EN $\to$ UK) and answering (🟣 UK $\to$ EN).

1. 🛠️ Initial Setup

1. Azure & Python:

In the Azure Portal, create a Speech Service resource. Get the Key and Region.

Create a .env file and add your credentials [cite: .env]:

# .env
AZURE_SPEECH_KEY="YOUR_AZURE_KEY"
AZURE_SPEECH_REGION="uksouth" # Or your region


Create a virtual environment and install dependencies:

python -m venv .venv
# Activate (Windows PowerShell):
.venv\Scripts\activate
# Install:
pip install -r requirements.txt


[cite: requirements.txt]

2. Audio Drivers:

Install two virtual audio cables: VB-CABLE A and VB-CABLE B from VB-Audio Software.

2. 🎧 Audio Routing (Critical Step)

This 2-cable setup replaces Voicemeeter.

1. Configure Zoom / Teams / Meet:

Speaker (Output): CABLE Input (VB-Audio Virtual Cable) (This is Cable A)

Microphone (Input): CABLE-B Input (VB-Audio Cable B)

2. Configure Windows ("Listen" to Original Audio):

Go to Sound Control Panel $\to$ Recording tab.

Find CABLE Output (A), click Properties $\to$ Listen tab.

Check "Listen to this device".

Set "Playback through" to your physical headphones (e.g., Навушники (2- HD65) [cite: config.py]).

This routes Zoom's audio to both the AI (for translation) and your ears (for the original voice).

3. ⚙️ Configuration & Diagnostics

1. Check Config:

Verify your device names in app/config.py. The script uses partial names to find them [cite: config.py, utils.py].

# app/config.py (Check these names)
PROFILES = {
    "understand": {"input_device": "CABLE Output (VB-Audio Virtual ", "output_device": "Навушники (2- HD65)", ... },
    "answer":     {"input_device": "Головной телефон (2- HD65)",   "output_device": "CABLE-B Input (VB-Audio", ... }
}


2. Run Diagnostics (If needed):

List devices: python -m app.diag_audio --list (Shows exact names to use in config) [cite: diag_audio.py]

Full test: python -m app.diag_audio --full (Tests both headphone output and mic input) [cite: diag_audio.py]

4. 🚀 Launch

Ensure your audio settings (Step 2) are active.

Run the batch file:

.\run_translator.bat


[cite: run_translator.bat]

This opens two console windows [cite: run_translator.bat]:

"Translator (Understand EN->UK)": 🟢 Listens to Zoom, translates to your headphones [cite: config.py].

"Translator (Answer UK->EN)": 🟣 Listens to your mic, translates to Zoom [cite: config.py].