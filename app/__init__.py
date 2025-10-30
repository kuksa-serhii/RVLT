"""
RT Bilingual PTT Translator Package.

A real-time Push-to-Talk translator supporting UA↔EN speech translation
using Azure Speech SDK and Voicemeeter for audio routing.
"""

__version__ = "0.1.0"
__all__ = [
    "Config",
    "AudioDevices", 
    "AzureSTT",
    "AzureTTS",
    "VoicemeeterController",
    "PTTHandler",
    "Pipeline",
]
