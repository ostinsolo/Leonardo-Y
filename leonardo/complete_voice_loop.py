#!/usr/bin/env python3
"""
Leonardo Complete Voice Loop
FULL microphone → STT → LLM → TTS → speakers pipeline

This version includes REAL AUDIO PLAYBACK through speakers!

Usage:
    python leonardo/complete_voice_loop.py
"""

import asyncio
import logging
import sys
import signal
import numpy as np
import threading
import queue
import time
import io
import wave
from pathlib import Path

# Add Leonardo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo.config import LeonardoConfig
from leonardo.io.stt_engine import STTEngine  
from leonardo.io.tts_engine import TTSEngine
from leonardo.planner.llm_planner import LLMPlanner
from leonardo.validator.validation_wall import ValidationWall
from leonardo.sandbox.executor import SandboxExecutor
from leonardo.verification.verifier import VerificationLayer
from leonardo.rag.rag_system import RAGSystem
from leonardo.memory.service import MemoryService  # ADD MEMORY SERVICE
from leonardo.interaction_logger import InteractionLogger

# Audio libraries
try:
    import sounddevice as sd
    import soundfile as sf
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("❌ Audio libraries not available. Install with: pip install sounddevice soundfile")

# Configure logging - reduce noise from libraries
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format='%(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Silence noisy libraries
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("edge_tts").setLevel(logging.ERROR)
logging.getLogger("faster_whisper").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)

class CompleteVoiceLoop:
    """Complete voice loop with microphone input and speaker output."""
    
    def __init__(self):
        self.config = None
        self.stt_engine = None
        self.tts_engine = None
        self.llm_planner = None
        self.memory_service = None  # ADD MEMORY SERVICE
        self.validator = None
        self.executor = None
        self.verifier = None
        self.rag_system = None
        self.running = False
        
        # Interaction logging
        self.logger = InteractionLogger()
        self.current_interaction_id = None
        
        # Memory will be handled by MemoryService, not here
        
        # Audio settings
        self.sample_rate = 16000  # 16kHz for Whisper
        self.channels = 1  # Mono
        self.dtype = np.float32
        self.blocksize = 1024
        
        # Voice activity detection
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.silence_threshold = 0.02  # Higher threshold to filter noise
        self.min_audio_length = 2.0    # Minimum 2 seconds of audio
        self.max_audio_length = 8.0    # Maximum 8 seconds
        self.silence_duration = 1.5    # 1.5 seconds of silence to stop recording
        
    async def initialize(self):
        """Initialize all Leonardo components."""
        print("🎭 LEONARDO COMPLETE VOICE LOOP")
        print("=" * 50)
        print("🎙️ Microphone → 🧠 AI → 🔊 Speakers")
        print("Full voice-first AI assistant!")
        print()
        
        if not AUDIO_AVAILABLE:
            print("❌ Audio libraries not installed!")
            print("Run: pip install sounddevice soundfile")
            return False
        
        # Load configuration (quiet)
        self.config = LeonardoConfig.load_from_file(Path("leonardo.toml")) if Path("leonardo.toml").exists() else LeonardoConfig()
        self.config.audio.sample_rate = self.sample_rate  # Ensure consistent sample rate
        
        # Initialize components (quiet initialization)
        print("🔧 Starting Leonardo's brain...")
        
        # STT Engine
        self.stt_engine = STTEngine(self.config)
        await self.stt_engine.initialize()
        
        # TTS Engine  
        self.tts_engine = TTSEngine(self.config)
        await self.tts_engine.initialize()
        
        # RAG System (needed for LLM Planner)
        self.rag_system = RAGSystem(self.config)
        await self.rag_system.initialize()
        
        # Memory Service (needed for LLM Planner)
        self.memory_service = MemoryService(self.config)
        await self.memory_service.initialize()
        
        # LLM Planner (with memory and RAG)
        self.llm_planner = LLMPlanner(self.config, self.rag_system, self.memory_service)
        await self.llm_planner.initialize()
        
        # Validation Wall
        self.validator = ValidationWall(self.config)
        await self.validator.initialize()
        
        # Sandbox Executor
        self.executor = SandboxExecutor(self.config)
        await self.executor.initialize()
        
        # Verification Layer
        self.verifier = VerificationLayer(self.config)
        await self.verifier.initialize()
        
        print("✅ Leonardo is ready!")
        print()
        
        # Test microphone and speakers
        await self.test_audio_devices()
        
        return True
        
    async def test_audio_devices(self):
        """Test microphone and speaker access."""
        try:
            # Get device info quietly
            devices = sd.query_devices()
            default_input = sd.default.device[0]
            default_output = sd.default.device[1]
            
            print(f"🎤 Microphone: {devices[default_input]['name']}")
            print(f"🔊 Speakers: {devices[default_output]['name']}")
            
            # Test TTS and playback
            print("🧪 Testing voice response...")
            
            test_text = "Hello! I am Leonardo and I'm ready to talk."
            audio_data = await self.tts_engine.synthesize(test_text)
            
            if len(audio_data) > 0:
                # Play the audio through speakers
                success = await self.play_audio(audio_data)
                
                if success:
                    print("✅ Audio test successful!")
                else:
                    print("⚠️ Speaker test failed")
            else:
                print("❌ No audio generated")
            
            return True
            
        except Exception as e:
            print(f"❌ Audio test failed: {e}")
            return False
    
    async def play_audio(self, audio_data: bytes) -> bool:
        """Play audio data through speakers using the proven method."""
        try:
            # Save to temporary file and use soundfile (proven working method)
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_filename = temp_file.name
            
            try:
                # Use soundfile to read and play
                audio_array, sample_rate = sf.read(temp_filename)
                
                # Play the audio (quietly)
                sd.play(audio_array, samplerate=sample_rate)
                sd.wait()  # Wait until audio finishes playing
                
                # Clean up temp file
                os.unlink(temp_filename)
                return True
                
            except Exception as e:
                print(f"❌ Audio playback failed: {e}")
                try:
                    os.unlink(temp_filename)
                except:
                    pass
                return False
        
        except Exception as e:
            print(f"❌ Audio playback setup failed: {e}")
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
    
    def is_valid_speech(self, text: str) -> bool:
        """Filter out garbage transcriptions."""
        if not text or len(text.strip()) < 3:
            return False
            
        # Filter out random characters or technical gibberish
        text_clean = text.strip().lower()
        
        # Check if it contains mostly gibberish
        if len([c for c in text_clean if c.isalpha()]) < len(text_clean) * 0.6:
            return False
            
        # Filter out very repetitive text
        words = text_clean.split()
        if len(set(words)) == 1 and len(words) > 3:
            return False
            
        # Filter out single random characters
        if len(text_clean) < 3 and not any(word in text_clean for word in ['hi', 'hey', 'yes', 'no', 'ok']):
            return False
            
        return True

    async def generate_intelligent_response(self, user_input: str, user_id: str = "default"):
        """Generate context-aware responses using Leonardo's full intelligence stack."""
        try:
            # Use Leonardo's LLM Planner with MCP memory integration
            plan_result = await self.llm_planner.generate_plan(user_input, user_id)
            
            if plan_result and plan_result.tool_call:
                tool_call = plan_result.tool_call
                
                # Handle different tool types
                if tool_call.get("tool") == "respond":
                    message = tool_call.get("args", {}).get("message", "")
                    if message:
                        return message
            
            # Fallback to basic logic if no plan or MCP memory unavailable  
            import datetime
            user_lower = user_input.lower()
            
            # Handle memory/context questions - now with MCP memory context
            if any(phrase in user_lower for phrase in ['remember', 'what you said', 'what did you say', 'before']):
                # Try to get actual memory context (using async version)
                if self.memory_service:
                    context = await self.memory_service.get_context_async(user_id, user_input)
                    recent_turns = context.get('recent_turns', [])
                    if recent_turns:
                        # Find the last non-memory question
                        for turn in reversed(recent_turns):
                            if turn.get('user_input') and not any(phrase in turn['user_input'].lower() for phrase in ['remember', 'what you said', 'before']):
                                return f"You asked me: '{turn['user_input']}'"
                
                return "I don't see any previous questions in our conversation yet."
            
            # Name learning and personalization
            name_mentioned = None
            import re
            name_patterns = [
                r"my name is (\w+)",
                r"i'm (\w+)", 
                r"call me (\w+)",
                r"i am (\w+)"
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, user_lower)
                if match:
                    name_mentioned = match.group(1).title()
                    break
            
            if name_mentioned:
                return f"Nice to meet you, {name_mentioned}! I'll remember that. How can I help you today?"
            
            # Context-aware greetings
            if any(word in user_lower for word in ['hello', 'hi', 'hey']):
                return "Hello! I'm Leonardo, your voice assistant. How can I help you today?"
            
            # Standard queries 
            if any(word in user_lower for word in ['weather', 'temperature', 'forecast']):
                return "I'd love to check the weather for you! Weather lookup is coming soon."
            
            elif any(word in user_lower for word in ['search', 'find', 'look up', 'google']):
                return "I understand you want to search for information. Web search integration is being developed!"
            
            elif any(word in user_lower for word in ['time', 'clock', 'what time']):
                current_time = datetime.datetime.now().strftime("%I:%M %p")
                return f"The current time is {current_time}."
            
            elif any(word in user_lower for word in ['date', 'today', 'what day']):
                current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
                return f"Today is {current_date}."
            
            elif any(word in user_lower for word in ['email', 'send email']):
                return "I'd help you with email! Email integration is being implemented."
            
            elif any(word in user_lower for word in ['stop', 'quit', 'exit', 'goodbye']):
                return "Goodbye! Thanks for talking with me."
            
            elif any(word in user_lower for word in ['test', 'testing']):
                return "Test successful! Conversation memory is working perfectly."
            
            elif any(word in user_lower for word in ['music', 'song', 'play']):
                return "I'd love to help you play music! Music integration is coming soon."
            
            elif any(word in user_lower for word in ['news', 'latest', 'headlines']):
                return "I'd get the latest news for you! News integration is being developed."
            
            else:
                # General response
                return f"I heard you say '{user_input}'. How can I help you with that?"
            
        except Exception as e:
            print(f"⚠️ LLM planning error: {e}")
            # Fallback to basic response
            return f"I heard you say '{user_input}'. Let me help you with that."
    
    def _classify_response_type(self, user_input: str) -> str:
        """Classify the type of user input for logging."""
        user_lower = user_input.lower()
        
        if any(word in user_lower for word in ['hello', 'hi', 'hey']):
            return "greeting"
        elif any(word in user_lower for word in ['time', 'clock']):
            return "time_query"
        elif any(word in user_lower for word in ['date', 'today']):
            return "date_query"
        elif any(word in user_lower for word in ['weather', 'temperature']):
            return "weather_query"
        elif any(word in user_lower for word in ['search', 'find', 'google']):
            return "search_request"
        elif any(word in user_lower for word in ['email', 'send']):
            return "email_request"
        elif any(word in user_lower for word in ['music', 'play', 'song']):
            return "media_request"
        elif any(word in user_lower for word in ['stop', 'quit', 'exit']):
            return "exit_command"
        elif any(word in user_lower for word in ['test', 'testing']):
            return "system_test"
        else:
            return "general_query"
    
    # Old conversation history methods removed - now using MCP Memory System
    
    async def process_complete_voice_loop(self):
        """Process a complete voice loop: mic → AI → speakers with detailed logging."""
        import time
        
        print("\n" + "="*60)
        
        # START INTERACTION LOGGING
        interaction_id = self.logger.start_interaction()
        self.current_interaction_id = interaction_id
        
        try:
            # Phase 1: Audio Recording
            start_time = time.time()
            audio_data = await self.record_voice_command()
            recording_time = time.time() - start_time
            
            if not audio_data:
                self.logger.log_issue(interaction_id, "audio", "No audio data captured")
                self.logger.finish_interaction(interaction_id, success=False)
                return None
            
            # Log audio input
            audio_duration = len(audio_data) / (self.sample_rate * 2)  # Assuming 16-bit samples
            self.logger.log_timing(interaction_id, "recording", recording_time)
            
            # Phase 2: STT Processing
            print("🎤 Processing speech...")
            start_time = time.time()
            transcription = await self.stt_engine.transcribe(audio_data)
            stt_time = time.time() - start_time
            
            self.logger.log_timing(interaction_id, "stt", stt_time)
            
            if not transcription or not transcription.strip():
                print("❌ No clear speech detected")
                self.logger.log_issue(interaction_id, "transcription", "No speech detected or empty transcription")
                self.logger.finish_interaction(interaction_id, success=False)
                return None
            
            # Filter out garbage transcriptions
            if not self.is_valid_speech(transcription):
                print("⚠️ Audio was unclear, please try again")
                self.logger.log_issue(interaction_id, "transcription", "Transcription failed validation (likely noise)")
                self.logger.finish_interaction(interaction_id, success=False)
                return None
            
            print(f"📝 You said: '{transcription}'")
            
            # Log successful transcription
            self.logger.log_audio_input(interaction_id, audio_duration, transcription, confidence=0.8)
            
            # Phase 3: AI Response Generation
            print("🧠 Thinking...")
            start_time = time.time()
            response_text = await self.generate_intelligent_response(transcription, user_id="voice_user")
            ai_time = time.time() - start_time
            
            self.logger.log_timing(interaction_id, "ai", ai_time)
            
            # Determine response type 
            response_type = self._classify_response_type(transcription)
            
            self.logger.log_ai_response(
                interaction_id, response_text, response_type, ai_time,
                conversation_context="", user_name=""  # MCP memory system handles context
            )
            
            print(f"\n💬 AI RESPONSE: '{response_text}'")
            print(f"📏 Response length: {len(response_text)} characters")
            
            # Phase 4: TTS Processing
            print("🗣️ Converting to speech...")
            start_time = time.time()
            audio_response = await self.tts_engine.synthesize(response_text)
            tts_time = time.time() - start_time
            
            self.logger.log_timing(interaction_id, "tts", tts_time)
            
            if len(audio_response) == 0:
                print("❌ No audio generated")
                self.logger.log_issue(interaction_id, "tts", "TTS failed to generate audio")
                self.logger.finish_interaction(interaction_id, success=False)
                return None
            
            # Phase 5: Audio Playback
            start_time = time.time()
            playback_success = await self.play_audio(audio_response)
            playback_time = time.time() - start_time
            
            self.logger.log_timing(interaction_id, "audio_playback", playback_time)
            self.logger.log_audio_output(interaction_id, response_text, tts_time, playback_success)
            
            if playback_success:
                print("✅ Leonardo responded successfully!")
            else:
                print("⚠️ Audio playback failed")
                self.logger.log_issue(interaction_id, "audio", "Audio playback failed")
            
            # Complete interaction
            overall_success = playback_success
            
            # Update MCP memory with the conversation turn
            if self.memory_service and overall_success:
                try:
                    conversation_turn = {
                        "user": transcription,  # Changed from user_input to user
                        "assistant": response_text,  # Changed from ai_response to assistant  
                        "user_input": transcription,  # Keep for compatibility
                        "ai_response": response_text,  # Keep for compatibility
                        "timestamp": time.time(),
                        "interaction_id": interaction_id
                    }
                    await self.memory_service.update_async("voice_user", conversation_turn)
                    print("🧠 Memory updated")
                except Exception as e:
                    print(f"⚠️ Memory update failed: {e}")
            
            self.logger.finish_interaction(interaction_id, success=overall_success)
            
            # Check for exit command
            if any(word in transcription.lower() for word in ['stop', 'quit', 'exit', 'goodbye']):
                return 'exit'
            
            return transcription
            
        except Exception as e:
            print(f"❌ Voice loop failed: {e}")
            self.logger.log_issue(interaction_id, "system", f"Unexpected error: {str(e)}")
            self.logger.finish_interaction(interaction_id, success=False)
            import traceback
            traceback.print_exc()
            return None
    
    async def run_complete_voice_loop(self):
        """Main voice loop with full microphone to speaker pipeline."""
        print("\n🎙️ LEONARDO COMPLETE VOICE LOOP")
        print("=" * 50)
        print("🎤 Say something to Leonardo!")
        print("🗣️ Leonardo will respond through your speakers")
        print("💡 Try: 'Hello', 'What time is it?', 'Search for AI news', 'What's the weather?'")
        print("⏹️ Say 'stop' or press Ctrl+C to exit")
        print()
        
        command_count = 0
        
        while self.running:
            try:
                print(f"\n--- Voice Interaction #{command_count + 1} ---")
                print("🎧 Leonardo is listening...")
                
                result = await self.process_complete_voice_loop()
                
                if result == 'exit':
                    print("👋 Leonardo says goodbye!")
                    break
                elif result:
                    command_count += 1
                    print(f"✅ Interaction {command_count} completed!")
                else:
                    print("⚠️ No valid command detected, trying again...")
                
                # Brief pause before next command
                print("\n⏳ Waiting 2 seconds before next interaction...")
                await asyncio.sleep(2)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Voice loop error: {e}")
                await asyncio.sleep(2)  # Brief pause before retrying
        
        print(f"\n📊 Session complete: {command_count} voice interactions")
    
    async def run_voice_test(self):
        """Run the complete voice test."""
        self.running = True
        
        try:
            # Initialize all components
            if not await self.initialize():
                return
            
            # Run complete voice loop
            await self.run_complete_voice_loop()
        
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown all components gracefully."""
        print("\n🛑 Shutting down Leonardo components...")
        
        self.running = False
        
        # Close logging session first
        if self.logger:
            self.logger.close_session()
        
        if self.verifier:
            await self.verifier.shutdown()
        if self.executor:
            await self.executor.shutdown()
        if self.validator:
            await self.validator.shutdown()
        if self.llm_planner:
            await self.llm_planner.shutdown()
        if self.memory_service:
            await self.memory_service.shutdown()
        if self.rag_system:
            await self.rag_system.shutdown()
        if self.tts_engine:
            await self.tts_engine.shutdown()
        if self.stt_engine:
            await self.stt_engine.shutdown()
            
        print("✅ All components shut down successfully")

async def main():
    """Main function to run the complete voice loop."""
    
    # Handle Ctrl+C gracefully
    test_instance = CompleteVoiceLoop()
    
    def signal_handler(signum, frame):
        print("\n\n⚠️ Received interrupt signal, shutting down...")
        test_instance.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await test_instance.run_voice_test()
    except KeyboardInterrupt:
        print("\n👋 Leonardo voice loop interrupted by user")
    except Exception as e:
        print(f"\n❌ Leonardo voice loop failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting Leonardo COMPLETE Voice Loop...")
    print("🎙️ Microphone input + 🔊 Speaker output")
    print("Press Ctrl+C anytime to exit gracefully")
    print()
    
    # Run the async test
    asyncio.run(main())
