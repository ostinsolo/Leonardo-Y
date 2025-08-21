#!/usr/bin/env python3
"""
Leonardo Real Voice Test
ACTUAL microphone input → STT → LLM → TTS pipeline test

This version captures REAL AUDIO from your microphone!

Usage:
    python leonardo/real_voice_test.py
"""

import asyncio
import logging
import sys
import signal
import numpy as np
import threading
import queue
import time
from pathlib import Path

# Add Leonardo to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from leonardo.config import LeonardoConfig
from leonardo.io.stt_engine import STTEngine  
from leonardo.io.tts_engine import TTSEngine
from leonardo.planner.llm_planner import LLMPlanner
from leonardo.validator.validation_wall import ValidationWall
from leonardo.sandbox.executor import SandboxExecutor
from leonardo.verification.verifier import VerificationLayer
from leonardo.rag.rag_system import RAGSystem

# Audio libraries
try:
    import sounddevice as sd
    import soundfile as sf
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("❌ Audio libraries not available. Install with: pip install sounddevice soundfile")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealVoiceTest:
    """Real microphone input voice test for Leonardo."""
    
    def __init__(self):
        self.config = None
        self.stt_engine = None
        self.tts_engine = None
        self.llm_planner = None
        self.validator = None
        self.executor = None
        self.verifier = None
        self.rag_system = None
        self.running = False
        
        # Audio settings
        self.sample_rate = 16000  # 16kHz for Whisper
        self.channels = 1  # Mono
        self.dtype = np.float32
        self.blocksize = 1024
        
        # Voice activity detection
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.silence_threshold = 0.01  # Adjust based on your mic
        self.min_audio_length = 1.0    # Minimum 1 second of audio
        self.max_audio_length = 10.0   # Maximum 10 seconds
        self.silence_duration = 2.0    # 2 seconds of silence to stop recording
        
    async def initialize(self):
        """Initialize all Leonardo components."""
        print("🎙️ LEONARDO REAL VOICE TEST")
        print("=" * 40)
        print("🎤 This version captures REAL microphone input!")
        print()
        
        if not AUDIO_AVAILABLE:
            print("❌ Audio libraries not installed!")
            print("Run: pip install sounddevice soundfile")
            return False
        
        # Load configuration
        print("📋 Loading configuration...")
        self.config = LeonardoConfig.load_from_file(Path("leonardo.toml")) if Path("leonardo.toml").exists() else LeonardoConfig()
        self.config.audio.sample_rate = self.sample_rate  # Ensure consistent sample rate
        print(f"✅ Configuration loaded")
        
        # Initialize components
        print("🔧 Initializing Leonardo components...")
        
        # STT Engine
        print("  🎙️ Initializing Speech-to-Text...")
        self.stt_engine = STTEngine(self.config)
        await self.stt_engine.initialize()
        
        # TTS Engine  
        print("  🗣️ Initializing Text-to-Speech...")
        self.tts_engine = TTSEngine(self.config)
        await self.tts_engine.initialize()
        
        # RAG System (needed for LLM Planner)
        print("  📚 Initializing RAG system...")
        self.rag_system = RAGSystem(self.config)
        await self.rag_system.initialize()
        
        # LLM Planner
        print("  🧠 Initializing LLM Planner...")
        self.llm_planner = LLMPlanner(self.config, self.rag_system)
        await self.llm_planner.initialize()
        
        # Validation Wall
        print("  🛡️ Initializing Validation Wall...")
        self.validator = ValidationWall(self.config)
        await self.validator.initialize()
        
        # Sandbox Executor
        print("  📦 Initializing Sandbox Executor...")
        self.executor = SandboxExecutor(self.config)
        await self.executor.initialize()
        
        # Verification Layer
        print("  ✅ Initializing Verification Layer...")
        self.verifier = VerificationLayer(self.config)
        await self.verifier.initialize()
        
        print("✅ All components initialized!")
        print()
        
        # Test microphone
        await self.test_microphone()
        
        return True
        
    async def test_microphone(self):
        """Test microphone access."""
        print("🎤 Testing microphone access...")
        
        try:
            # List available audio devices
            devices = sd.query_devices()
            default_input = sd.default.device[0]
            
            print(f"🎤 Default input device: {devices[default_input]['name']}")
            print(f"   Sample rate: {devices[default_input]['default_samplerate']} Hz")
            print(f"   Channels: {devices[default_input]['max_input_channels']}")
            
            # Quick recording test
            print("🧪 Testing 2-second recording...")
            test_recording = sd.rec(
                frames=int(2 * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype
            )
            sd.wait()  # Wait for recording to complete
            
            # Check if we captured audio
            max_amplitude = np.max(np.abs(test_recording))
            print(f"📊 Max amplitude: {max_amplitude:.4f}")
            
            if max_amplitude > 0.001:
                print("✅ Microphone is working!")
            else:
                print("⚠️ Very quiet or no input detected")
                print("   Make sure your microphone is enabled and try speaking during the test")
            
            return True
            
        except Exception as e:
            print(f"❌ Microphone test failed: {e}")
            return False
    
    def audio_callback(self, indata, frames, time, status):
        """Audio callback for continuous recording."""
        if status:
            print(f"⚠️ Audio status: {status}")
        
        # Add audio data to queue
        self.audio_queue.put(indata.copy())
    
    def detect_voice_activity(self, audio_data):
        """Simple voice activity detection."""
        # Calculate RMS (Root Mean Square) energy
        rms = np.sqrt(np.mean(audio_data ** 2))
        return rms > self.silence_threshold
    
    async def record_voice_command(self):
        """Record a voice command from the microphone."""
        print("🎤 Listening... (speak now)")
        print("   💡 Tip: Speak clearly and wait for the response")
        
        recorded_audio = []
        silence_samples = 0
        total_samples = 0
        started_recording = False
        
        # Start audio stream
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            blocksize=self.blocksize,
            callback=self.audio_callback
        ):
            
            while self.running:
                try:
                    # Get audio data (timeout to check for stop)
                    audio_block = self.audio_queue.get(timeout=0.1)
                    
                    # Voice activity detection
                    has_voice = self.detect_voice_activity(audio_block)
                    
                    if has_voice and not started_recording:
                        print("🎤 Voice detected - recording...")
                        started_recording = True
                    
                    if started_recording:
                        recorded_audio.append(audio_block)
                        total_samples += len(audio_block)
                        
                        if has_voice:
                            silence_samples = 0
                            print("🔊", end="", flush=True)  # Visual feedback
                        else:
                            silence_samples += len(audio_block)
                            print(".", end="", flush=True)
                        
                        # Check stopping conditions
                        total_duration = total_samples / self.sample_rate
                        silence_duration = silence_samples / self.sample_rate
                        
                        if total_duration >= self.max_audio_length:
                            print(f"\n⏱️ Max recording time reached ({self.max_audio_length}s)")
                            break
                        
                        if (total_duration >= self.min_audio_length and 
                            silence_duration >= self.silence_duration):
                            print(f"\n⏹️ Recording complete ({total_duration:.1f}s)")
                            break
                    
                except queue.Empty:
                    # Timeout - continue listening
                    continue
                except KeyboardInterrupt:
                    print("\n⏹️ Recording interrupted")
                    break
        
        if not recorded_audio:
            print("❌ No audio recorded")
            return None
        
        # Convert to numpy array
        audio_data = np.concatenate(recorded_audio)
        
        # Convert from float32 to int16 for Whisper
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        print(f"🎵 Recorded {len(audio_data)/self.sample_rate:.1f}s of audio")
        
        return audio_int16.tobytes()
    
    async def process_voice_command(self):
        """Record and process a complete voice command."""
        print("\n" + "="*50)
        
        # Record audio
        audio_data = await self.record_voice_command()
        
        if not audio_data:
            return None
        
        try:
            # Step 1: STT - Convert audio to text
            print("1️⃣ STT: Converting speech to text...")
            transcription = await self.stt_engine.transcribe(audio_data)
            
            if not transcription or not transcription.strip():
                print("❌ No speech detected or transcription failed")
                return None
            
            print(f"📝 Transcribed: '{transcription}'")
            
            # Step 2: Process through Leonardo pipeline
            print("2️⃣ PROCESSING: Running through Leonardo pipeline...")
            
            # Planning
            print("   🧠 Generating plan...")
            plan = await self.llm_planner.generate_plan(transcription)
            print(f"      Tool: {plan.tool_call.get('tool', 'unknown')}")
            
            # Validation
            print("   🛡️ Validating safety...")
            validation_result = await self.validator.validate_plan(plan)
            
            if not validation_result.is_valid:
                response_text = f"I cannot do that: {validation_result.reason}"
                print(f"   ❌ Validation failed: {validation_result.reason}")
            else:
                print(f"   ✅ Validation passed (risk: {validation_result.risk_level})")
                
                # Execution
                print("   📦 Executing in sandbox...")
                execution_result = await self.executor.execute_plan(validation_result.validated_plan)
                print(f"      Status: {'SUCCESS' if execution_result.success else 'FAILED'}")
                
                # Verification
                print("   ✅ Verifying results...")
                verification_result = await self.verifier.verify_execution(plan.tool_call, execution_result)
                
                response_text = verification_result.summary if verification_result.summary else "Task completed successfully."
            
            # Step 3: TTS - Generate voice response
            print("3️⃣ TTS: Generating voice response...")
            print(f"🗣️ Response: '{response_text}'")
            
            audio_response = await self.tts_engine.synthesize(response_text)
            
            if len(audio_response) > 0:
                print(f"🎵 Generated {len(audio_response)} bytes of audio")
                print("🔊 (In full implementation, this would play through speakers)")
                
                # TODO: Implement actual audio playback
                # For now, we confirm audio generation
            else:
                print("❌ No audio generated")
            
            print("✅ Voice command processed successfully!")
            return transcription
            
        except Exception as e:
            print(f"❌ Voice processing failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def run_voice_loop(self):
        """Main voice interaction loop."""
        print("\n🎙️ REAL VOICE INTERACTION")
        print("=" * 40)
        print("🎤 Leonardo is now listening to your microphone!")
        print("📢 Say something to test the complete voice pipeline")
        print("⏹️ Press Ctrl+C to exit")
        print()
        
        command_count = 0
        
        while self.running:
            try:
                print(f"\n--- Voice Command #{command_count + 1} ---")
                print("🎧 Ready to listen...")
                
                result = await self.process_voice_command()
                
                if result:
                    command_count += 1
                    print(f"✅ Command {command_count} completed!")
                else:
                    print("⚠️ No valid command detected, trying again...")
                
                # Brief pause before next command
                await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Voice loop error: {e}")
                await asyncio.sleep(2)  # Brief pause before retrying
        
        print(f"\n📊 Session complete: Processed {command_count} voice commands")
    
    async def run_real_voice_test(self):
        """Run the real voice test."""
        self.running = True
        
        try:
            # Initialize all components
            if not await self.initialize():
                return
            
            # Run voice loop
            await self.run_voice_loop()
        
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown all components gracefully."""
        print("\n🛑 Shutting down Leonardo components...")
        
        self.running = False
        
        if self.verifier:
            await self.verifier.shutdown()
        if self.executor:
            await self.executor.shutdown()
        if self.validator:
            await self.validator.shutdown()
        if self.llm_planner:
            await self.llm_planner.shutdown()
        if self.rag_system:
            await self.rag_system.shutdown()
        if self.tts_engine:
            await self.tts_engine.shutdown()
        if self.stt_engine:
            await self.stt_engine.shutdown()
            
        print("✅ All components shut down successfully")

async def main():
    """Main function to run the real voice test."""
    
    # Handle Ctrl+C gracefully
    test_instance = RealVoiceTest()
    
    def signal_handler(signum, frame):
        print("\n\n⚠️ Received interrupt signal, shutting down...")
        test_instance.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await test_instance.run_real_voice_test()
    except KeyboardInterrupt:
        print("\n👋 Voice test interrupted by user")
    except Exception as e:
        print(f"\n❌ Voice test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting Leonardo REAL Voice Test...")
    print("🎤 This will capture audio from your microphone!")
    print("Press Ctrl+C anytime to exit gracefully")
    print()
    
    # Run the async test
    asyncio.run(main())
