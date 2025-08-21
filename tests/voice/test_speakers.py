#!/usr/bin/env python3
"""
Quick Speaker Test
Test audio playback through speakers
"""

import asyncio
import sys
from pathlib import Path

# Add Leonardo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo.config import LeonardoConfig
from leonardo.io.tts_engine import TTSEngine

try:
    import sounddevice as sd
    import numpy as np
    import io
    import wave
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("❌ Audio libraries not available. Install with: pip install sounddevice")

async def test_speakers():
    """Test speaker output with TTS."""
    if not AUDIO_AVAILABLE:
        print("❌ Audio libraries not installed!")
        return False
    
    print("🔊 Testing Leonardo's speaker output...")
    
    # Initialize TTS
    config = LeonardoConfig()
    tts_engine = TTSEngine(config)
    await tts_engine.initialize()
    
    # Generate test audio
    test_text = "Hello! This is Leonardo testing the speaker output. Can you hear me clearly?"
    print(f"🗣️ Generating: '{test_text}'")
    
    audio_data = await tts_engine.synthesize(test_text)
    
    if len(audio_data) > 0:
        print(f"✅ Generated {len(audio_data)} bytes of audio")
        
        try:
            # Try to play the audio
            print("🎵 Playing through speakers...")
            
            # Edge TTS audio format handling
            # First, save to a temporary file and play it
            import tempfile
            import os
            
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_filename = temp_file.name
            
            try:
                # Try to load with soundfile
                try:
                    import soundfile as sf
                    audio_array, sample_rate = sf.read(temp_filename)
                    
                    print(f"📊 Audio info: {sample_rate} Hz, {audio_array.shape} shape")
                    print(f"🎵 Playing {len(audio_array)} samples...")
                    
                    # Play the audio
                    sd.play(audio_array, samplerate=sample_rate)
                    sd.wait()  # Wait until audio finishes playing
                    
                    print("✅ Speaker test completed!")
                    print("🎉 If you heard Leonardo speak, speakers are working!")
                    
                    # Clean up temp file
                    os.unlink(temp_filename)
                    return True
                    
                except ImportError:
                    print("⚠️ soundfile not available, trying alternative...")
                    
                    # Alternative: try with pygame
                    try:
                        import pygame
                        pygame.mixer.init()
                        pygame.mixer.music.load(temp_filename)
                        
                        print("🎵 Playing with pygame...")
                        pygame.mixer.music.play()
                        
                        # Wait for playback to complete
                        while pygame.mixer.music.get_busy():
                            await asyncio.sleep(0.1)
                        
                        print("✅ Speaker test completed!")
                        print("🎉 If you heard Leonardo speak, speakers are working!")
                        
                        pygame.mixer.quit()
                        os.unlink(temp_filename)
                        return True
                        
                    except ImportError:
                        print("⚠️ pygame not available, trying system playback...")
                        
                        # Last resort: use system audio player
                        import subprocess
                        import sys
                        
                        if sys.platform == 'darwin':  # macOS
                            subprocess.run(['afplay', temp_filename], check=True)
                            print("✅ Speaker test completed with system player!")
                            print("🎉 If you heard Leonardo speak, speakers are working!")
                            os.unlink(temp_filename)
                            return True
                        else:
                            print("❌ No suitable audio player found")
                            os.unlink(temp_filename)
                            return False
            
            except Exception as e:
                print(f"❌ Audio file playback failed: {e}")
                if 'temp_filename' in locals():
                    try:
                        os.unlink(temp_filename)
                    except:
                        pass
                return False
                
        except Exception as e:
            print(f"❌ Speaker playback failed: {e}")
            return False
    else:
        print("❌ No audio generated")
        return False
    
    await tts_engine.shutdown()

if __name__ == "__main__":
    print("🔊 Leonardo Speaker Test")
    print("=" * 30)
    
    success = asyncio.run(test_speakers())
    
    if success:
        print("\n🎉 Speakers are working! Ready for full voice loop.")
    else:
        print("\n❌ Speaker test failed. Check audio setup.")
