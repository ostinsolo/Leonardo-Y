"""
Text-to-Speech engine using Microsoft Edge TTS with multiple backend support.
"""

import logging
import asyncio
from typing import Optional, Union
import tempfile
import os

# Microsoft Edge TTS integration
try:
    import edge_tts
    from edge_tts import VoicesManager
except ImportError:
    edge_tts = None
    print("Edge TTS not available - install with: pip install git+https://github.com/microsoft/Edge-TTS.git")

from ..config import LeonardoConfig


class TTSEngine:
    """Text-to-Speech with multiple backend support."""
    
    def __init__(self, config: LeonardoConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.engine = config.tts.engine
    
    async def initialize(self) -> None:
        """Initialize TTS engine."""
        self.logger.info(f"🗣️ Initializing TTS engine: {self.engine}")
        
        if self.engine == "edge":
            await self._check_edge_tts()
        elif self.engine == "piper":
            await self._check_piper()
        elif self.engine == "avspeech":
            await self._check_avspeech()
        else:
            raise ValueError(f"Unsupported TTS engine: {self.engine}")
        
        self.logger.info("✅ TTS engine initialized")
    
    async def shutdown(self) -> None:
        """Shutdown TTS engine."""
        self.logger.info("✅ TTS engine shutdown")
    
    async def synthesize(self, text: str) -> bytes:
        """Synthesize speech from text."""
        if not text.strip():
            return b''
        
        # LOG EXACTLY WHAT WE'RE TRYING TO SYNTHESIZE
        print(f"\n🗣️ TTS INPUT: '{text}'")
        print(f"📝 Length: {len(text)} characters")
        
        try:
            if self.engine == "edge":
                return await self._synthesize_edge_tts(text)
            elif self.engine == "piper":
                return await self._synthesize_piper(text)
            elif self.engine == "avspeech":
                return await self._synthesize_avspeech(text)
            else:
                raise ValueError(f"Unsupported engine: {self.engine}")
        
        except Exception as e:
            self.logger.error(f"❌ TTS synthesis error: {e}")
            return b''
    
    async def _check_edge_tts(self) -> None:
        """Check if Edge TTS is available."""
        if edge_tts is None:
            raise RuntimeError(
                "Edge TTS not available. Install with: pip install edge-tts"
            )
    
    def _clean_text_for_speech(self, text: str) -> str:
        """Clean text for speech - remove technical details and unwanted content."""
        import re
        
        # Remove common technical patterns
        cleaned = text
        
        # Remove HTTP URLs and technical paths
        cleaned = re.sub(r'https?://[^\s]+', '', cleaned)
        cleaned = re.sub(r'/[/\w\-.]+', '', cleaned)
        
        # Remove XML/HTML-like tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # Remove technical percentage indicators
        cleaned = re.sub(r'\+?\d+%', '', cleaned)
        cleaned = re.sub(r'\+?\d+Hz', '', cleaned)
        
        # Remove file extensions and technical terms
        cleaned = re.sub(r'\.[a-z]{2,4}\b', '', cleaned)
        cleaned = re.sub(r'\bxml:lang\b', '', cleaned)
        cleaned = re.sub(r'\bversion\b', '', cleaned)
        cleaned = re.sub(r'\bxmlns\b', '', cleaned)
        cleaned = re.sub(r'\bprosody\b', '', cleaned)
        
        # Remove extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()

    async def _synthesize_edge_tts(self, text: str) -> bytes:
        """Synthesize speech using Microsoft Edge TTS with plain text."""
        try:
            # Clean text before synthesis
            clean_text = self._clean_text_for_speech(text)
            
            print(f"🧹 CLEANED TEXT: '{clean_text}'")
            
            # Configure Edge TTS communication with PLAIN TEXT (no SSML)
            voice = self.config.tts.voice
            
            # Create communication object with plain text
            communicate = edge_tts.Communicate(clean_text, voice)
            
            # Generate audio
            audio_data = b''
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            return audio_data
            
        except Exception as e:
            self.logger.error(f"❌ Edge TTS synthesis failed: {e}")
            # Try fallback without SSML
            try:
                communicate = edge_tts.Communicate(text, self.config.tts.voice)
                audio_data = b''
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                return audio_data
            except Exception as fallback_e:
                self.logger.error(f"❌ Edge TTS fallback failed: {fallback_e}")
                return b''
    
    async def _check_piper(self) -> None:
        """Check if Piper TTS is available."""
        try:
            # Check if piper command exists
            result = await asyncio.create_subprocess_exec(
                "piper", "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            if result.returncode != 0:
                raise RuntimeError("Piper TTS not found in PATH")
                
        except FileNotFoundError:
            raise RuntimeError(
                "Piper TTS not found. Install with: pip install piper-tts"
            )
    
    async def _check_avspeech(self) -> None:
        """Check if AVSpeech (macOS) is available."""
        import sys
        if sys.platform != "darwin":
            raise RuntimeError("AVSpeech only available on macOS")
        
        try:
            import objc
        except ImportError:
            raise RuntimeError(
                "PyObjC not found. Install with: pip install pyobjc"
            )
    
    async def _synthesize_piper(self, text: str) -> bytes:
        """Synthesize speech using Piper TTS."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Run piper command
            cmd = [
                "piper",
                "--model", self.config.tts.voice,
                "--output_file", temp_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=text.encode())
            
            if process.returncode != 0:
                raise RuntimeError(f"Piper failed: {stderr.decode()}")
            
            # Read generated audio
            with open(temp_path, 'rb') as f:
                # Skip WAV header (44 bytes) to get raw PCM data
                f.seek(44)
                audio_data = f.read()
            
            return audio_data
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def _synthesize_avspeech(self, text: str) -> bytes:
        """Synthesize speech using macOS AVSpeech."""
        # This is a placeholder - full implementation would use PyObjC
        # to interface with AVSpeechSynthesizer
        
        # For now, use macOS 'say' command as fallback
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Use macOS 'say' command
            cmd = [
                "say",
                "-o", temp_path,
                "-r", str(int(200 * self.config.tts.speed)),  # Words per minute
                text
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError("macOS 'say' command failed")
            
            # Convert AIFF to raw PCM using ffmpeg (if available)
            return await self._convert_audio_to_pcm(temp_path)
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def _convert_audio_to_pcm(self, input_path: str) -> bytes:
        """Convert audio file to PCM format."""
        with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            # Use ffmpeg to convert to raw PCM
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-f", "s16le",
                "-ar", str(self.config.audio.sample_rate),
                "-ac", str(self.config.audio.channels),
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode == 0:
                with open(output_path, 'rb') as f:
                    return f.read()
            else:
                # Fallback: just return empty bytes
                self.logger.warning("Audio conversion failed, returning silence")
                return b''
                
        except FileNotFoundError:
            self.logger.warning("ffmpeg not found, returning silence")
            return b''
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
