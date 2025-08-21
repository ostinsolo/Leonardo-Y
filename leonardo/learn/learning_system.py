"""
ART-based learning system with LoRA fine-tuning.
"""

import logging
from typing import Dict, Any, Optional

from ..config import LeonardoConfig
from .art_trainer import ARTTrainer
from .lora_adapter_loader import LoRAAdapterLoader


class LearningSystem:
    """Continuous learning with ART rewards and LoRA fine-tuning."""
    
    def __init__(self, config: LeonardoConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # ART trainer for RL-based learning
        self.art_trainer: Optional[ARTTrainer] = None
        
        # LoRA adapter loader for Colab-trained models
        self.lora_loader = LoRAAdapterLoader(config)
        
        # Command and synonym registries
        self.command_registry = {}
        self.synonym_registry = {}
    
    async def initialize(self) -> None:
        """Initialize learning system."""
        self.logger.info("🧑‍🎓 Initializing learning system...")
        
        # Initialize ART trainer if enabled
        if self.config.learning.enable_art_training:
            self.art_trainer = ARTTrainer(self.config)
            await self.art_trainer.initialize()
        
        # Initialize LoRA adapter loader
        await self.lora_loader.initialize()
        
        # Load existing registries
        await self._load_registries()
        
        self.logger.info("✅ Learning system initialized")
    
    async def shutdown(self) -> None:
        """Shutdown learning system."""
        self.logger.info("🛑 Shutting down learning system...")
        
        # Shutdown ART trainer
        if self.art_trainer:
            await self.art_trainer.shutdown()
        
        # Shutdown LoRA loader
        await self.lora_loader.shutdown()
        
        # Save registries
        await self._save_registries()
        
        self.logger.info("✅ Learning system shutdown")
    
    # LoRA Adapter Management (Colab Integration)
    
    async def list_lora_adapters(self) -> Dict[str, Dict]:
        """List all available LoRA adapters trained in Colab."""
        return self.lora_loader.list_available_adapters()
    
    async def load_lora_adapter(self, adapter_name: str) -> bool:
        """Load a specific LoRA adapter for inference."""
        return await self.lora_loader.load_adapter(adapter_name)
    
    async def install_colab_adapter(self, colab_path: str, adapter_name: str) -> bool:
        """Install a LoRA adapter downloaded from Colab training."""
        return await self.lora_loader.install_adapter_from_colab(colab_path, adapter_name)
    
    async def evaluate_lora_adapter(self, adapter_name: str) -> Dict[str, Any]:
        """Run evaluation tests on a LoRA adapter."""
        return await self.lora_loader.evaluate_adapter(adapter_name)
    
    def get_current_adapter_info(self) -> Optional[Dict]:
        """Get information about the currently loaded LoRA adapter."""
        return self.lora_loader.get_adapter_info()
    
    async def generate_with_lora(self, messages: list, max_length: int = 512) -> str:
        """Generate response using the loaded LoRA adapter."""
        return await self.lora_loader.generate_response(messages, max_length)
    
    async def record_interaction(self, transcription: str, plan, execution_result, verification_result) -> None:
        """Record interaction for learning."""
        try:
            # Record with ART trainer if available
            if self.art_trainer:
                await self.art_trainer.record_interaction(
                    transcription, plan, execution_result, verification_result
                )
            
            self.logger.debug("📊 Recorded interaction for learning")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to record interaction: {e}")
    
    async def register_command(self, command_id: str, description: str, tool: str, 
                              schema: Dict[str, Any], examples: list, 
                              permission_level: str) -> bool:
        """Register new command."""
        try:
            # Store command in registry
            command_def = {
                "id": command_id,
                "description": description,
                "tool": tool,
                "schema": schema,
                "examples": examples,
                "permission_level": permission_level,
                "enabled": False  # Start disabled for safety
            }
            
            self.command_registry[command_id] = command_def
            
            # TODO: Run smoke tests before enabling
            # TODO: Add to MCP interface
            
            self.logger.info(f"📝 Registered command: {command_id}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to register command: {e}")
            return False
    
    async def register_synonym(self, phrase: str, canonical: str, scope: str) -> bool:
        """Register new phrase synonym."""
        try:
            # Store synonym in lexicon
            if scope not in self.synonym_registry:
                self.synonym_registry[scope] = {}
            
            self.synonym_registry[scope][phrase.lower()] = canonical.lower()
            
            self.logger.info(f"📝 Registered synonym: '{phrase}' -> '{canonical}' (scope: {scope})")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to register synonym: {e}")
            return False
    
    async def _load_registries(self) -> None:
        """Load command and synonym registries from disk."""
        try:
            # TODO: Load from persistent storage
            self.logger.debug("📂 Loaded learning registries")
        except Exception as e:
            self.logger.error(f"❌ Failed to load registries: {e}")
    
    async def _save_registries(self) -> None:
        """Save command and synonym registries to disk."""
        try:
            # TODO: Save to persistent storage
            self.logger.debug("💾 Saved learning registries")
        except Exception as e:
            self.logger.error(f"❌ Failed to save registries: {e}")
    
    def get_learning_metrics(self) -> Dict[str, Any]:
        """Get current learning system metrics."""
        metrics = {
            "registered_commands": len(self.command_registry),
            "registered_synonyms": sum(len(synonyms) for synonyms in self.synonym_registry.values()),
            "art_training_enabled": self.art_trainer is not None
        }
        
        # Add ART trainer metrics if available
        if self.art_trainer:
            metrics.update(self.art_trainer.get_training_metrics())
        
        return metrics
    
    async def get_policy_suggestion(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Get policy suggestion from trained models."""
        if self.art_trainer:
            return await self.art_trainer.get_policy_suggestion(user_input)
        return None
    
    def resolve_synonym(self, phrase: str, scope: str = "global") -> str:
        """Resolve synonym to canonical form."""
        phrase_lower = phrase.lower()
        
        # Check specific scope first
        if scope in self.synonym_registry and phrase_lower in self.synonym_registry[scope]:
            return self.synonym_registry[scope][phrase_lower]
        
        # Check global scope as fallback
        if scope != "global" and "global" in self.synonym_registry:
            if phrase_lower in self.synonym_registry["global"]:
                return self.synonym_registry["global"][phrase_lower]
        
        # Return original if no synonym found
        return phrase
    
    def is_command_enabled(self, command_id: str) -> bool:
        """Check if a command is enabled."""
        if command_id in self.command_registry:
            return self.command_registry[command_id].get("enabled", False)
        return False
    
    async def enable_command(self, command_id: str) -> bool:
        """Enable a command after validation."""
        try:
            if command_id in self.command_registry:
                # TODO: Run final validation/smoke tests
                self.command_registry[command_id]["enabled"] = True
                self.logger.info(f"✅ Enabled command: {command_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"❌ Failed to enable command {command_id}: {e}")
            return False

