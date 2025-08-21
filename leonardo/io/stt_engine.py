"""
Speech-to-Text engine using Faster-Whisper.
"""

import logging
import asyncio
from typing import Optional
import tempfile
import os

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

from ..config import LeonardoConfig


class STTEngine:
    """Speech-to-Text using Faster-Whisper."""
    
    def __init__(self, config: LeonardoConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model: Optional[WhisperModel] = None
    
    async def initialize(self) -> None:
        """Initialize STT model."""
        if WhisperModel is None:
            raise RuntimeError(
                "Faster-Whisper not available. Install with: pip install faster-whisper"
            )
        
        self.logger.info(f"🎤 Loading Whisper model: {self.config.stt.model_size}")
        
        # Load model in executor to avoid blocking
        loop = asyncio.get_event_loop()
        self.model = await loop.run_in_executor(
            None,
            self._load_model
        )
        
        self.logger.info("✅ STT engine initialized")
    
    def _load_model(self) -> WhisperModel:
        """Load Whisper model (runs in executor)."""
        return WhisperModel(
            self.config.stt.model_size,
            device=self.config.stt.device,
            compute_type=self.config.stt.compute_type
        )
    
    async def shutdown(self) -> None:
        """Shutdown STT engine."""
        self.model = None
        self.logger.info("✅ STT engine shutdown")
    
    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio bytes to text."""
        if not self.model:
            return ""
        
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(self._create_wav_header(audio_data))
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            try:
                # Run transcription in executor
                loop = asyncio.get_event_loop()
                segments = await loop.run_in_executor(
                    None,
                    self._transcribe_file,
                    temp_path
                )
                
                # Combine segments into single text
                text = " ".join(segment.text.strip() for segment in segments)
                
                # LOG THE RAW TRANSCRIPTION
                print(f"\n🎤 STT OUTPUT: '{text.strip()}'")
                if len(text.strip()) > 100:
                    print(f"⚠️ Very long transcription ({len(text)} chars) - possible noise pickup")
                
                return text.strip()
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        except Exception as e:
            self.logger.error(f"❌ Transcription error: {e}")
            return ""
    
    def _transcribe_file(self, file_path: str):
        """Transcribe audio file (runs in executor)."""
        segments, _ = self.model.transcribe(
            file_path,
            beam_size=self.config.stt.beam_size,
            language=self.config.stt.language
        )
        return list(segments)
    
    def _create_wav_header(self, audio_data: bytes) -> bytes:
        """Create WAV header for raw audio data."""
        sample_rate = self.config.audio.sample_rate
        channels = self.config.audio.channels
        data_length = len(audio_data)
        
        # WAV header (44 bytes)
        header = b'RIFF'
        header += (data_length + 36).to_bytes(4, 'little')
        header += b'WAVE'
        header += b'fmt '
        header += (16).to_bytes(4, 'little')  # PCM format
        header += (1).to_bytes(2, 'little')   # Audio format
        header += channels.to_bytes(2, 'little')
        header += sample_rate.to_bytes(4, 'little')
        header += (sample_rate * channels * 2).to_bytes(4, 'little')  # Byte rate
        header += (channels * 2).to_bytes(2, 'little')  # Block align
        header += (16).to_bytes(2, 'little')  # Bits per sample
        header += b'data'
        header += data_length.to_bytes(4, 'little')
        
        return header
