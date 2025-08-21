"""
Leonardo TTS Engine Tests
Replaces raw CLI TTS testing commands
"""

import asyncio
import pytest
from pathlib import Path
import sys
import os

# Add Leonardo to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from leonardo.config import LeonardoConfig
from leonardo.io.tts_engine import TTSEngine


class TestTTSEngine:
    """Test Leonardo's Text-to-Speech engine."""
    
    def setup_method(self):
        """Setup for each test."""
        self.config = LeonardoConfig.load_from_file(Path("leonardo.toml")) if Path("leonardo.toml").exists() else LeonardoConfig()
        
    @pytest.mark.asyncio
    async def test_tts_engine_initialization(self):
        """Test TTS engine initialization."""
        print("🧪 Testing TTS engine initialization...")
        
        tts_engine = TTSEngine(self.config)
        
        print(f"  • Engine: {self.config.tts.engine}")
        print(f"  • Voice: {self.config.tts.voice}")
        print(f"  • Language: {self.config.tts.language}")
        
        try:
            await tts_engine.initialize()
            print("✅ TTS engine initialized successfully")
            
            await tts_engine.shutdown()
            print("✅ TTS engine shutdown complete")
            
        except Exception as e:
            print(f"❌ TTS initialization failed: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_tts_synthesis(self):
        """Test TTS speech synthesis."""
        print("🧪 Testing TTS speech synthesis...")
        
        tts_engine = TTSEngine(self.config)
        
        try:
            await tts_engine.initialize()
            
            test_texts = [
                "Hello, I am Leonardo, your voice-first assistant!",
                "Testing speech synthesis with a longer sentence to verify audio quality and naturalness.",
                "Short test."
            ]
            
            for i, text in enumerate(test_texts, 1):
                print(f"  • Test {i}: '{text[:50]}{'...' if len(text) > 50 else ''}'")
                
                audio_data = await tts_engine.synthesize(text)
                
                if len(audio_data) > 0:
                    print(f"    ✅ Generated {len(audio_data)} bytes of audio")
                else:
                    print(f"    ⚠️  No audio generated")
            
            await tts_engine.shutdown()
            print("✅ TTS synthesis tests completed")
            
        except Exception as e:
            print(f"❌ TTS synthesis failed: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_tts_edge_cases(self):
        """Test TTS with edge cases."""
        print("🧪 Testing TTS edge cases...")
        
        tts_engine = TTSEngine(self.config)
        
        try:
            await tts_engine.initialize()
            
            edge_cases = [
                "",  # Empty string
                "   ",  # Whitespace only
                "A",  # Single character
                "Hello! How are you? I'm fine. Thanks for asking!",  # Punctuation
                "Testing with numbers: 123, 456.789, and symbols @#$%"  # Special characters
            ]
            
            for i, text in enumerate(edge_cases, 1):
                print(f"  • Edge case {i}: '{text}' ({len(text)} chars)")
                
                audio_data = await tts_engine.synthesize(text)
                
                if len(text.strip()) == 0:
                    assert len(audio_data) == 0, "Empty text should produce no audio"
                    print(f"    ✅ Correctly handled empty text")
                else:
                    print(f"    ✅ Generated {len(audio_data)} bytes")
            
            await tts_engine.shutdown()
            print("✅ TTS edge case tests completed")
            
        except Exception as e:
            print(f"❌ TTS edge case testing failed: {e}")
            raise
    
    def test_tts_config_validation(self):
        """Test TTS configuration validation."""
        print("🧪 Testing TTS configuration...")
        
        tts_config = self.config.tts
        
        # Validate key configuration values
        assert tts_config.engine in ["edge", "piper", "avspeech"], f"Invalid TTS engine: {tts_config.engine}"
        assert isinstance(tts_config.voice, str) and len(tts_config.voice) > 0, f"Invalid voice: {tts_config.voice}"
        assert tts_config.language in ["en-US", "en-GB", "es-ES", "fr-FR", "de-DE"], f"Invalid language: {tts_config.language}"
        
        print("✅ TTS configuration validated")
        print(f"  • Engine: {tts_config.engine}")
        print(f"  • Voice: {tts_config.voice}")
        print(f"  • Language: {tts_config.language}")


async def run_tts_tests():
    """Run all TTS tests manually."""
    print("🎭 LEONARDO TTS ENGINE TESTS")
    print("=" * 34)
    
    test_suite = TestTTSEngine()
    test_suite.setup_method()
    
    try:
        # Run sync tests
        test_suite.test_tts_config_validation()
        
        # Run async tests
        await test_suite.test_tts_engine_initialization()
        await test_suite.test_tts_synthesis()
        await test_suite.test_tts_edge_cases()
        
        print("\n🎉 ALL TTS TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ TTS test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_tts_tests())
    exit(0 if success else 1)
