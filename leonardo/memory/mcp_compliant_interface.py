"""
MCP-Compliant Memory Interface for Leonardo
Uses the official MCP Memory Service for full protocol compliance
"""

import asyncio
import logging
import json
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# Import MCP Memory Service
try:
    from mcp_memory_service import (
        Memory, 
        MemoryStorage, 
        SqliteVecMemoryStorage, 
        MemoryQueryResult
    )
    # Remove ChromaMemoryStorage (deprecated)
    MCP_MEMORY_SERVICE_AVAILABLE = True
except ImportError as e:
    MCP_MEMORY_SERVICE_AVAILABLE = False
    print(f"⚠️ MCP Memory Service not available: {e}")

# Import Leonardo's enhanced memory for fallback
try:
    from .enhanced_memory import EnhancedMemorySystem
    import time  # needed for timestamp conversion
    ENHANCED_MEMORY_AVAILABLE = True
except ImportError:
    ENHANCED_MEMORY_AVAILABLE = False
    import time  # still needed for simple fallback


class MCPCompliantInterface:
    """
    Fully MCP-compliant memory interface for Leonardo.
    
    Provides the standard MCP operations:
    - add(user_id, content, metadata)
    - search(user_id, query, limit) 
    - get_recent(user_id, limit)
    - forget(user_id, memory_id/query)
    
    Uses official MCP Memory Service as primary backend with
    enhanced memory fallback for compatibility.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # MCP Memory Service components
        self.memory: Optional[Memory] = None
        self.storage: Optional[MemoryStorage] = None
        self.backend_type = "unknown"
        
        # Enhanced memory fallback
        self.enhanced_memory: Optional[EnhancedMemorySystem] = None
        
        # Configuration
        self.memory_dir = Path(config.get("memory_dir", "leonardo_mcp_memory"))
        self.memory_dir.mkdir(exist_ok=True)
        
        # Storage options: "sqlite_vec", "enhanced_fallback" (ChromaDB deprecated)
        self.storage_backend = config.get("storage_backend", "sqlite_vec")
        self.collection_name = config.get("collection_name", "leonardo_conversations")
        
        self.logger.info("🔌 MCP-Compliant Memory Interface initializing...")
        
    async def initialize(self) -> bool:
        """Initialize MCP-compliant memory backend."""
        
        if MCP_MEMORY_SERVICE_AVAILABLE:
            try:
                await self._initialize_mcp_backend()
                return True
            except Exception as e:
                self.logger.warning(f"⚠️ MCP backend failed: {e}, trying fallback...")
                
        # Fallback to enhanced memory
        if ENHANCED_MEMORY_AVAILABLE:
            try:
                await self._initialize_enhanced_fallback()
                return True
            except Exception as e:
                self.logger.error(f"❌ Enhanced memory fallback failed: {e}")
        
        # Final fallback to simple mode
        await self._initialize_simple_fallback()
        return True
    
    async def _initialize_mcp_backend(self) -> None:
        """Initialize official MCP Memory Service backend."""
        
        if self.storage_backend == "sqlite_vec":
            # SQLite-vec storage (recommended, replaces deprecated ChromaDB)
            self.storage = SqliteVecMemoryStorage(
                db_path=str(self.memory_dir / "leonardo_memory_vec.db"),
                embedding_model='all-MiniLM-L6-v2'
            )
            self.backend_type = "mcp_sqlite_vec"
            
        else:
            raise ValueError(f"Unknown storage backend: {self.storage_backend}. Use 'sqlite_vec' (ChromaDB deprecated)")
        
        # Create MCP Memory instance
        self.memory = Memory(storage=self.storage)
        await self.memory.initialize()
        
        self.logger.info(f"✅ MCP Memory Service initialized: {self.backend_type}")
    
    async def _initialize_enhanced_fallback(self) -> None:
        """Initialize enhanced memory as fallback."""
        enhanced_memory_dir = self.memory_dir / "enhanced"
        
        # EnhancedMemorySystem expects (memory_dir: Path, max_experiences: int)
        self.enhanced_memory = EnhancedMemorySystem(
            memory_dir=enhanced_memory_dir,
            max_experiences=10000
        )
        await self.enhanced_memory.initialize()
        
        self.backend_type = "enhanced_fallback"
        self.logger.info("✅ Enhanced Memory fallback initialized")
    
    async def _initialize_simple_fallback(self) -> None:
        """Initialize simple JSON-based fallback."""
        self.simple_memory = {
            "recent_turns": [],
            "user_profiles": {},
            "max_recent": 20
        }
        
        # Load existing data
        memory_file = self.memory_dir / "simple_memory.json"
        if memory_file.exists():
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    self.simple_memory.update(json.load(f))
                    self.logger.info("📖 Loaded existing simple memory")
            except Exception as e:
                self.logger.warning(f"Could not load existing memory: {e}")
        
        self.backend_type = "simple_fallback"
        self.logger.info("✅ Simple memory fallback initialized")
    
    async def shutdown(self) -> None:
        """Shutdown memory interface and save data."""
        try:
            if self.backend_type.startswith("mcp_") and self.memory:
                # MCP Memory Service cleanup
                await self.memory.shutdown()
                
            elif self.backend_type == "enhanced_fallback" and self.enhanced_memory:
                # Enhanced memory cleanup
                await self.enhanced_memory.shutdown()
                
            elif self.backend_type == "simple_fallback":
                # Save simple memory data
                memory_file = self.memory_dir / "simple_memory.json"
                with open(memory_file, 'w', encoding='utf-8') as f:
                    json.dump(self.simple_memory, f, indent=2, ensure_ascii=False)
                    
            self.logger.info("✅ MCP-Compliant Memory Interface shutdown")
            
        except Exception as e:
            self.logger.error(f"❌ Memory shutdown error: {e}")
    
    # MCP Standard Operations
    
    async def add(self, user_id: str, content: str, metadata: Dict[str, Any] = None) -> str:
        """
        MCP Standard: Add new memory content.
        Returns memory_id for later reference.
        """
        try:
            metadata = metadata or {}
            metadata.update({
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "leonardo_version": "1.0"
            })
            
            if self.backend_type.startswith("mcp_"):
                # Use MCP Memory Service
                result = await self.memory.add(content, metadata=metadata)
                memory_id = result.id if hasattr(result, 'id') else str(result)
                
            elif self.backend_type == "enhanced_fallback":
                # Use enhanced memory - correct method signature
                interaction_data = {
                    "user": content.split("User: ", 1)[-1].split("\nAssistant: ")[0] if "User: " in content else content,
                    "assistant": content.split("\nAssistant: ", 1)[-1] if "\nAssistant: " in content else "",
                    "interaction_type": metadata.get("interaction_type", "conversation"),
                    "tools_used": metadata.get("tools_used", []),
                    "response_type": metadata.get("interaction_type", "conversation")
                }
                
                success = metadata.get("success", True)
                response_quality = 1.0  # Default quality
                
                memory_id = await self.enhanced_memory.store_experience(
                    user_id=user_id,
                    interaction_data=interaction_data,
                    success=success,
                    response_quality=response_quality
                )
                
            elif self.backend_type == "simple_fallback":
                # Simple storage
                memory_id = f"{user_id}_{int(datetime.now().timestamp())}"
                memory_item = {
                    "id": memory_id,
                    "user_id": user_id,
                    "content": content,
                    "metadata": metadata,
                    "timestamp": datetime.now().isoformat()
                }
                
                self.simple_memory["recent_turns"].append(memory_item)
                
                # Keep only recent items
                if len(self.simple_memory["recent_turns"]) > self.simple_memory["max_recent"]:
                    self.simple_memory["recent_turns"] = self.simple_memory["recent_turns"][-self.simple_memory["max_recent"]:]
                
            else:
                raise ValueError(f"Unknown backend type: {self.backend_type}")
                
            self.logger.debug(f"🧠 Added memory: {memory_id}")
            return memory_id
            
        except Exception as e:
            self.logger.error(f"❌ Failed to add memory: {e}")
            return ""
    
    async def search(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        MCP Standard: Search memory content by query.
        Returns list of relevant memory items.
        """
        try:
            if self.backend_type.startswith("mcp_"):
                # Use MCP Memory Service search
                results = await self.memory.search(query, limit=limit, user_filter={"user_id": user_id})
                
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        "id": result.id if hasattr(result, 'id') else str(hash(result.content)),
                        "content": result.content,
                        "metadata": result.metadata if hasattr(result, 'metadata') else {},
                        "score": result.score if hasattr(result, 'score') else 1.0,
                        "timestamp": result.metadata.get("timestamp") if hasattr(result, 'metadata') else datetime.now().isoformat()
                    })
                
                return formatted_results
                
            elif self.backend_type == "enhanced_fallback":
                # Use enhanced memory search
                results = await self.enhanced_memory.search_experiences(user_id, query, limit=limit)
                
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        "id": result.get("id", ""),
                        "content": result.get("content", ""),
                        "metadata": result.get("context", {}),
                        "score": result.get("confidence", 1.0),
                        "timestamp": datetime.fromtimestamp(result.get("timestamp", time.time())).isoformat()
                    })
                
                return formatted_results
                
            elif self.backend_type == "simple_fallback":
                # Simple text search
                query_lower = query.lower()
                matches = []
                
                for item in self.simple_memory["recent_turns"]:
                    if (item["user_id"] == user_id and 
                        query_lower in item["content"].lower()):
                        matches.append({
                            "id": item["id"],
                            "content": item["content"],
                            "metadata": item["metadata"],
                            "timestamp": item["timestamp"],
                            "score": 1.0  # Simple search doesn't compute relevance
                        })
                
                return matches[:limit]
            
            return []
            
        except Exception as e:
            self.logger.error(f"❌ Failed to search memory: {e}")
            return []
    
    async def get_recent(self, user_id: str, limit: int = 8) -> List[Dict[str, Any]]:
        """
        MCP Standard: Get recent memory items for context.
        Returns list of recent memory items.
        """
        try:
            if self.backend_type.startswith("mcp_"):
                # Use MCP Memory Service - search with recent constraint
                recent_query = f"user_id:{user_id}"
                results = await self.memory.search(
                    recent_query, 
                    limit=limit, 
                    sort_by="timestamp", 
                    sort_order="desc"
                )
                
                formatted_results = []
                for result in results:
                    # Parse content to extract user/assistant parts for Leonardo compatibility
                    content = result.content
                    parsed_content = self._parse_conversation_content(content)
                    
                    item = {
                        "id": result.id if hasattr(result, 'id') else str(hash(content)),
                        "content": content,
                        "metadata": result.metadata if hasattr(result, 'metadata') else {},
                        "timestamp": result.metadata.get("timestamp") if hasattr(result, 'metadata') else datetime.now().isoformat(),
                        **parsed_content  # Add user_input, ai_response for compatibility
                    }
                    formatted_results.append(item)
                
                return formatted_results
                
            elif self.backend_type == "enhanced_fallback":
                # Use enhanced memory recent retrieval
                recent_experiences = await self.enhanced_memory.get_recent_experiences(user_id, limit=limit)
                
                formatted_results = []
                for exp in recent_experiences:
                    content = exp.get("content", "")
                    parsed_content = self._parse_conversation_content(content)
                    
                    item = {
                        "id": exp.get("id", ""),
                        "content": content,
                        "metadata": exp.get("context", {}),
                        "timestamp": datetime.fromtimestamp(exp.get("timestamp", time.time())).isoformat(),
                        **parsed_content
                    }
                    formatted_results.append(item)
                
                return formatted_results
                
            elif self.backend_type == "simple_fallback":
                # Simple recent retrieval
                user_items = [
                    item for item in self.simple_memory["recent_turns"] 
                    if item["user_id"] == user_id
                ]
                
                # Sort by timestamp (most recent first)
                user_items.sort(key=lambda x: x["timestamp"], reverse=True)
                recent_items = user_items[:limit]
                
                # Parse content for Leonardo compatibility
                for item in recent_items:
                    parsed_content = self._parse_conversation_content(item["content"])
                    item.update(parsed_content)
                
                return recent_items
            
            return []
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get recent memories: {e}")
            return []
    
    async def forget(self, user_id: str, memory_id: str = None, query: str = None) -> bool:
        """
        MCP Standard: Forget/delete memory content.
        Can forget by ID or by query match.
        """
        try:
            if self.backend_type.startswith("mcp_"):
                # Use MCP Memory Service deletion
                if memory_id:
                    result = await self.memory.delete(memory_id)
                    return result.success if hasattr(result, 'success') else bool(result)
                elif query:
                    # Search and delete matching memories
                    matches = await self.search(user_id, query, limit=100)
                    deleted_count = 0
                    for match in matches:
                        if await self.memory.delete(match["id"]):
                            deleted_count += 1
                    return deleted_count > 0
                    
            elif self.backend_type == "enhanced_fallback":
                # Use enhanced memory deletion
                if memory_id:
                    return await self.enhanced_memory.delete_experience(memory_id)
                elif query:
                    matches = await self.search(user_id, query, limit=100)
                    deleted_count = 0
                    for match in matches:
                        if await self.enhanced_memory.delete_experience(match["id"]):
                            deleted_count += 1
                    return deleted_count > 0
                    
            elif self.backend_type == "simple_fallback":
                # Simple deletion
                original_length = len(self.simple_memory["recent_turns"])
                
                if memory_id:
                    self.simple_memory["recent_turns"] = [
                        item for item in self.simple_memory["recent_turns"]
                        if item["id"] != memory_id
                    ]
                elif query:
                    query_lower = query.lower()
                    self.simple_memory["recent_turns"] = [
                        item for item in self.simple_memory["recent_turns"]
                        if not (item["user_id"] == user_id and query_lower in item["content"].lower())
                    ]
                
                return len(self.simple_memory["recent_turns"]) < original_length
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Failed to forget memory: {e}")
            return False
    
    # Leonardo Integration Methods
    
    async def get_context_for_planner(self, user_id: str, query: str = "") -> Dict[str, Any]:
        """
        Get comprehensive memory context for Leonardo's LLM Planner.
        This is the main method that the Planner calls.
        """
        try:
            # Get recent conversation context
            recent_turns = await self.get_recent(user_id, limit=8)
            
            # Search for relevant episodic memories (if query provided)
            relevant_memories = []
            if query:
                relevant_memories = await self.search(user_id, query, limit=5)
            
            # Get user profile/preferences
            user_profile = await self._get_user_profile(user_id)
            
            context = {
                "recent_turns": recent_turns,
                "relevant_memories": relevant_memories,
                "user_profile": user_profile,
                "memory_stats": {
                    "recent_count": len(recent_turns),
                    "relevant_count": len(relevant_memories),
                    "backend_type": self.backend_type,
                    "mcp_compliant": self.backend_type.startswith("mcp_")
                }
            }
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get planner context: {e}")
            return {
                "recent_turns": [],
                "relevant_memories": [],
                "user_profile": {},
                "memory_stats": {"backend_type": self.backend_type}
            }
    
    async def store_interaction(self, user_id: str, interaction: Dict[str, Any]) -> str:
        """
        Store a complete Leonardo interaction (user + assistant + metadata).
        Called after each conversation turn.
        """
        try:
            # Format interaction content for MCP storage
            user_input = interaction.get('user', '')
            assistant_response = interaction.get('assistant', '')
            content = f"User: {user_input}\nAssistant: {assistant_response}"
            
            metadata = {
                "interaction_type": "conversation_turn",
                "success": interaction.get("success", True),
                "tools_used": interaction.get("tools_used", []),
                "response_type": interaction.get("response_type", "conversation"),
                "verification_status": interaction.get("verification_status", "unknown"),
                "leonardo_session": interaction.get("session_id", ""),
            }
            
            # Store using MCP add operation
            memory_id = await self.add(user_id, content, metadata)
            
            # Extract and store user facts/preferences
            await self._extract_user_facts(user_id, interaction)
            
            self.logger.debug(f"💾 Stored interaction: {memory_id}")
            return memory_id
            
        except Exception as e:
            self.logger.error(f"❌ Failed to store interaction: {e}")
            return ""
    
    # Helper Methods
    
    def _parse_conversation_content(self, content: str) -> Dict[str, str]:
        """Parse conversation content to extract user/assistant parts."""
        if "User: " in content and "\nAssistant: " in content:
            try:
                parts = content.split("\nAssistant: ", 1)
                user_part = parts[0].replace("User: ", "", 1)
                assistant_part = parts[1] if len(parts) > 1 else ""
                
                return {
                    "user_input": user_part,
                    "ai_response": assistant_part
                }
            except:
                pass
        
        # Fallback for unparseable content
        return {
            "user_input": content,
            "ai_response": ""
        }
    
    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get stored user profile/preferences."""
        try:
            if self.backend_type == "simple_fallback":
                return self.simple_memory.get("user_profiles", {}).get(user_id, {})
            
            # Search for profile-related memories
            profile_memories = await self.search(user_id, "name preferences profile", limit=10)
            
            profile = {}
            for memory in profile_memories:
                content = memory.get("content", "").lower()
                
                # Extract name
                if "name is" in content:
                    import re
                    name_match = re.search(r"name is (\w+)", content)
                    if name_match:
                        profile["name"] = name_match.group(1).title()
                
                # Extract preferences
                if "prefer" in content or "like" in content:
                    if "preferences" not in profile:
                        profile["preferences"] = []
                    profile["preferences"].append(memory.get("content", "")[:100])
            
            return profile
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get user profile: {e}")
            return {}
    
    async def _extract_user_facts(self, user_id: str, interaction: Dict[str, Any]) -> None:
        """Extract and store user facts/preferences from interaction."""
        try:
            user_input = interaction.get("user", "").lower()
            
            # Extract user name
            import re
            name_patterns = [
                r"my name is (\w+)",
                r"i'm (\w+)",
                r"call me (\w+)",
                r"i am (\w+)"
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, user_input)
                if match:
                    name = match.group(1).title()
                    await self.add(user_id, f"User's name is {name}", {
                        "type": "user_fact",
                        "category": "identity"
                    })
                    
                    # Store in simple backend profile if applicable
                    if self.backend_type == "simple_fallback":
                        if "user_profiles" not in self.simple_memory:
                            self.simple_memory["user_profiles"] = {}
                        if user_id not in self.simple_memory["user_profiles"]:
                            self.simple_memory["user_profiles"][user_id] = {}
                        self.simple_memory["user_profiles"][user_id]["name"] = name
                    
                    break
                    
        except Exception as e:
            self.logger.error(f"❌ Failed to extract user facts: {e}")
    
    # MCP Protocol Information
    
    def get_mcp_info(self) -> Dict[str, Any]:
        """Get MCP compliance and backend information."""
        return {
            "mcp_compliant": self.backend_type.startswith("mcp_"),
            "backend_type": self.backend_type,
            "mcp_memory_service_available": MCP_MEMORY_SERVICE_AVAILABLE,
            "enhanced_memory_available": ENHANCED_MEMORY_AVAILABLE,
            "supported_operations": ["add", "search", "get_recent", "forget"],
            "storage_backend": self.storage_backend if hasattr(self, 'storage_backend') else "unknown"
        }


# Factory function for Leonardo integration
async def create_mcp_compliant_interface(config: Dict[str, Any]) -> MCPCompliantInterface:
    """Create and initialize MCP-compliant memory interface."""
    interface = MCPCompliantInterface(config)
    success = await interface.initialize()
    
    if not success:
        raise RuntimeError("Failed to initialize MCP-compliant memory interface")
    
    return interface
