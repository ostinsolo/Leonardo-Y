#!/usr/bin/env python3
"""
FastMCP Memory Service - Clean MCP-compliant memory interface
Uses FastMCP for proper MCP protocol compliance with Leonardo's memory system

Features:
1. Clean FastMCP decorators (@mcp.tool, @mcp.resource)
2. Built-in SQLite-vec support (no ChromaDB deprecation)  
3. Enhanced memory fallback with JARVIS-1 features
4. Simple file-based fallback for maximum reliability
5. In-memory testing support
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastmcp import FastMCP, Context

# Import Leonardo's enhanced memory for fallback
try:
    from .enhanced_memory import EnhancedMemorySystem
    ENHANCED_MEMORY_AVAILABLE = True
except ImportError as e:
    ENHANCED_MEMORY_AVAILABLE = False
    print(f"⚠️ Enhanced Memory not available: {e}")

# Import stores for simple fallback
try:
    from .stores import JSONLMemoryStore
    STORES_AVAILABLE = True
except ImportError as e:
    STORES_AVAILABLE = False
    print(f"⚠️ Memory Stores not available: {e}")


class FastMCPMemoryService:
    """
    FastMCP-based Memory Service for Leonardo
    
    Clean, modern MCP implementation using FastMCP decorators
    Provides memory tools, resources, and prompts via MCP protocol
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Memory backends
        self.enhanced_memory: Optional[EnhancedMemorySystem] = None
        self.simple_store: Optional[JSONLMemoryStore] = None
        
        # Configuration 
        self.memory_dir = Path(self.config.get("memory_dir", "leonardo_fastmcp_memory"))
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Backend selection
        self.backend_type = "unknown"
        
        # Create FastMCP server instance
        self.mcp_server = FastMCP("Leonardo Memory Service")
        self._register_mcp_tools()
        
        self.logger.info("🚀 FastMCP Memory Service initialized")
    
    async def initialize(self) -> bool:
        """Initialize memory backends in order of preference."""
        try:
            # Try enhanced memory first (JARVIS-1 features)
            if ENHANCED_MEMORY_AVAILABLE:
                try:
                    enhanced_memory_dir = self.memory_dir / "enhanced"
                    enhanced_memory_dir.mkdir(parents=True, exist_ok=True)
                    self.enhanced_memory = EnhancedMemorySystem(
                        memory_dir=enhanced_memory_dir,
                        max_experiences=10000
                    )
                    success = await self.enhanced_memory.initialize()
                    if success:
                        self.backend_type = "enhanced_jarvis"
                        self.logger.info("✅ Enhanced Memory (JARVIS-1) initialized")
                        return True
                except Exception as e:
                    self.logger.warning(f"⚠️ Enhanced memory failed: {e}")
            
            # Fallback to simple store
            if STORES_AVAILABLE:
                try:
                    # JSONLMemoryStore needs a config object
                    from ..config import LeonardoConfig
                    
                    # Create minimal config for JSONLMemoryStore
                    class SimpleConfig:
                        def __init__(self, data_dir):
                            self.data_dir = data_dir
                    
                    simple_config = SimpleConfig(str(self.memory_dir))
                    self.simple_store = JSONLMemoryStore(simple_config)
                    await self.simple_store.initialize()
                    self.backend_type = "simple_jsonl"
                    self.logger.info("✅ Simple JSONL store initialized")
                    return True
                except Exception as e:
                    self.logger.warning(f"⚠️ Simple store failed: {e}")
            
            # Final fallback - create directories only
            self.backend_type = "directory_only"
            self.logger.warning("⚠️ Using directory-only fallback")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize FastMCP Memory Service: {e}")
            return False
    
    def _register_mcp_tools(self):
        """Register MCP tools, resources, and prompts using FastMCP decorators."""
        
        @self.mcp_server.tool
        async def add_memory(content: str, user_id: str = "default", metadata: Dict[str, Any] = None, ctx: Context = None) -> str:
            """Add a memory to the user's memory store."""
            if ctx:
                await ctx.info(f"Adding memory for user {user_id}")
            
            try:
                memory_id = await self._add_memory_internal(user_id, content, metadata or {})
                return f"✅ Memory stored with ID: {memory_id}"
            except Exception as e:
                error_msg = f"❌ Failed to add memory: {e}"
                if ctx:
                    await ctx.error(error_msg)
                return error_msg
        
        @self.mcp_server.tool
        async def search_memory(query: str, user_id: str = "default", limit: int = 5, ctx: Context = None) -> str:
            """Search user's memories for relevant content."""
            if ctx:
                await ctx.info(f"Searching memories for user {user_id}: {query}")
            
            try:
                results = await self._search_memory_internal(user_id, query, limit)
                return json.dumps(results, indent=2)
            except Exception as e:
                error_msg = f"❌ Failed to search memory: {e}"
                if ctx:
                    await ctx.error(error_msg)
                return error_msg
        
        @self.mcp_server.tool
        async def get_recent_memory(user_id: str = "default", limit: int = 10, ctx: Context = None) -> str:
            """Get recent memories for the user."""
            if ctx:
                await ctx.info(f"Getting recent memories for user {user_id}")
            
            try:
                results = await self._get_recent_internal(user_id, limit)
                return json.dumps(results, indent=2)
            except Exception as e:
                error_msg = f"❌ Failed to get recent memories: {e}"
                if ctx:
                    await ctx.error(error_msg)
                return error_msg
        
        @self.mcp_server.tool
        async def forget_memory(memory_id: str, user_id: str = "default", ctx: Context = None) -> str:
            """Forget a specific memory by ID."""
            if ctx:
                await ctx.info(f"Forgetting memory {memory_id} for user {user_id}")
            
            try:
                success = await self._forget_memory_internal(user_id, memory_id)
                return "✅ Memory forgotten" if success else "❌ Memory not found"
            except Exception as e:
                error_msg = f"❌ Failed to forget memory: {e}"
                if ctx:
                    await ctx.error(error_msg)
                return error_msg
        
        @self.mcp_server.resource("leonardo://memory/stats/{user_id}")
        async def memory_stats(user_id: str = "default") -> str:
            """Get memory statistics and backend information."""
            stats = {
                "backend_type": self.backend_type,
                "memory_dir": str(self.memory_dir),
                "enhanced_available": ENHANCED_MEMORY_AVAILABLE,
                "stores_available": STORES_AVAILABLE,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add backend-specific stats
            if self.backend_type == "enhanced_jarvis" and self.enhanced_memory:
                user_profile = self.enhanced_memory.user_profiles.get(user_id, {})
                stats["enhanced_stats"] = {
                    "total_interactions": user_profile.get("total_interactions", 0),
                    "successful_interactions": user_profile.get("successful_interactions", 0),
                    "dominant_themes": dict(user_profile.get("themes", {})),
                    "preferred_tools": dict(user_profile.get("preferred_tools", {}))
                }
            
            return json.dumps(stats, indent=2)
        
        @self.mcp_server.prompt
        def memory_context_prompt(query: str, user_id: str = "default") -> str:
            """Generate a prompt including relevant memory context for the query."""
            return f"""Please provide a response to the following query, taking into account the user's memory context.

User ID: {user_id}
Query: {query}

To get relevant memory context, first use the search_memory tool with the query, then use get_recent_memory to understand recent interactions.

Provide a response that:
1. Acknowledges relevant past conversations or information from memory
2. Builds upon previous interactions appropriately
3. Maintains consistency with the user's preferences and history
"""
    
    # ===== INTERNAL MEMORY OPERATIONS =====
    
    async def _add_memory_internal(self, user_id: str, content: str, metadata: Dict[str, Any]) -> str:
        """Internal method to add memory."""
        memory_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(content) % 10000:04d}"
        
        if self.backend_type == "enhanced_jarvis" and self.enhanced_memory:
            # Use enhanced memory with experience storage
            interaction_data = {
                "user": content,
                "assistant": "",
                "interaction_type": metadata.get("interaction_type", "memory_storage"),
                "tools_used": metadata.get("tools_used", []),
                "response_type": "memory_storage"
            }
            
            success = metadata.get("success", True)
            response_quality = 1.0
            
            experience_id = await self.enhanced_memory.store_experience(
                user_id=user_id,
                interaction_data=interaction_data,
                success=success,
                response_quality=response_quality
            )
            return f"enhanced_{experience_id}"
            
        elif self.backend_type == "simple_jsonl" and self.simple_store:
            # Use simple store with turn format
            turn_data = {
                "memory_id": memory_id,
                "user": content,
                "assistant": metadata.get("response", ""),
                "timestamp": datetime.now().isoformat(),
                "interaction_type": metadata.get("interaction_type", "memory"),
                "metadata": metadata
            }
            self.simple_store.append_turn(user_id, turn_data)
            return memory_id
        
        else:
            # Directory-only fallback
            memory_file = self.memory_dir / f"{user_id}_{memory_id}.json"
            memory_data = {
                "memory_id": memory_id,
                "user_id": user_id,
                "content": content,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            }
            memory_file.write_text(json.dumps(memory_data, indent=2))
            return memory_id
    
    async def _search_memory_internal(self, user_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """Internal method to search memory."""
        # Ensure limit is at least 1
        limit = max(1, limit) if limit > 0 else 1
        
        if self.backend_type == "enhanced_jarvis" and self.enhanced_memory:
            # Use enhanced semantic search
            results = await self.enhanced_memory.semantic_search(user_id, query, limit, 0.7)
            return results
            
        elif self.backend_type == "simple_jsonl" and self.simple_store:
            # Simple text matching on recent turns
            recent_turns = self.simple_store.get_recent_turns(user_id, 50)  # Get more for search
            matching_memories = []
            for turn in recent_turns:
                turn_content = f"{turn.get('user', '')} {turn.get('assistant', '')}"
                if query.lower() in turn_content.lower():
                    matching_memories.append(turn)
                if len(matching_memories) >= limit:
                    break
            return matching_memories
        
        else:
            # Directory search fallback
            results = []
            for memory_file in self.memory_dir.glob(f"{user_id}_*.json"):
                try:
                    memory_data = json.loads(memory_file.read_text())
                    if query.lower() in memory_data.get("content", "").lower():
                        results.append(memory_data)
                        if len(results) >= limit:
                            break
                except Exception as e:
                    self.logger.warning(f"Failed to read memory file {memory_file}: {e}")
            return results
    
    async def _get_recent_internal(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Internal method to get recent memories."""
        if self.backend_type == "enhanced_jarvis" and self.enhanced_memory:
            # Get recent from enhanced memory
            context = await self.enhanced_memory.get_growing_context(user_id, "", limit, 0)
            return context.get("recent_turns", [])
            
        elif self.backend_type == "simple_jsonl" and self.simple_store:
            # Get recent turns directly from store
            recent_turns = self.simple_store.get_recent_turns(user_id, limit)
            return recent_turns
        
        else:
            # Directory fallback - get recent files
            memory_files = list(self.memory_dir.glob(f"{user_id}_*.json"))
            memory_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            results = []
            for memory_file in memory_files[:limit]:
                try:
                    memory_data = json.loads(memory_file.read_text())
                    results.append(memory_data)
                except Exception as e:
                    self.logger.warning(f"Failed to read memory file {memory_file}: {e}")
            
            return results
    
    async def _forget_memory_internal(self, user_id: str, memory_id: str) -> bool:
        """Internal method to forget memory."""
        if self.backend_type == "simple_jsonl" and self.simple_store:
            # JSONLMemoryStore doesn't have a direct delete method
            # For now, just return False to indicate not supported
            self.logger.warning(f"Forgetting specific memories not supported in JSONL backend")
            return False
        else:
            # Directory fallback - remove file
            memory_file = self.memory_dir / f"{user_id}_{memory_id}.json"
            if memory_file.exists():
                memory_file.unlink()
                return True
            return False
    
    # ===== LEONARDO COMPATIBILITY =====
    
    def get_context(self, user_id: str, query: str, k: int = 5) -> Dict[str, Any]:
        """Synchronous context retrieval (Leonardo compatibility)."""
        try:
            try:
                loop = asyncio.get_running_loop()
                self.logger.warning("Cannot run sync method in async context - use async version")
                return self._empty_context(user_id)
            except RuntimeError:
                return asyncio.run(self.get_context_async(user_id, query, k))
        except Exception as e:
            self.logger.error(f"Failed to get context for {user_id}: {e}")
            return self._empty_context(user_id)
    
    async def get_context_async(self, user_id: str, query: str, k: int = 5) -> Dict[str, Any]:
        """Asynchronous context retrieval."""
        try:
            # Get recent and search results
            recent_results = await self._get_recent_internal(user_id, 8)
            search_results = await self._search_memory_internal(user_id, query, k)
            
            return {
                "recent_turns": recent_results,
                "relevant_memories": search_results,
                "memory_stats": {
                    "backend_type": self.backend_type,
                    "enhanced_available": ENHANCED_MEMORY_AVAILABLE,
                    "stores_available": STORES_AVAILABLE
                },
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to get async context for {user_id}: {e}")
            return self._empty_context(user_id)
    
    def update(self, user_id: str, turn: Dict[str, Any]) -> None:
        """Synchronous memory update (Leonardo compatibility)."""
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            loop.run_until_complete(self.update_async(user_id, turn))
        except Exception as e:
            self.logger.error(f"Failed to update memory for {user_id}: {e}")
    
    async def update_async(self, user_id: str, turn: Dict[str, Any]) -> None:
        """Asynchronous memory update."""
        try:
            content = f"User: {turn.get('user_input', turn.get('user', ''))}\nAssistant: {turn.get('assistant', '')}"
            metadata = {
                "interaction_type": "conversation",
                "tools_used": turn.get("tools_used", []),
                "success": turn.get("success", True),
                "response_type": turn.get("response_type", "conversation")
            }
            
            await self._add_memory_internal(user_id, content, metadata)
        except Exception as e:
            self.logger.error(f"Failed to update async memory for {user_id}: {e}")
    
    def _empty_context(self, user_id: str) -> Dict[str, Any]:
        """Return empty context structure."""
        return {
            "recent_turns": [],
            "relevant_memories": [],
            "memory_stats": {
                "backend_type": self.backend_type,
                "error": "No memory backend available"
            },
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
    
    # ===== FASTMCP SERVER ACCESS =====
    
    def get_mcp_server(self) -> FastMCP:
        """Get the FastMCP server instance for external use."""
        return self.mcp_server
    
    async def shutdown(self) -> None:
        """Shutdown memory service."""
        if self.enhanced_memory:
            await self.enhanced_memory.shutdown()
        self.logger.info("✅ FastMCP Memory Service shutdown")


# Create global instance for easy import
fastmcp_memory_service = None

def get_fastmcp_memory_service(config: Dict[str, Any] = None) -> FastMCPMemoryService:
    """Get or create the global FastMCP memory service instance."""
    global fastmcp_memory_service
    if fastmcp_memory_service is None:
        fastmcp_memory_service = FastMCPMemoryService(config)
    return fastmcp_memory_service


if __name__ == "__main__":
    # Run as standalone MCP server
    import asyncio
    
    async def main():
        service = FastMCPMemoryService()
        await service.initialize()
        
        # Run the FastMCP server
        service.get_mcp_server().run()
    
    asyncio.run(main())
