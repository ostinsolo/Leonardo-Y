"""
Grammar-Constrained Decoding for Leonardo LLM Planner
Ensures JSON-only output from LLM, eliminates "chatty text" problem
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import re

# Constrained generation libraries
try:
    import outlines
    from outlines import models, generate
    OUTLINES_AVAILABLE = True
except ImportError:
    outlines = None
    OUTLINES_AVAILABLE = False

try:
    import guidance
    GUIDANCE_AVAILABLE = True
except ImportError:
    guidance = None
    GUIDANCE_AVAILABLE = False

# Transformers for model loading
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Ollama for local models
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    ollama = None
    OLLAMA_AVAILABLE = False

# JSON validation
try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    jsonschema = None
    JSONSCHEMA_AVAILABLE = False

from ..config import LeonardoConfig
from .tool_schema import ToolCall

logger = logging.getLogger(__name__)


class ConstrainedDecoder:
    """
    Grammar-constrained decoder ensuring JSON-only tool call output.
    Eliminates LLM "chatty text" problem with hard constraints.
    """
    
    def __init__(self, config: LeonardoConfig):
        self.config = config
        self.model = None
        self.tokenizer = None
        self.generator = None
        self.grammar_path = Path(__file__).parent / "grammars"
        self.schema_path = self.grammar_path / "tool_call_schema.json"
        self.ebnf_path = self.grammar_path / "tool_call.ebnf"
        
        # Load schema for validation
        self.schema = self._load_schema()
        self.ebnf_grammar = self._load_ebnf_grammar()
        
    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON schema for tool calls."""
        try:
            with open(self.schema_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            return {}
    
    def _load_ebnf_grammar(self) -> str:
        """Load EBNF grammar for constrained generation."""
        try:
            with open(self.ebnf_path) as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load EBNF grammar: {e}")
            return ""
    
    async def initialize(self, model_name: Optional[str] = None) -> bool:
        """Initialize constrained decoder with model."""
        try:
            model_name = model_name or self.config.llm.model_name or "llama3.2:latest"
            logger.info(f"🧠 Initializing constrained decoder with {model_name}")
            
            # Try Ollama first if it's a local model (fastest)
            if ":" in model_name and OLLAMA_AVAILABLE and self._initialize_ollama(model_name):
                logger.info("✅ Using Ollama for local grammar-constrained generation")
                return True
            
            # Try Outlines for Hugging Face models
            elif OUTLINES_AVAILABLE and self._initialize_outlines(model_name):
                logger.info("✅ Using Outlines for grammar-constrained generation")
                return True
                
            # Fallback to Guidance
            elif GUIDANCE_AVAILABLE and self._initialize_guidance(model_name):
                logger.info("✅ Using Guidance for constrained generation")
                return True
                
            # Fallback to regex-based validation with Ollama
            elif ":" in model_name and OLLAMA_AVAILABLE and self._initialize_ollama_regex(model_name):
                logger.info("⚠️ Using Ollama with regex validation")
                return True
                
            # Final fallback to transformers + regex
            elif self._initialize_regex_fallback(model_name):
                logger.info("⚠️ Using transformers with regex fallback for JSON validation")
                return True
            
            else:
                logger.error("❌ No constrained generation library available")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize constrained decoder: {e}")
            return False
    
    def _initialize_outlines(self, model_name: str) -> bool:
        """Initialize with Outlines for grammar constraints."""
        try:
            # Load model for Outlines
            self.model = models.transformers(model_name)
            
            # Create grammar-constrained generator
            self.generator = generate.json(self.model, self.schema)
            
            logger.info("✅ Outlines grammar constraints active")
            return True
            
        except Exception as e:
            logger.error(f"❌ Outlines initialization failed: {e}")
            return False
    
    def _initialize_guidance(self, model_name: str) -> bool:
        """Initialize with Guidance for constraints."""
        try:
            # Set up guidance model
            guidance.llm = guidance.models.Transformers(model_name)
            
            # Create constrained generation template
            self.generator = guidance('''
            {{#geneach 'tool_calls' stop=False}}
            {
                "tool": "{{gen 'tool' pattern=tool_pattern max_tokens=50}}",
                "args": {{gen 'args' max_tokens=200}},
                "meta": {
                    "risk": "{{gen 'risk' pattern=risk_pattern max_tokens=20}}",
                    "command_id": "{{gen 'command_id' max_tokens=50}}"
                }
            }
            {{/geneach}}
            ''')
            
            logger.info("✅ Guidance constraints active")
            return True
            
        except Exception as e:
            logger.error(f"❌ Guidance initialization failed: {e}")
            return False
    
    def _initialize_ollama(self, model_name: str) -> bool:
        """Initialize with Ollama for local models (fastest)."""
        try:
            if not OLLAMA_AVAILABLE:
                return False
            
            # Test Ollama connection and model availability
            models = ollama.list()
            available_models = [model.model for model in models.models]
            
            if model_name not in available_models:
                logger.error(f"❌ Ollama model '{model_name}' not found. Available: {available_models}")
                return False
            
            # Store model name for generation
            self.ollama_model = model_name
            logger.info(f"✅ Ollama model '{model_name}' ready")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ollama initialization failed: {e}")
            return False
    
    def _initialize_ollama_regex(self, model_name: str) -> bool:
        """Initialize with Ollama + regex validation fallback."""
        try:
            if not OLLAMA_AVAILABLE:
                return False
            
            # Test Ollama connection
            models = ollama.list()
            available_models = [model.model for model in models.models]
            
            if model_name not in available_models:
                logger.error(f"❌ Ollama model '{model_name}' not found. Available: {available_models}")
                return False
            
            self.ollama_model = model_name
            self.use_regex_validation = True
            logger.info(f"✅ Ollama regex fallback with '{model_name}' ready")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ollama regex fallback failed: {e}")
            return False

    def _initialize_regex_fallback(self, model_name: str) -> bool:
        """Initialize with basic model + regex validation with Intel Mac optimizations."""
        try:
            if not TRANSFORMERS_AVAILABLE:
                return False
            
            import os
            import multiprocessing as mp
            
            # Intel Mac optimizations - fix OpenMP conflicts
            os.environ["OMP_NUM_THREADS"] = "1"
            os.environ["MKL_NUM_THREADS"] = "1" 
            os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
            
            # Fix multiprocessing on macOS
            if mp.get_start_method(allow_none=True) != "spawn":
                mp.set_start_method("spawn", force=True)
            
            # Setup model cache directory
            cache_dir = Path(self.config.llm.model_cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Setup offload directory for memory management
            offload_dir = Path(self.config.llm.offload_folder)
            offload_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"🗂️ Using model cache: {cache_dir}")
            logger.info(f"💾 Using offload directory: {offload_dir}")
                
            # Load tokenizer with caching
            logger.info(f"🔤 Loading tokenizer from cache...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=str(cache_dir)
            )
            
            # Load model with Intel Mac optimizations and caching
            logger.info(f"🧠 Loading model from cache (Intel Mac optimized)...")
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                cache_dir=str(cache_dir),
                device_map="cpu",  # Force CPU for Intel Mac stability
                torch_dtype=torch.float32,  # No fp16 on Intel Mac CPU
                low_cpu_mem_usage=True,  # Reduce memory usage
                offload_folder=str(offload_dir),  # Offload to disk
                trust_remote_code=True  # Required for some models
            )
            
            logger.info("✅ Cached model with Intel Mac optimizations loaded")
            return True
            
        except Exception as e:
            logger.error(f"❌ Regex fallback failed: {e}")
            logger.error(f"   Consider using Ollama instead: ollama pull llama3.2:latest")
            return False
    
    async def generate_constrained(self, prompt: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Generate grammar-constrained tool call."""
        try:
            # Use Ollama if available (fastest, local)
            if hasattr(self, 'ollama_model') and OLLAMA_AVAILABLE:
                return await self._generate_with_ollama(prompt, max_retries)
            
            # Use Outlines if available
            elif OUTLINES_AVAILABLE and self.generator:
                return await self._generate_with_outlines(prompt)
            
            # Use Guidance if available  
            elif GUIDANCE_AVAILABLE and self.generator:
                return await self._generate_with_guidance(prompt)
            
            # Fallback to transformers + regex validation
            else:
                return await self._generate_with_regex(prompt, max_retries)
                
        except Exception as e:
            logger.error(f"❌ Constrained generation failed: {e}")
            return None
    
    async def _generate_with_ollama(self, prompt: str, max_retries: int) -> Optional[Dict[str, Any]]:
        """Generate using Ollama local models with regex validation."""
        formatted_prompt = self._format_tool_call_prompt(prompt)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🦙 Generating with Ollama {self.ollama_model} (attempt {attempt + 1})")
                
                # Generate with Ollama
                response = ollama.generate(
                    model=self.ollama_model,
                    prompt=formatted_prompt,
                    options={
                        "temperature": 0.3,  # Lower temperature for more consistent JSON
                        "num_predict": 300,   # Limit tokens for JSON response
                        "stop": ["\n\n", "```"],  # Stop at double newline or code blocks
                    }
                )
                
                response_text = response.get('response', '').strip()
                logger.debug(f"Raw Ollama response: {response_text[:200]}...")
                
                # Extract and validate JSON
                tool_call = self._extract_json_from_response(response_text)
                if tool_call and self._validate_tool_call(tool_call):
                    logger.info(f"✅ Valid tool call from Ollama (attempt {attempt + 1}): {tool_call['tool']}")
                    return tool_call
                else:
                    logger.warning(f"❌ Invalid JSON attempt {attempt + 1}: {response_text[:100]}...")
                    
            except Exception as e:
                logger.error(f"❌ Ollama generation attempt {attempt + 1} failed: {e}")
        
        logger.error("❌ All Ollama attempts failed")
        return None

    async def _generate_with_outlines(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Generate using Outlines grammar constraints."""
        try:
            # Format prompt for tool call generation
            formatted_prompt = self._format_tool_call_prompt(prompt)
            
            # Generate with JSON schema constraints
            result = self.generator(formatted_prompt)
            
            # Validate result
            if self._validate_tool_call(result):
                logger.info("✅ Valid tool call generated with Outlines")
                return result
            else:
                logger.error("❌ Invalid tool call from Outlines")
                return None
                
        except Exception as e:
            logger.error(f"❌ Outlines generation failed: {e}")
            return None
    
    async def _generate_with_guidance(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Generate using Guidance constraints."""
        try:
            # Format prompt and generate
            formatted_prompt = self._format_tool_call_prompt(prompt)
            result = self.generator(prompt=formatted_prompt)
            
            # Extract and validate JSON
            tool_call = self._extract_json_from_guidance(result)
            if tool_call and self._validate_tool_call(tool_call):
                logger.info("✅ Valid tool call generated with Guidance")
                return tool_call
            else:
                logger.error("❌ Invalid tool call from Guidance")
                return None
                
        except Exception as e:
            logger.error(f"❌ Guidance generation failed: {e}")
            return None
    
    async def _generate_with_regex(self, prompt: str, max_retries: int) -> Optional[Dict[str, Any]]:
        """Generate with regex validation fallback."""
        formatted_prompt = self._format_tool_call_prompt(prompt)
        
        for attempt in range(max_retries):
            try:
                # Generate response
                inputs = self.tokenizer(formatted_prompt, return_tensors="pt")
                
                with torch.no_grad():
                    outputs = self.model.generate(
                        inputs.input_ids,
                        max_new_tokens=300,
                        temperature=0.7,
                        do_sample=True,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                
                # Decode response
                response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
                
                # Extract and validate JSON
                tool_call = self._extract_json_from_response(response)
                if tool_call and self._validate_tool_call(tool_call):
                    logger.info(f"✅ Valid tool call generated with regex (attempt {attempt + 1})")
                    return tool_call
                else:
                    logger.warning(f"❌ Invalid JSON attempt {attempt + 1}: {response[:100]}...")
                    
            except Exception as e:
                logger.error(f"❌ Regex generation attempt {attempt + 1} failed: {e}")
        
        logger.error("❌ All regex validation attempts failed")
        return None
    
    def _format_tool_call_prompt(self, user_input: str) -> str:
        """Format prompt to encourage JSON-only tool call output."""
        return f"""<system>
You are Leonardo's planning component. Your ONLY job is to output a valid JSON tool call.
You must respond with EXACTLY one JSON object, nothing else.
No explanations, no text, ONLY the JSON tool call.

JSON Schema:
{json.dumps(self.schema, indent=2)}

Available tools: {", ".join(self.schema["properties"]["tool"]["enum"])}
</system>

<user>
{user_input}
</user>

<assistant>
"""
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from potentially chatty response."""
        # Remove common prefixes
        response = response.strip()
        
        # Try to find JSON block
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            return None
            
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            return None
    
    def _extract_json_from_guidance(self, result) -> Optional[Dict[str, Any]]:
        """Extract JSON from Guidance result."""
        try:
            # Guidance-specific extraction logic
            if hasattr(result, 'variables'):
                # Extract variables and construct JSON
                return {
                    "tool": result.variables.get('tool', ''),
                    "args": json.loads(result.variables.get('args', '{}')),
                    "meta": {
                        "risk": result.variables.get('risk', 'safe'),
                        "command_id": result.variables.get('command_id', '')
                    }
                }
            else:
                return self._extract_json_from_response(str(result))
        except Exception:
            return None
    
    def _validate_tool_call(self, tool_call: Dict[str, Any]) -> bool:
        """Validate tool call against schema."""
        try:
            # Basic structure validation
            if not all(key in tool_call for key in ["tool", "args", "meta"]):
                logger.error(f"❌ Missing required keys in tool call: {tool_call.keys()}")
                return False
            
            # Tool validation
            valid_tools = self.schema["properties"]["tool"]["enum"]
            if tool_call["tool"] not in valid_tools:
                logger.error(f"❌ Invalid tool '{tool_call['tool']}', must be one of: {valid_tools}")
                return False
            
            # Risk level validation  
            valid_risks = ["safe", "review", "confirm", "owner_root"]
            risk = tool_call["meta"].get("risk", "")
            if risk not in valid_risks:
                logger.error(f"❌ Invalid risk level '{risk}', must be one of: {valid_risks}")
                return False
            
            # Args must be dict
            if not isinstance(tool_call["args"], dict):
                logger.error(f"❌ Args must be dict, got: {type(tool_call['args'])}")
                return False
            
            logger.info(f"✅ Valid tool call: {tool_call['tool']} (risk: {risk})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Tool call validation error: {e}")
            return False
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tools from schema."""
        return self.schema.get("properties", {}).get("tool", {}).get("enum", [])
    
    def shutdown(self):
        """Cleanup resources."""
        self.model = None
        self.tokenizer = None
        self.generator = None
        logger.info("✅ Constrained decoder shutdown")
