"""
Voice Activity Detection processor using WebRTC VAD.
"""

import logging
from typing import Optional

try:
    import webrtcvad
except ImportError:
    webrtcvad = None

from ..config import LeonardoConfig


class VADProcessor:
    """Voice Activity Detection using WebRTC VAD."""
    
    def __init__(self, config: LeonardoConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.vad: Optional[webrtcvad.Vad] = None
    
    async def initialize(self) -> None:
        """Initialize VAD processor."""
        if webrtcvad is None:
            raise RuntimeError(
                "WebRTC VAD not available. Install with: pip install webrtcvad"
            )
        
        self.vad = webrtcvad.Vad(self.config.audio.vad_aggressiveness)
        self.logger.info("✅ VAD processor initialized")
    
    async def shutdown(self) -> None:
        """Shutdown VAD processor."""
        self.vad = None
        self.logger.info("✅ VAD processor shutdown")
    
    async def has_speech(self, audio_data: bytes) -> bool:
        """Check if audio contains speech."""
        if not self.vad:
            return False
        
        try:
            # WebRTC VAD requires specific frame lengths
            frame_length = int(self.config.audio.sample_rate * 0.01)  # 10ms frames
            if len(audio_data) < frame_length * 2:  # 16-bit samples
                return False
            
            # Take first 10ms frame
            frame = audio_data[:frame_length * 2]
            return self.vad.is_speech(frame, self.config.audio.sample_rate)
            
        except Exception as e:
            self.logger.error(f"❌ VAD error: {e}")
            return False
