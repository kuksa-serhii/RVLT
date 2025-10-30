# 🤝 Contributing to RT Bilingual PTT Translator

Thank you for your interest in contributing! This guide will help you get started.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Setup](#development-setup)
- [Project Architecture](#project-architecture)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Feature Requests](#feature-requests)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Respect privacy and data protection

## Development Setup

### 1. Fork and Clone

```powershell
git clone https://github.com/YOUR_USERNAME/RVLT.git
cd RVLT
git remote add upstream https://github.com/kuksa-serhii/RVLT.git
```

### 2. Create Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .  # Editable install
```

### 3. Setup Pre-commit (Optional)

```powershell
pip install pre-commit
pre-commit install
```

### 4. Run Tests

```powershell
pytest tests/ -v
```

## Project Architecture

### Module Overview

```
app/
├── config.py           # Configuration (add new settings here)
├── audio_devices.py    # Audio I/O (extend for new devices)
├── resample.py         # Sample rate conversion
├── ptt.py              # PTT input (add new input methods)
├── voicemeeter_ctrl.py # Voicemeeter API (add new controls)
├── azure_speech.py     # Azure SDK integration
├── pipeline.py         # Main orchestration
├── utils.py            # Utilities (add helpers here)
└── cli.py              # CLI commands (add new commands)
```

### Key Design Patterns

1. **Dependency Injection**: Pass config objects
2. **Context Managers**: Use `with` for resource management
3. **Event Callbacks**: Subscribe/notify pattern
4. **Graceful Degradation**: Guard imports, handle errors

## Coding Standards

### Python Style

- **PEP 8** compliance (use `flake8`)
- **Type hints** for all function signatures
- **Docstrings** for all public functions/classes
- **Max line length**: 120 characters

Example:
```python
def process_audio(
    audio_data: np.ndarray,
    sample_rate: int,
    channels: int = 1
) -> np.ndarray:
    """
    Process audio data with optional resampling.
    
    Args:
        audio_data: Input audio as int16 array
        sample_rate: Sample rate in Hz
        channels: Number of channels (default: 1)
        
    Returns:
        Processed audio data
        
    Raises:
        ValueError: If sample rate is invalid
    """
    # Implementation
```

### Naming Conventions

- **Functions/methods**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Private members**: `_leading_underscore`

### Error Handling

```python
# Good
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    return None

# Avoid bare except
except:  # ❌ Don't do this
    pass
```

### Logging

```python
import logging
logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Detailed info")
logger.info("General info")
logger.warning("Warning")
logger.error("Error occurred")
```

## Testing

### Writing Tests

Place tests in `tests/test_<module>.py`:

```python
import pytest
from app.module import function_to_test

def test_function_basic():
    """Test basic functionality."""
    result = function_to_test(input_data)
    assert result == expected_output

def test_function_edge_case():
    """Test edge case."""
    with pytest.raises(ValueError):
        function_to_test(invalid_input)

@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {"key": "value"}

def test_with_fixture(sample_data):
    """Test using fixture."""
    assert sample_data["key"] == "value"
```

### Running Tests

```powershell
# All tests
pytest tests/ -v

# Specific file
pytest tests/test_resample.py -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Only failed tests
pytest tests/ --lf
```

### Mocking External Dependencies

```python
from unittest.mock import Mock, patch

@patch('app.module.external_dependency')
def test_with_mock(mock_dep):
    mock_dep.return_value = "mocked result"
    result = function_using_dependency()
    assert result == "expected"
```

## Pull Request Process

### 1. Create Feature Branch

```powershell
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Changes

- Write code following standards above
- Add/update tests
- Update documentation if needed
- Run tests locally

### 3. Commit Changes

```powershell
git add .
git commit -m "feat: Add new feature description"
```

**Commit message format:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `test:` Adding tests
- `refactor:` Code refactoring
- `perf:` Performance improvement
- `chore:` Maintenance tasks

### 4. Push and Create PR

```powershell
git push origin feature/your-feature-name
```

Then create Pull Request on GitHub with:
- Clear title
- Description of changes
- Related issue number (if any)
- Screenshots/logs (if applicable)

### 5. Code Review

- Address reviewer comments
- Make requested changes
- Push updates to same branch

## Feature Requests

### Adding New Features

#### Example: Add new language pair

1. **Update config:**
   ```python
   # app/config.py
   class SpeechConfig(BaseModel):
       tts_voice_fr: str = Field("fr-FR-DeniseNeural", ...)
   ```

2. **Add CLI option:**
   ```python
   # app/cli.py
   parser_ptt.add_argument('--lang-pair', choices=['ua-en', 'en-fr'])
   ```

3. **Implement logic:**
   ```python
   # app/pipeline.py
   def _select_tts_voice(self, target_lang: str) -> str:
       # Voice selection logic
   ```

4. **Add tests:**
   ```python
   # tests/test_pipeline.py
   def test_language_pair_selection():
       # Test new feature
   ```

5. **Update docs:**
   ```markdown
   # README.md
   ## Supported Languages
   - Ukrainian ↔ English
   - English ↔ French (new!)
   ```

#### Example: Add streaming TTS

See `TODO` comments in `app/azure_speech.py`:
```python
def synthesize_to_pcm48_async(self, text: str, callback: Callable):
    # TODO: Implement streaming TTS for lower latency
```

## Areas for Contribution

### 🌟 High Priority

- [ ] Streaming TTS implementation
- [ ] Performance optimizations
- [ ] Better error messages
- [ ] More unit tests

### 🔧 Medium Priority

- [ ] Web UI dashboard
- [ ] Additional language pairs
- [ ] BLE/HID PTT support
- [ ] LLM text polishing

### 📚 Documentation

- [ ] Video tutorials
- [ ] Voicemeeter setup guide
- [ ] Azure setup guide
- [ ] FAQ section

### 🐛 Bug Fixes

- Check [Issues](https://github.com/kuksa-serhii/RVLT/issues)
- Look for `good first issue` label
- Fix and test

## Questions?

- **General questions**: [Discussions](https://github.com/kuksa-serhii/RVLT/discussions)
- **Bug reports**: [Issues](https://github.com/kuksa-serhii/RVLT/issues)
- **Feature ideas**: [Discussions - Ideas](https://github.com/kuksa-serhii/RVLT/discussions/categories/ideas)

---

**Thank you for contributing!** 🎉
