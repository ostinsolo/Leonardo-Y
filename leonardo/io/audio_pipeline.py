"""
Audio pipeline for Leonardo using Pipecat for real-time conversational orchestration.
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional
from dataclasses import dataclass

# Pipecat imports for real-time conversational pipelines
try:
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineTask
    from pipecat.transports.base_transport import BaseTransport
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
    from pipecat.frames.frames import Frame, AudioRawFrame, TextFrame
    # Note: We use Edge-TTS and Faster-Whisper instead of Cartesia/Deepgram services
    PIPECAT_AVAILABLE = True
except ImportError as e:
    # Fallback imports if Pipecat not available
    Pipeline = None
    BaseTransport = None
    FrameProcessor = None
    PIPECAT_AVAILABLE = False
    print(f"⚠️ Pipecat import issue: {e}")

from ..config import LeonardoConfig
from .stt_engine import STTEngine
from .tts_engine import TTSEngine


@dataclass
class AudioChunk:
    """Audio chunk with metadata."""
    data: bytes
    timestamp: float
    has_speech: bool
    is_complete_utterance: bool


class LeonardoProcessor(FrameProcessor if PIPECAT_AVAILABLE else object):
    """Custom Pipecat processor for Leonardo's audio processing."""
    
    def __init__(self, stt_engine, tts_engine, callback=None):
        if PIPECAT_AVAILABLE:
            super().__init__()
        self.stt_engine = stt_engine
        self.tts_engine = tts_engine  
        self.callback = callback
        self.logger = logging.getLogger(__name__)
    
    async def process_frame(self, frame: Frame, direction: FrameDirection) -> Optional[Frame]:
        """Process frames through Leonardo's pipeline."""
        if not PIPECAT_AVAILABLE:
            return None
            
        if isinstance(frame, AudioRawFrame):
            # Handle audio input through STT
            try:
                # Convert audio frame to text
                audio_data = frame.audio
                text = await self.stt_engine.transcribe_bytes(audio_data)
                
                if text and text.strip():
                    self.logger.debug(f"🎤 Pipecat STT: {text}")
                    
                    # Callback to Leonardo's main loop
                    if self.callback:
                        await self.callback(text)
                    
                    # Create text frame for pipeline
                    return TextFrame(text=text)
                    
            except Exception as e:
                self.logger.error(f"❌ Pipecat STT error: {e}")
                
        elif isinstance(frame, TextFrame):
            # Handle text for TTS processing
            self.logger.debug(f"📝 Pipecat Text: {frame.text}")
        
        return frame


class AudioPipeline:
    """
    Real-time audio processing pipeline with VAD, STT, and TTS.
    
    Features:
    - Voice Activity Detection (VAD)
    - Real-time streaming
    - Barge-in interruption
    - Duplex audio (simultaneous input/output)
    """
    
    def __init__(self, config: LeonardoConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Audio configuration
        self.sample_rate = config.audio.sample_rate
        self.chunk_size = config.audio.chunk_size
        self.channels = config.audio.channels
        
        # Components
        self.vad_processor: Optional[VADProcessor] = None
        self.stt_engine: Optional[STTEngine] = None
        self.tts_engine: Optional[TTSEngine] = None
        
        # Pipecat integration
        self.pipecat_pipeline = None
        self.pipecat_runner = None
        self.leonardo_processor = None
        
        # PyAudio stream
        self._audio = None
        self._input_stream = None
        self._output_stream = None
        self._streaming = False
        
        # Barge-in support
        self._tts_playing = False
        self._interrupt_tts = False
    
    def initialize_pipecat_pipeline(self, voice_callback=None):
        """Initialize Pipecat pipeline for real-time processing."""
        if not PIPECAT_AVAILABLE:
            self.logger.warning("⚠️ Pipecat not available - using fallback audio processing")
            return False
        
        try:
            # Create Leonardo processor
            self.leonardo_processor = LeonardoProcessor(
                stt_engine=self.stt_engine,
                tts_engine=self.tts_engine,
                callback=voice_callback
            )
            
            # Create Pipecat pipeline
            processors = [self.leonardo_processor]
            self.pipecat_pipeline = Pipeline(processors)
            
            # Create runner
            self.pipecat_runner = PipelineRunner()
            
            self.logger.info("✅ Pipecat pipeline initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Pipecat pipeline: {e}")
            return False
    
    async def initialize(self) -> None:
        """Initialize the audio pipeline."""
        if pyaudio is None:
            raise RuntimeError(
                "PyAudio not available. Install with: pip install pyaudio"
            )
        
        self.logger.info("🎙️ Initializing audio pipeline...")
        
        # Initialize PyAudio
        self._audio = pyaudio.PyAudio()
        
        # Check for available devices
        self._check_audio_devices()
        
        # Initialize components
        self.vad_processor = VADProcessor(self.config)
        self.stt_engine = STTEngine(self.config)
        self.tts_engine = TTSEngine(self.config)
        
        await self.vad_processor.initialize()
        await self.stt_engine.initialize()
        await self.tts_engine.initialize()
        
        self.logger.info("✅ Audio pipeline initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the audio pipeline."""
        self.logger.info("🛑 Shutting down audio pipeline...")
        
        await self.stop_streaming()
        
        # Shutdown components
        if self.tts_engine:
            await self.tts_engine.shutdown()
        if self.stt_engine:
            await self.stt_engine.shutdown()
        if self.vad_processor:
            await self.vad_processor.shutdown()
        
        # Close PyAudio
        if self._audio:
            self._audio.terminate()
        
        self.logger.info("✅ Audio pipeline shutdown complete")
    
    def _check_audio_devices(self) -> None:
        """Check available audio devices."""
        info = self._audio.get_host_api_info_by_index(0)
        device_count = info.get('deviceCount')
        
        self.logger.info(f"Found {device_count} audio devices")
        
        # Find default input/output devices
        default_input = self._audio.get_default_input_device_info()
        default_output = self._audio.get_default_output_device_info()
        
        self.logger.info(f"Input device: {default_input['name']}")
        self.logger.info(f"Output device: {default_output['name']}")
    
    async def start_streaming(self) -> AsyncGenerator[AudioChunk, None]:
        """Start audio streaming and yield audio chunks with speech."""
        if self._streaming:
            raise RuntimeError("Audio streaming already started")
        
        self.logger.info("🎙️ Starting audio streaming...")
        self._streaming = True
        
        try:
            # Start input stream
            self._input_stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=None
            )
            
            # Start output stream for TTS
            self._output_stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=None
            )
            
            self.logger.info("✅ Audio streaming started")
            
            # Audio buffer for building utterances
            audio_buffer = []
            silence_frames = 0
            max_silence_frames = int(1.5 * self.sample_rate / self.chunk_size)  # 1.5s silence
            
            while self._streaming:
                try:
                    # Read audio chunk
                    audio_data = self._input_stream.read(
                        self.chunk_size, 
                        exception_on_overflow=False
                    )
                    
                    # Convert to numpy array
                    audio_np = np.frombuffer(audio_data, dtype=np.int16)
                    
                    # Check for speech using VAD
                    has_speech = await self.vad_processor.has_speech(audio_data)
                    
                    # Handle barge-in during TTS
                    if has_speech and self._tts_playing:
                        self.logger.info("🚨 Barge-in detected, interrupting TTS")
                        self._interrupt_tts = True
                        await self._stop_current_tts()
                    
                    if has_speech:
                        # Add to buffer and reset silence counter
                        audio_buffer.append(audio_data)
                        silence_frames = 0
                        self.logger.debug("🎤 Speech detected")
                    else:
                        # Increment silence counter
                        silence_frames += 1
                        
                        # If we have buffered audio and hit silence threshold
                        if audio_buffer and silence_frames >= max_silence_frames:
                            # Yield complete utterance
                            complete_audio = b''.join(audio_buffer)
                            
                            chunk = AudioChunk(
                                data=complete_audio,
                                timestamp=asyncio.get_event_loop().time(),
                                has_speech=True,
                                is_complete_utterance=True
                            )
                            
                            self.logger.info("🎯 Complete utterance detected")
                            yield chunk
                            
                            # Clear buffer
                            audio_buffer.clear()
                            silence_frames = 0
                
                except Exception as e:
                    self.logger.error(f"❌ Error reading audio: {e}")
                    break
                
                # Small delay to prevent CPU overload
                await asyncio.sleep(0.001)
        
        finally:
            await self.stop_streaming()
    
    async def stop_streaming(self) -> None:
        """Stop audio streaming."""
        if not self._streaming:
            return
        
        self.logger.info("🛑 Stopping audio streaming...")
        self._streaming = False
        
        # Close streams
        if self._input_stream:
            self._input_stream.stop_stream()
            self._input_stream.close()
            self._input_stream = None
        
        if self._output_stream:
            self._output_stream.stop_stream()
            self._output_stream.close()
            self._output_stream = None
        
        self.logger.info("✅ Audio streaming stopped")
    
    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio data to text."""
        try:
            if not self.stt_engine:
                raise RuntimeError("STT engine not initialized")
            
            transcription = await self.stt_engine.transcribe(audio_data)
            
            if transcription.strip():
                self.logger.info(f"📝 Transcription: {transcription}")
            
            return transcription
            
        except Exception as e:
            self.logger.error(f"❌ Transcription error: {e}")
            return ""
    
    async def speak(self, text: str) -> None:
        """Convert text to speech and play it."""
        try:
            if not self.tts_engine:
                raise RuntimeError("TTS engine not initialized")
            
            self.logger.info(f"🗣️ Speaking: {text}")
            self._tts_playing = True
            self._interrupt_tts = False
            
            # Generate audio
            audio_data = await self.tts_engine.synthesize(text)
            
            # Play audio (with interruption support)
            await self._play_audio(audio_data)
            
        except Exception as e:
            self.logger.error(f"❌ TTS error: {e}")
        finally:
            self._tts_playing = False
            self._interrupt_tts = False
    
    async def _play_audio(self, audio_data: bytes) -> None:
        """Play audio data with interruption support."""
        if not self._output_stream or not audio_data:
            return
        
        # Split audio into chunks for interruption support
        chunk_size = self.chunk_size * 2  # 16-bit samples
        chunks = [
            audio_data[i:i + chunk_size] 
            for i in range(0, len(audio_data), chunk_size)
        ]
        
        for chunk in chunks:
            if self._interrupt_tts:
                self.logger.info("🚨 TTS interrupted")
                break
            
            if len(chunk) < chunk_size:
                # Pad last chunk with silence
                chunk += b'\x00' * (chunk_size - len(chunk))
            
            self._output_stream.write(chunk)
            
            # Small delay to allow interruption
            await asyncio.sleep(0.01)
    
    async def _stop_current_tts(self) -> None:
        """Stop currently playing TTS."""
        self._interrupt_tts = True
        
        # Clear output buffer
        if self._output_stream:
            # Write silence to clear any remaining audio
            silence = b'\x00' * (self.chunk_size * 2)
            for _ in range(5):  # Clear ~100ms of audio
                try:
                    self._output_stream.write(silence)
                except:
                    break
    
    def is_streaming(self) -> bool:
        """Check if audio streaming is active."""
        return self._streaming
    
    def is_speaking(self) -> bool:
        """Check if TTS is currently playing."""
        return self._tts_playing
