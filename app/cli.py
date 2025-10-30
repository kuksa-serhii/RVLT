"""
Command-line interface for RT Bilingual PTT Translator.

Provides commands for running PTT mode, listing devices, and self-test.
"""

import argparse
import sys
import time
import logging
from pathlib import Path

from .config import load_config, validate_environment, Config
from .audio_devices import list_audio_devices, find_device_by_name
from .voicemeeter_ctrl import VoicemeeterController
from .pipeline import PTTPipeline
from .utils import setup_logger, format_device_list

logger = logging.getLogger(__name__)


def cmd_list_devices(args):
    """List all available audio devices."""
    print("\n🎤 Enumerating Audio Devices...")
    
    devices = list_audio_devices()
    print(format_device_list(devices))
    
    return 0


def cmd_self_test(args):
    """Run self-test to verify components."""
    print("\n🔧 Running Self-Test...\n")
    
    errors = []
    
    # Check environment
    env_errors = validate_environment()
    if env_errors:
        errors.extend(env_errors)
        for err in env_errors:
            print(f"❌ {err}")
    else:
        print("✅ Environment variables OK")
    
    # Check Voicemeeter
    print("\n📡 Testing Voicemeeter connection...")
    vm = VoicemeeterController()
    if vm.connect():
        print("✅ Voicemeeter connected")
        vm.disconnect()
    else:
        print("❌ Voicemeeter connection failed")
        errors.append("Voicemeeter not available")
    
    # Check audio devices
    print("\n🎵 Checking audio devices...")
    devices = list_audio_devices()
    input_devices = [d for d in devices if d['max_input_channels'] > 0]
    output_devices = [d for d in devices if d['max_output_channels'] > 0]
    
    if input_devices:
        print(f"✅ Found {len(input_devices)} input device(s)")
    else:
        print("❌ No input devices found")
        errors.append("No input devices")
    
    if output_devices:
        print(f"✅ Found {len(output_devices)} output device(s)")
    else:
        print("❌ No output devices found")
        errors.append("No output devices")
    
    # Summary
    print("\n" + "="*60)
    if errors:
        print(f"❌ Self-test FAILED with {len(errors)} error(s)")
        return 1
    else:
        print("✅ Self-test PASSED - all systems operational")
        return 0


def cmd_run_ptt(args):
    """Run PTT translation mode."""
    print("\n🚀 Starting RT Bilingual PTT Translator...\n")
    
    # Load config
    try:
        config = load_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\n❌ Configuration error: {e}")
        print("\nPlease check your .env file and ensure SPEECH_KEY and SPEECH_REGION are set.")
        return 1
    
    # Apply CLI overrides
    if args.ptt_key:
        config.ptt.ptt_key = args.ptt_key
    if args.mic_device:
        config.audio.mic_device = args.mic_device
    if args.tts_device:
        config.audio.tts_device = args.tts_device
    if args.lang_in:
        config.speech.stt_lang_ptt = args.lang_in
    if args.lang_out:
        # This would affect TTS voice selection
        pass  # TODO: map language to voice
    if args.log_level:
        config.logging.log_level = args.log_level
    
    # Setup logging
    setup_logger(
        level=config.logging.log_level,
        log_file=config.logging.log_file
    )
    
    # Validate devices
    if config.audio.mic_device:
        mic_idx = find_device_by_name(config.audio.mic_device, input_device=True)
        if mic_idx is None:
            print(f"❌ Microphone device not found: {config.audio.mic_device}")
            print("\nRun 'python -m app.cli list-devices' to see available devices")
            return 1
    
    if config.audio.tts_device:
        tts_idx = find_device_by_name(config.audio.tts_device, input_device=False)
        if tts_idx is None:
            print(f"❌ TTS output device not found: {config.audio.tts_device}")
            print("\nRun 'python -m app.cli list-devices' to see available devices")
            return 1
    
    # Display configuration
    print(f"Configuration:")
    print(f"  PTT Key: {config.ptt.ptt_key}")
    print(f"  STT Language: {config.speech.stt_lang_ptt}")
    print(f"  TTS Voice: {config.speech.tts_voice_en}")
    print(f"  Mic Device: {config.audio.mic_device or 'Default'}")
    print(f"  TTS Device: {config.audio.tts_device or 'Default'}")
    print(f"  Voicemeeter: Mic strip={config.voicemeeter.strip_mic}, TTS strip={config.voicemeeter.strip_tts}")
    print()
    
    # Create and run pipeline
    try:
        with PTTPipeline(config) as pipeline:
            print(f"✅ Pipeline ready")
            print(f"\n🎤 Press {config.ptt.ptt_key} to speak (Ukrainian)")
            print(f"   Translation will be synthesized in English\n")
            print("Press Ctrl+C to exit\n")
            
            # Run until interrupted
            while True:
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        return 0
    
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RT Bilingual PTT Translator - Real-time UA↔EN speech translation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available audio devices
  python -m app.cli list-devices
  
  # Run self-test
  python -m app.cli self-test
  
  # Run PTT translator with defaults
  python -m app.cli run-ptt
  
  # Run with custom PTT key and devices
  python -m app.cli run-ptt --ptt-key F9 \\
    --mic-device "Voicemeeter Output" \\
    --tts-device "Voicemeeter Aux Input"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # list-devices command
    parser_list = subparsers.add_parser(
        'list-devices',
        help='List all available audio devices'
    )
    parser_list.set_defaults(func=cmd_list_devices)
    
    # self-test command
    parser_test = subparsers.add_parser(
        'self-test',
        help='Run self-test to verify components'
    )
    parser_test.set_defaults(func=cmd_self_test)
    
    # run-ptt command
    parser_ptt = subparsers.add_parser(
        'run-ptt',
        help='Run PTT translation mode'
    )
    parser_ptt.add_argument(
        '--ptt-key',
        type=str,
        help='PTT hotkey (default: F8)'
    )
    parser_ptt.add_argument(
        '--mic-device',
        type=str,
        help='Microphone device name (substring match)'
    )
    parser_ptt.add_argument(
        '--tts-device',
        type=str,
        help='TTS output device name (substring match)'
    )
    parser_ptt.add_argument(
        '--lang-in',
        type=str,
        help='Input language code (default: uk-UA)'
    )
    parser_ptt.add_argument(
        '--lang-out',
        type=str,
        help='Output language code (default: en-GB)'
    )
    parser_ptt.add_argument(
        '--no-translate',
        action='store_true',
        help='Debug mode: STT only, no translation/TTS'
    )
    parser_ptt.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    parser_ptt.set_defaults(func=cmd_run_ptt)
    
    # Parse args
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
