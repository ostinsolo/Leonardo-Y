# Leonardo Test Suite

Professional testing framework for Leonardo AI Assistant that replaces raw CLI testing commands with structured, maintainable tests.

## 🎯 Purpose

This test suite provides:
- **Structured testing** instead of raw terminal commands
- **Reproducible results** across different environments  
- **Component isolation** for easier debugging
- **Integration validation** of the complete pipeline
- **Professional development workflow**

## 📁 Test Structure

```
tests/
├── unit/                           # Component-level tests
│   ├── test_config_system.py      # Configuration system tests
│   ├── test_stt_engine.py         # Speech-to-Text engine tests
│   ├── test_tts_engine.py         # Text-to-Speech engine tests
│   └── test_external_repos.py     # External repository integration tests
├── integration/                    # System-level tests
│   └── test_full_pipeline.py      # Complete voice-first pipeline tests
├── pipeline/                       # Future pipeline-specific tests
├── run_all_tests.py               # Main test runner
└── README.md                      # This file
```

## 🚀 Usage

### Run All Tests
```bash
# Activate Leonardo environment
source leonardo-py310/bin/activate

# Run complete test suite
python tests/run_all_tests.py
```

### Run Specific Tests
```bash
# Configuration tests only
python tests/run_all_tests.py config

# STT engine tests only  
python tests/run_all_tests.py stt

# TTS engine tests only
python tests/run_all_tests.py tts

# External repositories tests only
python tests/run_all_tests.py external

# Full pipeline integration tests only
python tests/run_all_tests.py pipeline
```

### Run Individual Test Files
```bash
# Run specific test file directly
python tests/unit/test_config_system.py
python tests/unit/test_stt_engine.py
python tests/unit/test_tts_engine.py
python tests/integration/test_full_pipeline.py
```

## 🧪 Test Categories

### Unit Tests
Test individual components in isolation:

- **Configuration System**: TOML loading, validation, directory setup
- **STT Engine**: Faster-Whisper integration, transcription, error handling
- **TTS Engine**: Edge TTS integration, synthesis, voice quality
- **External Repositories**: All 10+ external package integrations

### Integration Tests
Test complete system workflows:

- **Full Pipeline**: End-to-end voice-to-voice processing
- **Error Handling**: Graceful degradation and recovery
- **Configuration Integration**: System-wide configuration validation

## 📊 Test Output

The test runner provides:
- **Colored output** with clear status indicators (✅/❌/⚠️)
- **Detailed component information** (versions, capabilities)
- **Performance metrics** (timing, data sizes)
- **Summary statistics** (pass/fail rates, total time)
- **Professional reporting** for development workflow

## 🔧 Requirements

Tests require:
- **Python 3.10** environment (leonardo-py310/)
- **Leonardo dependencies** installed via UV
- **Leonardo configuration** (leonardo.toml) in project root
- **All external repositories** properly installed

## 🎭 Replaces Raw CLI Commands

This test suite replaces manual CLI commands like:
```bash
# OLD: Raw CLI testing (error-prone, not reproducible)
python -c "import torch; print(torch.__version__)"
python -c "from leonardo.config import LeonardoConfig; config = LeonardoConfig()"

# NEW: Structured tests (professional, maintainable)
python tests/run_all_tests.py external
python tests/run_all_tests.py config
```

## 🏆 Benefits

1. **Reproducibility**: Same results across environments
2. **Maintainability**: Easy to update and extend tests
3. **Professional**: Industry-standard testing practices
4. **Debugging**: Clear failure points and detailed output
5. **CI/CD Ready**: Can be integrated into automated workflows
6. **Documentation**: Tests serve as executable documentation

## 🔍 Example Output

```
🎭 LEONARDO AI ASSISTANT - PROFESSIONAL TEST SUITE
===============================================================================
📊 LEONARDO TEST SUITE RESULTS
===============================================================================
Configuration System              : ✅ PASSED
External Repositories             : ✅ PASSED  
STT Engine                        : ✅ PASSED
TTS Engine                        : ✅ PASSED
Full Pipeline                     : ✅ PASSED
-------------------------------------------------------------------------------
Total Tests: 5
Passed: 5
Failed: 0
Success Rate: 100.0%
Total Time: 12.34s
===============================================================================
🎉 ALL LEONARDO TESTS PASSED - SYSTEM READY!
```

This professional test suite ensures Leonardo is always in a known, working state and makes development much more reliable and maintainable!
