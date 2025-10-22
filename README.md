🎤 Realtime Voice Live Translator (RVLT)

This project implements real-time, two-way voice translation (Ukrainian $\leftrightarrow$ English) with minimal latency, using Azure AI Speech Services. The architecture uses two independent processes for simultaneous "understanding" (🟢 EN $\to$ UK) and "answering" (🟣 UK $\to$ EN), making it ideal for important calls (Teams, Zoom, Meet).

1. 🛠️ Prerequisites (Azure & Python)

1. Create an Azure Resource
Log in to the Azure Portal and create a Speech Service resource. Save the Key and Region [cite: .env].

2. Set up the Environment

# Create a virtual environment (recommended)
python -m venv .venv

# Activate it:
# Windows (PowerShell)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\activate
 
# Linux/macOS
source .venv/bin/activate


3. Install Dependencies

# Upgrade pip and install libraries
python -m pip install --upgrade pip
pip install -r requirements.txt


[cite: requirements.txt]

4. Configure Keys
Create a .env file in the project root and add your credentials [cite: .env]:

# .env
AZURE_SPEECH_KEY="YOUR_AZURE_KEY"
AZURE_SPEECH_REGION="uksouth" # Or your region [cite: .env]


2. 🎧 Audio Setup ("2-Cable" Architecture)

This is a critical step. We are not using Voicemeeter, but instead setting up a clean routing system using two virtual audio cables.

Software Requirements:

VB-CABLE A (standard, CABLE Input/CABLE Output)

VB-CABLE B (additional, CABLE-B Input/CABLE-B Output)

Download and install both from VB-Audio Software.

Routing Diagram

Audio Flow

Source

Destination

AI Process?

Zoom Audio (Out)

Zoom/Teams (Speaker)

CABLE Input (A)

🟢 Understand

Your Microphone

Your Phys. Microphone

(Directly to AI)

🟣 Answer

Translation (To You)

🟢 Understand

Your Headphones

-

Translation (To Them)

🟣 Answer

CABLE-B Input (B)

-

Audio to Zoom (In)

-

CABLE-B Input (B)

Zoom/Teams (Mic)

Step 1: Configure Zoom / Teams / Meet

Speaker (What the app outputs):
CABLE Input (VB-Audio Virtual Cable)

Microphone (What the app listens to):
CABLE-B Input (VB-Audio Cable B)

Step 2: Configure Windows ("Listen")

To ensure you hear both the original Zoom audio and the AI translation:

Open Sound Settings (Windows).

Go to Sound Control Panel.

Open the Recording tab.

Find CABLE Output (A), click Properties.

Go to the Listen tab.

Check the box "Listen to this device".

In the "Playback through" dropdown, select your physical headphones (e.g., Навушники (2- HD65) [cite: config.py]).

Now, all audio from Zoom (CABLE A) will go to both the AI (for translation) and your ears (original audio).

3. ⚙️ Configuration (app/config.py)

The script is already configured for two profiles: understand (🟢) and answer (🟣) [cite: config.py].

Your only task is to verify that the device names in app/config.py match the names in your system.

# app/config.py (example names from your system)
PROFILES = {
    "understand": {
        "input_device": "CABLE Output (VB-Audio Virtual ", # [cite: config.py]
        "output_device": "Навушники (2- HD65)",         # [cite: config.py]
        #...
    },
    "answer": {
        "input_device": "Головной телефон (2- HD65)",   # [cite: config.py]
        "output_device": "CABLE-B Input (VB-Audio",       # [cite: config.py]
        #...
    }
}


4. 🩺 Diagnostics

If something doesn't work, use the built-in diagnostics script diag_audio.py [cite: diag_audio.py].

1. List all your audio devices:
Run python -m app.diag_audio --list. This will show the exact names you need to copy into config.py.

2. Run a full check:
Run python -m app.diag_audio --full. This test will [cite: diag_audio.py]:

Play a test tone to your headphones (checks the output_device from the understand profile).

Listen to your microphone (checks the input_device from the answer profile).

5. 🚀 Launch

Ensure your audio settings (Step 2) are active.

Run run_translator.bat:

.\run_translator.bat


[cite: run_translator.bat]

This script will automatically open two separate console windows [cite: run_translator.bat]:

"Translator (Understand EN->UK)": Runs the 🟢 understand profile [cite: config.py]. It listens to Zoom and translates to your headphones.

"Translator (Answer UK->EN)": Runs the 🟣 answer profile [cite: config.py]. It listens to your microphone and translates to Zoom's virtual microphone.

Start your conversation. Both windows will show real-time translation logs.