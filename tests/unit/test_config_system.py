"""
Leonardo Configuration System Tests
Replaces raw CLI configuration testing commands
"""

import asyncio
import pytest
from pathlib import Path
import sys
import os

# Add Leonardo to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from leonardo.config import LeonardoConfig


class TestConfigurationSystem:
    """Test Leonardo's configuration loading and validation."""
    
    def test_default_config_creation(self):
        """Test creating default configuration."""
        print("🧪 Testing default configuration creation...")
        
        config = LeonardoConfig()
        
        assert config.debug == False
        assert config.log_level == "INFO"
        assert config.audio.sample_rate == 16000
        assert config.llm.model_name == "Qwen/Qwen2.5-7B-Instruct"
        assert config.tts.engine == "edge"
        
        print("✅ Default configuration created successfully")
    
    def test_toml_config_loading(self):
        """Test loading configuration from TOML file."""
        print("🧪 Testing TOML configuration loading...")
        
        toml_path = Path("leonardo.toml")
        if not toml_path.exists():
            pytest.skip("leonardo.toml not found")
        
        config = LeonardoConfig.load_from_file(toml_path)
        
        # Verify key settings from TOML
        assert config.llm.model_name == "Qwen/Qwen2.5-7B-Instruct"
        assert config.llm.enable_lora == True
        assert config.llm.lora_rank == 16
        assert config.tts.engine == "edge"
        assert config.tts.voice == "en-US-JennyNeural"
        assert config.stt.device == "cpu"
        assert config.stt.compute_type == "float32"
        
        print("✅ TOML configuration loaded successfully")
        print(f"  • LLM: {config.llm.model_name}")
        print(f"  • TTS: {config.tts.engine} ({config.tts.voice})")
        print(f"  • STT: {config.stt.device} ({config.stt.compute_type})")
    
    def test_directory_setup(self):
        """Test configuration directory creation."""
        print("🧪 Testing directory setup...")
        
        config = LeonardoConfig()
        config.setup_directories()
        
        # Check if data directory exists
        data_path = Path(config.data_dir)
        assert data_path.exists(), f"Data directory {data_path} not created"
        
        print("✅ Data directories created successfully")
        print(f"  • Data dir: {config.data_dir}")
    
    def test_config_validation(self):
        """Test configuration validation."""
        print("🧪 Testing configuration validation...")
        
        # Test basic validation - just verify config loads
        config = LeonardoConfig()
        
        # Check required fields exist
        assert hasattr(config, 'audio')
        assert hasattr(config, 'llm') 
        assert hasattr(config, 'tts')
        assert hasattr(config, 'stt')
        
        print("✅ Configuration validation working correctly")


def run_config_tests():
    """Run all configuration tests manually."""
    print("🎭 LEONARDO CONFIGURATION SYSTEM TESTS")
    print("=" * 45)
    
    test_suite = TestConfigurationSystem()
    
    try:
        test_suite.test_default_config_creation()
        test_suite.test_toml_config_loading()
        test_suite.test_directory_setup()
        test_suite.test_config_validation()
        
        print("\n🎉 ALL CONFIGURATION TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_config_tests()
    exit(0 if success else 1)
