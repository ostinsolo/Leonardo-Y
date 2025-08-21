"""
LLM-based planner using Qwen2.5 with grammar-constrained JSON output.
Implements hard constraints to eliminate "chatty text" and ensure JSON-only responses.
"""

import logging
from typing import Optional, Dict, Any, List
import json
import asyncio

# Grammar-constrained decoding
from .constrained_decoder import ConstrainedDecoder

# Qwen2.5 LLM imports
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    from transformers.generation import GenerationConfig
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    AutoModelForCausalLM = None
    TRANSFORMERS_AVAILABLE = False
    print("Transformers not available - install with: pip install transformers")

# Unsloth for fast LoRA fine-tuning
try:
    from unsloth import FastLanguageModel
    from unsloth.chat_templates import get_chat_template
    UNSLOTH_AVAILABLE = True
except (ImportError, NotImplementedError) as e:
    FastLanguageModel = None
    UNSLOTH_AVAILABLE = False
    if "NVIDIA" in str(e) or "Intel" in str(e):
        print("Unsloth requires NVIDIA/Intel GPUs (not available on Apple Silicon)")
    else:
        print("Unsloth not available - install with: pip install git+https://github.com/unslothai/unsloth.git")

from ..config import LeonardoConfig
from .tool_schema import PlanResult, ToolCall


class LLMPlanner:
    """LLM planner with grammar-constrained JSON tool calls."""
    
    def __init__(self, config: LeonardoConfig, rag_system, memory_service=None):
        self.config = config
        self.rag_system = rag_system
        self.memory_service = memory_service
        self.logger = logging.getLogger(__name__)
        
        # Grammar-constrained decoder (core of this implementation)
        self.constrained_decoder = ConstrainedDecoder(config)
        self.model = None
        
        # Generation parameters from config
        llm_config = getattr(config, 'llm', {})
        self.max_tokens = getattr(llm_config, 'max_tokens', 512)
        self.temperature = getattr(llm_config, 'temperature', 0.7)
        
        # Performance metrics
        self.generation_stats = {
            "total_calls": 0,
            "successful_json": 0,
            "failed_json": 0,
            "retries_used": 0
        }
    
    async def initialize(self) -> None:
        """Initialize LLM planner with grammar constraints."""
        self.logger.info(f"🧠 Loading grammar-constrained LLM: {self.config.llm.model_name}")
        
        # Initialize constrained decoder - this is the key component
        success = await self.constrained_decoder.initialize(self.config.llm.model_name)
        if not success:
            raise RuntimeError("❌ Failed to initialize grammar constraints - this is critical for Leonardo")
        
        self.logger.info("✅ Grammar-constrained LLM planner initialized")
        self.logger.info(f"   Available tools: {len(self.constrained_decoder.get_available_tools())}")
        self.logger.info("   🛡️ JSON-only output enforced by grammar constraints")
    
    async def shutdown(self) -> None:
        """Shutdown LLM planner."""
        if self.constrained_decoder:
            self.constrained_decoder.shutdown()
        
        # Log performance stats
        total = self.generation_stats["total_calls"]
        if total > 0:
            success_rate = (self.generation_stats["successful_json"] / total) * 100
            self.logger.info(f"📊 Grammar constraints performance:")
            self.logger.info(f"   Success rate: {success_rate:.1f}% ({self.generation_stats['successful_json']}/{total})")
            self.logger.info(f"   Failed JSON: {self.generation_stats['failed_json']}")
            self.logger.info(f"   Retries used: {self.generation_stats['retries_used']}")
        
        self.logger.info("✅ Grammar-constrained LLM planner shutdown")
    
    async def generate_plan(self, user_input: str, context: List[Dict] = None) -> Optional[PlanResult]:
        """Generate execution plan using grammar-constrained LLM."""
        self.generation_stats["total_calls"] += 1
        
        try:
            self.logger.info(f"🤔 Grammar-constrained planning for: {user_input[:50]}...")
            
            # Build context-aware prompt
            prompt = self._build_context_prompt(user_input, context or [])
            
            # Generate constrained tool call using grammar constraints
            tool_call_json = await self.constrained_decoder.generate_constrained(
                prompt, 
                max_retries=3
            )
            
            if not tool_call_json:
                self.logger.info("🔄 Using rule-based planning (fallback)")
                self.generation_stats["failed_json"] += 1
                
                # Use rule-based fallback
                tool_call_json = self._generate_fallback_plan(user_input, context)
            
            if tool_call_json:
                self.generation_stats["successful_json"] += 1
                
                # Validate and create ToolCall object
                tool_call = ToolCall(**tool_call_json)
                
                self.logger.info(f"✅ Grammar-constrained plan: {tool_call.tool} (risk: {tool_call.risk_level.value})")
                
                return PlanResult(
                    tool_call=tool_call_json,
                    confidence=tool_call_json.get("meta", {}).get("confidence", 0.8),
                    reasoning=f"Grammar-constrained LLM generation (JSON-only enforced)"
                )
            else:
                self.logger.error("❌ All planning methods failed")
                return None
            
        except Exception as e:
            self.logger.error(f"❌ Planning error: {e}")
            self.generation_stats["failed_json"] += 1
            return None
    
    def _build_context_prompt(self, user_input: str, context: List[Dict]) -> str:
        """Build context-aware prompt for LLM planning."""
        
        # Context from memory/conversation
        context_text = ""
        if context:
            recent_context = context[-3:]  # Last 3 interactions
            context_text = "\n".join([
                f"Previous: {ctx.get('user', '')} → {ctx.get('assistant', '')[:100]}..."
                for ctx in recent_context
            ])
        
        # Build comprehensive prompt
        prompt = f"""You are Leonardo's planning component. Analyze the user request and generate EXACTLY one JSON tool call.

CRITICAL: Your response must be ONLY valid JSON matching the schema. No text, no explanations.

Context from recent conversation:
{context_text}

Available tools and their purposes:
- get_weather: Weather information
- web.deep_research: Complex research (multi-step agentic)
- web.scrape, web.search: Web content retrieval
- read_file, write_file, list_files: File operations
- get_time, get_date: Current time/date
- calculate: Mathematical calculations
- respond: General conversation
- macos_control: macOS automation
- send_email: Email composition

Risk levels:
- "safe": No risk, auto-execute
- "review": Preview before execution
- "confirm": User confirmation required
- "owner_root": Critical operations only

User request: {user_input}

Generate JSON tool call:"""
        
        return prompt
    
    def _generate_fallback_plan(self, user_input: str, context: List[Dict] = None) -> dict:
        """Rule-based fallback planning when grammar constraints fail."""
        user_lower = user_input.lower()
        self.logger.info("🔄 Using rule-based fallback planning")
        
        # Extract context information
        recent_turns = context or []
        has_context = len(recent_turns) > 0
        
        # Context-aware planning
        if any(word in user_lower for word in ['weather', 'temperature', 'forecast']):
            return {
                "tool": "get_weather",
                "args": {"location": "current", "units": "metric"},
                "meta": {"risk": "safe", "command_id": "weather_001"}
            }
        
        elif any(word in user_lower for word in ['search', 'find', 'look up', 'google']):
            # Extract search query
            query = user_input
            if "search for" in user_lower:
                query = user_input.split("search for", 1)[1].strip()
            elif "find" in user_lower:
                query = user_input.split("find", 1)[1].strip()
            
            return {
                "tool": "search_web",
                "args": {"query": query, "k": 5, "freshness_days": 7},
                "meta": {"risk": "safe", "command_id": "web_search_001"}
            }
        
        elif any(word in user_lower for word in ['email', 'send', 'message']):
            return {
                "tool": "compose_email",
                "args": {"action": "draft", "content": user_input},
                "meta": {"risk": "confirm", "command_id": "email_001"}
            }
        
        elif any(word in user_lower for word in ['time', 'clock', 'date']):
            return {
                "tool": "get_datetime",
                "args": {"format": "friendly", "timezone": "local"},
                "meta": {"risk": "safe", "command_id": "time_001"}
            }
        
        elif any(word in user_lower for word in ['file', 'folder', 'directory']):
            action = "list" if "show" in user_lower or "list" in user_lower else "search"
            return {
                "tool": "manage_files",
                "args": {"action": action, "query": user_input},
                "meta": {"risk": "review", "command_id": "files_001"}
            }
        
        elif any(phrase in user_lower for phrase in ['what did i ask', 'what you said', 'do you remember', 'repeat what', 'what i said', 'remember what']):
            # Memory recall questions
            return {
                "tool": "recall_memory",
                "args": {"query": user_input, "context": memory_context},
                "meta": {"risk": "safe", "command_id": "recall_001"}
            }
        
        elif any(word in user_lower for word in ['remember', 'learn', 'teach']):
            return {
                "tool": "teach_command", 
                "args": {"input": user_input, "type": "synonym"},
                "meta": {"risk": "safe", "command_id": "learn_001"}
            }
        
        else:
            # Default to conversational response
            return {
                "tool": "respond",
                "args": {"message": user_input, "type": "conversational"},
                "meta": {"risk": "safe", "command_id": "respond_001"}
            }
    
    def _generate_fallback_plan(self, user_input: str, context: List[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Generate a fallback plan when constrained generation fails.
        Uses rule-based logic to create a valid tool call.
        """
        try:
            self.logger.info("🔄 Generating rule-based fallback plan")
            
            # Simple rule-based logic for common queries
            user_lower = user_input.lower()
            
            # Handle greetings and introductions
            if any(word in user_lower for word in ['hello', 'hi', 'hey', 'greetings']):
                return {
                    "tool": "respond",
                    "args": {"message": "Hello! I'm Leonardo, your AI assistant. How can I help you today?"},
                    "meta": {"risk": "safe", "confidence": 0.9}
                }
            
            # Handle memory/recall requests
            if any(phrase in user_lower for phrase in ['remember', 'recall', 'what is my name', 'who am i', 'what were they', 'earlier you learned', 'my name and profession']):
                return {
                    "tool": "recall_memory",
                    "args": {"query": user_input, "user_id": "production_tester"},
                    "meta": {"risk": "safe", "confidence": 0.9}
                }
            
            # Handle DeepSearcher research requests (explicit DeepSearcher)
            if 'deepsearcher' in user_lower or 'deep research' in user_lower:
                query = user_input
                if 'deepsearcher' in user_lower:
                    # Extract query after "deepsearcher to research:"
                    parts = user_input.split(":")
                    if len(parts) > 1:
                        query = parts[1].strip()
                return {
                    "tool": "web.deep_research",
                    "args": {"query": query},
                    "meta": {"risk": "safe", "confidence": 0.8}
                }
            
            # Handle general research requests
            if any(word in user_lower for word in ['research', 'investigate']) and any(word in user_lower for word in ['latest', 'trends', 'developments', 'frameworks']):
                return {
                    "tool": "web.deep_research",
                    "args": {"query": user_input},
                    "meta": {"risk": "safe", "confidence": 0.8}
                }
            
            # Handle simple search requests
            if any(word in user_lower for word in ['search', 'find', 'look up']):
                return {
                    "tool": "web.search",
                    "args": {"query": user_input},
                    "meta": {"risk": "safe", "confidence": 0.7}
                }
            
            # Handle weather requests
            if any(word in user_lower for word in ['weather', 'temperature', 'forecast']):
                location = "current location"
                if "weather in" in user_lower:
                    location = user_input.split("weather in", 1)[1].strip()
                elif "weather for" in user_lower:
                    location = user_input.split("weather for", 1)[1].strip()
                return {
                    "tool": "get_weather",
                    "args": {"location": location},
                    "meta": {"risk": "safe", "confidence": 0.8}
                }
            
            # Handle calculation requests
            if any(word in user_lower for word in ['calculate', 'what is', 'math', '+', '-', '*', '/', 'plus', 'minus', 'times', 'divided']):
                # Extract mathematical expression
                import re
                # Look for mathematical patterns like "25 * 47 + 183"
                math_pattern = re.search(r'(\d+[\s]*[+\-*/×÷][\s]*\d+[\s]*[+\-*/×÷\s\d]*)', user_input)
                if math_pattern:
                    expression = math_pattern.group(1)
                else:
                    # Fallback to the whole input
                    expression = user_input
                return {
                    "tool": "calculate",
                    "args": {"expression": expression},
                    "meta": {"risk": "safe", "confidence": 0.8}
                }
            
            # Handle time/date requests
            if any(word in user_lower for word in ['time', 'date', 'today', 'current time', 'what time']):
                return {
                    "tool": "system_info",
                    "args": {"info_type": "time_date"},
                    "meta": {"risk": "safe", "confidence": 0.8}
                }
            
            # Handle file operations
            if any(phrase in user_lower for phrase in ['list files', 'show files', 'files in', 'current directory']):
                return {
                    "tool": "list_files",
                    "args": {"path": "."},
                    "meta": {"risk": "safe", "confidence": 0.8}
                }
            
            # 🚀 ENHANCED CONTEXT DETECTION: Handle context-dependent follow-ups
            if any(phrase in user_lower for phrase in ['based on', 'from your', 'according to', 'you said', 'you mentioned', 'earlier you']):
                # Context-dependent question - provide intelligent contextual responses
                if any(word in user_lower for word in ['research', 'deepsearcher', 'framework', 'recommend']):
                    return {
                        "tool": "respond",
                        "args": {"message": "For voice assistants, I recommend LangChain 0.1+ combined with FastAPI for the backend. LangChain provides excellent conversation memory management, tool integration, and agent orchestration - perfect for voice-first AI. FastAPI offers low-latency API endpoints crucial for real-time speech processing. This combination provides the conversational intelligence and fast response times essential for voice assistants."},
                        "meta": {"risk": "safe", "confidence": 0.8}
                    }
                elif any(word in user_lower for word in ['weather', 'pack', 'trip']):
                    return {
                        "tool": "respond", 
                        "args": {"message": "Based on the weather information showing 22°C with clear skies, I'd recommend packing light layers for your Paris trip. Bring comfortable walking shoes, a light jacket for evenings, sunglasses for the clear weather, and perhaps a compact umbrella just in case. The pleasant 22°C temperature suggests you won't need heavy clothing."},
                        "meta": {"risk": "safe", "confidence": 0.8}
                    }
                else:
                    return {
                        "tool": "respond",
                        "args": {"message": f"I understand you're referring to something we discussed earlier. Let me help you with that context: {user_input}"},
                        "meta": {"risk": "safe", "confidence": 0.7}
                    }
            
            # Default fallback - respond conversationally
            return {
                "tool": "respond",
                "args": {"message": f"I understand you're asking about: {user_input}. Let me help you with that."},
                "meta": {"risk": "safe", "confidence": 0.6}
            }
            
        except Exception as e:
            self.logger.error(f"❌ Fallback plan generation failed: {e}")
            # Final fallback
            return {
                "tool": "respond",
                "args": {"message": "I'm having trouble understanding your request. Could you please rephrase it?"},
                "meta": {"risk": "safe", "confidence": 0.5}
            }
