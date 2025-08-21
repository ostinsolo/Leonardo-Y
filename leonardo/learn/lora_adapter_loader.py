"""
Leonardo LoRA Adapter Loader
Loads LoRA adapters trained in Colab back into Leonardo for inference.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import torch

from ..config import LeonardoConfig

# Try imports - graceful handling for Apple Silicon
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False
    print("PEFT not available - LoRA adapter loading disabled")

try:
    from unsloth import FastLanguageModel
    UNSLOTH_AVAILABLE = True
except (ImportError, NotImplementedError):
    UNSLOTH_AVAILABLE = False
    print("Unsloth not available on this platform")


class LoRAAdapterLoader:
    """Manages loading and switching between LoRA adapters trained in Colab."""
    
    def __init__(self, config: LeonardoConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.registry_path = Path("leonardo/learn/lora_registry")
        self.registry_path.mkdir(parents=True, exist_ok=True)
        
        self.current_adapter: Optional[str] = None
        self.base_model = None
        self.tokenizer = None
        self.model = None
        
    async def initialize(self) -> None:
        """Initialize the adapter loader."""
        self.logger.info("🧑‍🎓 Initializing LoRA adapter loader...")
        
        if not PEFT_AVAILABLE:
            self.logger.warning("⚠️ PEFT not available - LoRA loading disabled")
            return
        
        # Load base model for adapter loading
        base_model_name = self.config.llm.model_name
        
        try:
            self.logger.info(f"Loading base model: {base_model_name}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(base_model_name)
            
            # Load base model (CPU is fine for inference, just slower)
            self.base_model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                device_map="auto",  # Will use CPU on Apple Silicon
                torch_dtype="auto"
            )
            
            self.logger.info("✅ Base model loaded for adapter integration")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load base model: {e}")
            self.base_model = None
    
    def list_available_adapters(self) -> Dict[str, Dict]:
        """List all available LoRA adapters in the registry."""
        adapters = {}
        
        for adapter_path in self.registry_path.iterdir():
            if adapter_path.is_dir():
                metadata_file = adapter_path / "leonardo_metadata.json"
                
                if metadata_file.exists():
                    try:
                        with open(metadata_file) as f:
                            metadata = json.load(f)
                        adapters[adapter_path.name] = metadata
                    except Exception as e:
                        self.logger.warning(f"⚠️ Failed to read metadata for {adapter_path.name}: {e}")
                        
        return adapters
    
    async def load_adapter(self, adapter_name: str) -> bool:
        """Load a specific LoRA adapter."""
        if not PEFT_AVAILABLE or not self.base_model:
            self.logger.error("❌ Cannot load adapter - base requirements not met")
            return False
        
        adapter_path = self.registry_path / adapter_name
        
        if not adapter_path.exists():
            self.logger.error(f"❌ Adapter not found: {adapter_name}")
            return False
        
        try:
            self.logger.info(f"🔄 Loading LoRA adapter: {adapter_name}")
            
            # Load adapter with PEFT
            self.model = PeftModel.from_pretrained(
                self.base_model, 
                str(adapter_path)
            )
            
            self.current_adapter = adapter_name
            
            # Load metadata
            metadata_file = adapter_path / "leonardo_metadata.json"
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                
                self.logger.info(f"✅ Loaded adapter: {adapter_name}")
                self.logger.info(f"  • Base model: {metadata.get('base_model', 'Unknown')}")
                self.logger.info(f"  • Training date: {metadata.get('training_date', 'Unknown')}")
                self.logger.info(f"  • LoRA rank: {metadata.get('lora_rank', 'Unknown')}")
                self.logger.info(f"  • Training steps: {metadata.get('training_steps', 'Unknown')}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load adapter {adapter_name}: {e}")
            return False
    
    async def generate_response(self, messages: list, max_length: int = 512) -> str:
        """Generate response using the loaded LoRA adapter."""
        if not self.model or not self.tokenizer:
            return "LoRA adapter not loaded"
        
        try:
            # Format messages with chat template
            prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # Tokenize
            inputs = self.tokenizer(
                prompt, 
                return_tensors="pt",
                truncation=True,
                max_length=2048
            )
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.1
                )
            
            # Decode response
            response = self.tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:], 
                skip_special_tokens=True
            )
            
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"❌ Generation failed: {e}")
            return f"Generation error: {e}"
    
    def get_adapter_info(self) -> Optional[Dict]:
        """Get information about the currently loaded adapter."""
        if not self.current_adapter:
            return None
        
        metadata_file = self.registry_path / self.current_adapter / "leonardo_metadata.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file) as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to read adapter info: {e}")
        
        return {"adapter_name": self.current_adapter, "metadata": "unavailable"}
    
    async def install_adapter_from_colab(self, colab_adapter_path: str, adapter_name: str) -> bool:
        """Install a LoRA adapter downloaded from Colab training."""
        source_path = Path(colab_adapter_path)
        target_path = self.registry_path / adapter_name
        
        if not source_path.exists():
            self.logger.error(f"❌ Colab adapter not found: {colab_adapter_path}")
            return False
        
        try:
            self.logger.info(f"📥 Installing Colab adapter: {adapter_name}")
            
            # Copy adapter files
            import shutil
            if target_path.exists():
                shutil.rmtree(target_path)
            
            shutil.copytree(source_path, target_path)
            
            # Verify installation
            required_files = ["adapter_config.json", "adapter_model.safetensors"]
            for file_name in required_files:
                if not (target_path / file_name).exists():
                    self.logger.warning(f"⚠️ Missing file: {file_name}")
            
            self.logger.info(f"✅ Colab adapter installed: {adapter_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to install Colab adapter: {e}")
            return False
    
    async def evaluate_adapter(self, adapter_name: str) -> Dict[str, Any]:
        """Run evaluation tests on a LoRA adapter."""
        self.logger.info(f"🧪 Evaluating adapter: {adapter_name}")
        
        # Load adapter
        if not await self.load_adapter(adapter_name):
            return {"error": "Failed to load adapter"}
        
        # Test cases for Leonardo evaluation
        test_cases = [
            {
                "messages": [
                    {"role": "system", "content": "You are Leonardo, a voice-first AI assistant."},
                    {"role": "user", "content": "Search for recent AI news"}
                ],
                "expected_tool": "search_web"
            },
            {
                "messages": [
                    {"role": "system", "content": "You are Leonardo, a voice-first AI assistant."},
                    {"role": "user", "content": "Send an email to John about the meeting"}
                ],
                "expected_tool": "send_email"
            }
        ]
        
        results = {
            "adapter_name": adapter_name,
            "test_results": [],
            "overall_score": 0.0,
            "timestamp": datetime.now().isoformat()
        }
        
        for i, test_case in enumerate(test_cases):
            try:
                response = await self.generate_response(test_case["messages"])
                
                # Basic evaluation (can be enhanced)
                score = 1.0 if test_case["expected_tool"] in response.lower() else 0.0
                
                results["test_results"].append({
                    "test_id": i,
                    "input": test_case["messages"][-1]["content"],
                    "response": response,
                    "expected": test_case["expected_tool"],
                    "score": score
                })
                
            except Exception as e:
                results["test_results"].append({
                    "test_id": i,
                    "error": str(e),
                    "score": 0.0
                })
        
        # Calculate overall score
        if results["test_results"]:
            total_score = sum(r.get("score", 0) for r in results["test_results"])
            results["overall_score"] = total_score / len(results["test_results"])
        
        self.logger.info(f"📊 Evaluation complete. Score: {results['overall_score']:.2f}")
        
        return results
    
    async def shutdown(self) -> None:
        """Shutdown the adapter loader."""
        self.logger.info("✅ LoRA adapter loader shutdown")
        self.model = None
        self.base_model = None
        self.tokenizer = None
