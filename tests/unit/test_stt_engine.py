"""
Leonardo STT Engine Tests
Replaces raw CLI STT testing commands
"""

import asyncio
import pytest
import numpy as np
from pathlib import Path
import sys
import os

# Add Leonardo to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from leonardo.config import LeonardoConfig
from leonardo.io.stt_engine import STTEngine


class TestSTTEngine:
    """Test Leonardo's Speech-to-Text engine."""
    
    def setup_method(self):
        """Setup for each test."""
        self.config = LeonardoConfig.load_from_file(Path("leonardo.toml")) if Path("leonardo.toml").exists() else LeonardoConfig()
        
    @pytest.mark.asyncio
    async def test_stt_engine_initialization(self):
        """Test STT engine initialization."""
        print("🧪 Testing STT engine initialization...")
        
        stt_engine = STTEngine(self.config)
        
        print(f"  • Model: {self.config.stt.model_size}")
        print(f"  • Device: {self.config.stt.device}")
        print(f"  • Compute type: {self.config.stt.compute_type}")
        
        try:
            await stt_engine.initialize()
            print("✅ STT engine initialized successfully")
            
            await stt_engine.shutdown()
            print("✅ STT engine shutdown complete")
            
        except Exception as e:
            print(f"❌ STT initialization failed: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_stt_transcription(self):
        """Test STT transcription with dummy audio."""
        print("🧪 Testing STT transcription...")
        
        stt_engine = STTEngine(self.config)
        
        try:
            await stt_engine.initialize()
            
            # Create dummy audio data (2 seconds of silence)
            sample_rate = self.config.audio.sample_rate
            dummy_audio = np.zeros(sample_rate * 2, dtype=np.int16).tobytes()
            
            print(f"  • Testing with {len(dummy_audio)} bytes of audio")
            
            result = await stt_engine.transcribe(dummy_audio)
            
            print(f"✅ Transcription completed: '{result}'")
            print("  • Note: Empty result expected for silent audio")
            
            await stt_engine.shutdown()
            
        except Exception as e:
            print(f"❌ STT transcription failed: {e}")
            raise
    
    def test_stt_config_validation(self):
        """Test STT configuration validation."""
        print("🧪 Testing STT configuration...")
        
        stt_config = self.config.stt
        
        # Validate key configuration values
        assert stt_config.model_size in ["tiny", "base", "small", "medium", "large"], f"Invalid model size: {stt_config.model_size}"
        assert stt_config.device in ["cpu", "cuda", "auto"], f"Invalid device: {stt_config.device}"
        assert stt_config.compute_type in ["float16", "float32", "int8"], f"Invalid compute type: {stt_config.compute_type}"
        
        print("✅ STT configuration validated")
        print(f"  • Model size: {stt_config.model_size}")
        print(f"  • Device: {stt_config.device}")
        print(f"  • Compute type: {stt_config.compute_type}")


async def run_stt_tests():
    """Run all STT tests manually."""
    print("🎭 LEONARDO STT ENGINE TESTS")
    print("=" * 34)
    
    test_suite = TestSTTEngine()
    test_suite.setup_method()
    
    try:
        # Run sync tests
        test_suite.test_stt_config_validation()
        
        # Run async tests
        await test_suite.test_stt_engine_initialization()
        await test_suite.test_stt_transcription()
        
        print("\n🎉 ALL STT TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ STT test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_stt_tests())
    exit(0 if success else 1)
