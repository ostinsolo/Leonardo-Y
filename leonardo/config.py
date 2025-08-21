"""
Configuration management for Leonardo.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import toml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class AudioConfig(BaseModel):
    """Audio processing configuration."""
    
    sample_rate: int = Field(default=16000, description="Audio sample rate")
    chunk_size: int = Field(default=1024, description="Audio chunk size")
    channels: int = Field(default=1, description="Number of audio channels")
    vad_aggressiveness: int = Field(default=2, description="VAD aggressiveness (0-3)")
    enable_barge_in: bool = Field(default=True, description="Enable barge-in interruption")


class STTConfig(BaseModel):
    """Speech-to-text configuration."""
    
    model_size: str = Field(default="base", description="Whisper model size")
    device: str = Field(default="auto", description="Compute device (auto/cpu/cuda)")
    compute_type: str = Field(default="float16", description="Compute precision")
    language: Optional[str] = Field(default=None, description="Force language (auto-detect if None)")
    beam_size: int = Field(default=5, description="Beam search size")


class LLMConfig(BaseModel):
    """Large Language Model configuration using Qwen2.5."""
    
    # Qwen2.5 model specifications
    model_name: str = Field(default="Qwen/Qwen2.5-3B-Instruct", description="Qwen2.5 model name")
    model_path: Optional[str] = Field(default=None, description="Local model path if downloaded")
    model_cache_dir: str = Field(default="./leonardo_model_cache", description="Local model cache directory")
    max_tokens: int = Field(default=2048, description="Maximum generation tokens (Qwen2.5 supports up to 32K)")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    top_p: float = Field(default=0.9, description="Top-p sampling")
    device: str = Field(default="cpu", description="Compute device (auto/cpu/cuda) - CPU for Intel Mac stability")
    offload_folder: str = Field(default="./leonardo_model_offload", description="Disk offload folder for memory management")
    
    # Unsloth LoRA configuration
    enable_lora: bool = Field(default=True, description="Enable Unsloth LoRA adapters")
    lora_rank: int = Field(default=16, description="LoRA rank")
    lora_alpha: int = Field(default=32, description="LoRA alpha parameter")
    lora_dropout: float = Field(default=0.1, description="LoRA dropout")
    
    # Grammar constraints for tool calls
    enable_json_constraints: bool = Field(default=True, description="Enable JSON schema constraints")
    grammar_file: Optional[Path] = Field(default=None, description="JSON grammar constraints file")
    
    # Reasoning and tool use capabilities
    enable_tool_use: bool = Field(default=True, description="Enable tool use reasoning")
    enable_chain_of_thought: bool = Field(default=True, description="Enable chain-of-thought reasoning")


class ValidationConfig(BaseModel):
    """Validation system configuration."""
    
    enable_schema_validation: bool = Field(default=True, description="Enable JSON schema validation")
    enable_policy_engine: bool = Field(default=True, description="Enable OPA/Cedar policies")
    enable_static_analysis: bool = Field(default=True, description="Enable script static analysis")
    enable_llm_validator: bool = Field(default=True, description="Enable LLM-based validation")
    max_retry_attempts: int = Field(default=2, description="Maximum retry attempts")


class SandboxConfig(BaseModel):
    """Sandbox execution configuration."""
    
    enable_mac_control: bool = Field(default=True, description="Enable macOS automation")
    enable_web_research: bool = Field(default=True, description="Enable web research")
    enable_file_operations: bool = Field(default=True, description="Enable file operations")
    default_timeout: int = Field(default=30, description="Default operation timeout (seconds)")
    max_concurrent_ops: int = Field(default=5, description="Maximum concurrent operations")


class RAGConfig(BaseModel):
    """Retrieval-Augmented Generation configuration."""
    
    vector_db_type: str = Field(default="chroma", description="Vector database type (chroma/faiss)")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", description="Sentence transformer model")
    chunk_size: int = Field(default=1000, description="Document chunk size")
    chunk_overlap: int = Field(default=200, description="Chunk overlap")
    max_retrieval_results: int = Field(default=10, description="Maximum retrieval results")


class TTSConfig(BaseModel):
    """Text-to-speech configuration using Microsoft Edge TTS."""
    
    engine: str = Field(default="edge", description="TTS engine (edge/piper/avspeech)")
    # Microsoft Edge TTS voices
    voice: str = Field(default="en-US-JennyNeural", description="Edge TTS voice (e.g., en-US-JennyNeural)")
    language: str = Field(default="en-US", description="Voice language")
    speed: str = Field(default="+0%", description="Speech speed (e.g., +20%, -10%)")
    pitch: str = Field(default="+0Hz", description="Voice pitch (e.g., +50Hz, -20Hz)")
    volume: str = Field(default="+0%", description="Voice volume (e.g., +10%, -5%)")
    enable_earcons: bool = Field(default=True, description="Enable UI sound effects")
    
    # Fallback options
    fallback_engine: str = Field(default="piper", description="Fallback TTS engine")
    fallback_voice: str = Field(default="en_US-lessac-medium", description="Fallback voice")


class LearningConfig(BaseModel):
    """Learning system configuration."""
    
    enable_art_training: bool = Field(default=True, description="Enable ART-based learning")
    reward_threshold: float = Field(default=0.8, description="Reward threshold for promotion")
    evaluation_tasks_path: Path = Field(default=Path("leonardo/eval/golden_tasks.yaml"))
    canary_percentage: float = Field(default=0.1, description="Canary deployment percentage")


class MemoryConfig(BaseModel):
    """Memory system configuration."""
    
    max_recent_turns: int = Field(default=8, description="Maximum recent conversation turns to keep")
    summary_target_tokens: int = Field(default=200, description="Target tokens for conversation summaries")
    enable_vector_search: bool = Field(default=True, description="Enable vector-based episodic search")
    retention_days: int = Field(default=30, description="Days to retain memory data")
    store_type: str = Field(default="sqlite", description="Storage backend (sqlite/jsonl)")


class LeonardoConfig(BaseSettings):
    """Main Leonardo configuration."""
    
    # Core settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    data_dir: Path = Field(default=Path("~/.leonardo").expanduser(), description="Data directory")
    
    # Component configurations
    audio: AudioConfig = Field(default_factory=AudioConfig)
    stt: STTConfig = Field(default_factory=STTConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    learning: LearningConfig = Field(default_factory=LearningConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    
    # Risk tiers and policies
    risk_tiers: Dict[str, List[str]] = Field(default_factory=lambda: {
        "safe": ["search_web", "summarize", "calculate"],
        "review": ["files_read", "applescript_info"],
        "confirm": ["files_write", "email_send", "calendar_create"],
        "owner_root": ["system_control", "install_software", "network_config"]
    })
    
    # Domain allowlists
    web_allowlist: List[str] = Field(default_factory=lambda: [
        "*.wikipedia.org", "*.stackoverflow.com", "*.github.com",
        "*.python.org", "*.mozilla.org"
    ])
    
    class Config:
        env_prefix = "LEONARDO_"
        env_file = ".env"
        case_sensitive = False
    
    @classmethod
    def load_from_file(cls, config_path: Path) -> "LeonardoConfig":
        """Load configuration from TOML file."""
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_data = toml.load(f)
            return cls(**config_data)
        return cls()
    
    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to TOML file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            toml.dump(self.model_dump(), f)
    
    def setup_directories(self) -> None:
        """Create necessary directories."""
        directories = [
            self.data_dir,
            self.data_dir / "logs",
            self.data_dir / "cache",
            self.data_dir / "models",
            self.data_dir / "registry",
            self.data_dir / "policies",
            self.data_dir / "memory",
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
