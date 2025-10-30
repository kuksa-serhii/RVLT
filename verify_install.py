"""
Installation verification script.

Run this after installation to verify all components are working.
"""

import sys
import importlib
from pathlib import Path


def check_python_version():
    """Check Python version."""
    print("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  ❌ Python {version.major}.{version.minor}.{version.micro} (need 3.10+)")
        return False


def check_imports():
    """Check required package imports."""
    print("\nChecking required packages...")
    
    packages = [
        ("numpy", "NumPy"),
        ("sounddevice", "SoundDevice"),
        ("soxr", "pysoxr"),
        ("pydantic", "Pydantic"),
        ("dotenv", "python-dotenv"),
        ("yaml", "PyYAML"),
    ]
    
    optional = [
        ("azure.cognitiveservices.speech", "Azure Speech SDK"),
        ("keyboard", "keyboard"),
        ("voicemeeterlib", "voicemeeterlib"),
    ]
    
    all_ok = True
    
    # Required packages
    for module, name in packages:
        try:
            importlib.import_module(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} - run: pip install {module}")
            all_ok = False
    
    # Optional packages
    print("\nChecking optional packages (may fail on CI)...")
    for module, name in optional:
        try:
            importlib.import_module(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ⚠️  {name} - optional, may not work without it")
    
    return all_ok


def check_app_structure():
    """Check app module structure."""
    print("\nChecking app module structure...")
    
    try:
        from app import __version__
        print(f"  ✅ app package (version {__version__})")
        
        modules = [
            "app.config",
            "app.audio_devices",
            "app.resample",
            "app.ptt",
            "app.voicemeeter_ctrl",
            "app.azure_speech",
            "app.pipeline",
            "app.utils",
            "app.cli",
        ]
        
        for module in modules:
            importlib.import_module(module)
            print(f"  ✅ {module}")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Error loading app: {e}")
        return False


def check_directories():
    """Check required directories exist."""
    print("\nChecking directory structure...")
    
    dirs = ["app", "tests", "logs", "debug_dumps", ".github"]
    all_ok = True
    
    for dir_name in dirs:
        path = Path(dir_name)
        if path.exists():
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/ - missing")
            all_ok = False
    
    return all_ok


def check_config_files():
    """Check configuration files exist."""
    print("\nChecking configuration files...")
    
    files = {
        ".env.example": "required",
        "requirements.txt": "required",
        "README.md": "required",
        ".gitignore": "required",
        ".env": "optional (create from .env.example)",
    }
    
    all_ok = True
    
    for filename, status in files.items():
        path = Path(filename)
        if path.exists():
            print(f"  ✅ {filename}")
        else:
            if "optional" in status:
                print(f"  ⚠️  {filename} - {status}")
            else:
                print(f"  ❌ {filename} - {status}")
                all_ok = False
    
    return all_ok


def main():
    """Run all checks."""
    print("=" * 60)
    print("RT Bilingual PTT Translator - Installation Verification")
    print("=" * 60)
    
    checks = [
        check_python_version(),
        check_imports(),
        check_app_structure(),
        check_directories(),
        check_config_files(),
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✅ All checks passed! Installation verified.")
        print("\nNext steps:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your Azure credentials to .env")
        print("  3. Run: python -m app.cli self-test")
        print("=" * 60)
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
