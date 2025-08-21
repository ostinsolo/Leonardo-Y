"""
Leonardo Memory Service (FastMCP-Compatible)
Clean wrapper around FastMCP Memory Service for backward compatibility
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..config import LeonardoConfig
from .fastmcp_memory import FastMCPMemoryService


class MemoryService:
    """
    Leonardo's Memory Service - FastMCP-Compatible wrapper.
    Provides backward compatibility while using FastMCP Memory Service.
    """
    
    def __init__(self, config: LeonardoConfig, store=None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.initialized = False
        
        # Initialize FastMCP Memory Service
        self.fastmcp_service: Optional[FastMCPMemoryService] = None
        
        # Configuration from memory config
        memory_config = getattr(config, 'memory', {})
        self.max_recent_turns = getattr(memory_config, 'max_recent_turns', 8)
        self.summary_target_tokens = getattr(memory_config, 'summary_target_tokens', 200)
        self.enable_vector_search = getattr(memory_config, 'enable_vector_search', True)
        self.retention_days = getattr(memory_config, 'retention_days', 30)
        
        self.logger.info("🚀 Memory Service (FastMCP-Compatible) initialized")
    
    async def initialize(self) -> None:
        """Initialize FastMCP memory service."""
        try:
            # Create FastMCP service with config
            fastmcp_config = {
                "memory_dir": str(Path(self.config.data_dir) / "leonardo_fastmcp_memory"),
                "max_recent_turns": self.max_recent_turns,
                "enable_vector_search": self.enable_vector_search,
                "retention_days": self.retention_days
            }
            
            self.fastmcp_service = FastMCPMemoryService(fastmcp_config)
            success = await self.fastmcp_service.initialize()
            
            if success:
                self.initialized = True
                self.logger.info("✅ Memory Service ready (FastMCP-Compatible)")
            else:
                self.logger.error("❌ FastMCP Memory Service initialization failed")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize FastMCP memory service: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown FastMCP memory service."""
        if self.fastmcp_service:
            await self.fastmcp_service.shutdown()
        self.initialized = False
        self.logger.info("✅ Memory Service shutdown")
    
    def get_context(self, user_id: str, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Return comprehensive context for the Planner using FastMCP service.
        Synchronous wrapper around async FastMCP operations.
        """
        try:
            if not self.fastmcp_service or not self.initialized:
                self.logger.warning("FastMCP service not initialized")
                return self._empty_context(user_id)
            
            # Handle running event loop properly
            try:
                # Try to get the current loop
                loop = asyncio.get_running_loop()
                # If we're in a running loop, we need to use a different approach
                # For now, return empty context and log the issue
                self.logger.warning("Cannot run sync method in async context - use async version")
                return self._empty_context(user_id)
                
            except RuntimeError:
                # No running loop, we can create one
                context = asyncio.run(
                    self.fastmcp_service.get_context_async(user_id, query, k)
                )
                
                self.logger.debug(f"Generated FastMCP context for {user_id}: "
                                f"{len(context.get('recent_turns', []))} recent turns")
                
                return context
                
        except Exception as e:
            self.logger.error(f"Failed to get FastMCP context for {user_id}: {e}")
            return self._empty_context(user_id)
    
    async def get_context_async(self, user_id: str, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Async version of get_context - preferred for async environments.
        """
        try:
            if not self.fastmcp_service or not self.initialized:
                self.logger.warning("FastMCP service not initialized")
                return self._empty_context(user_id)
            
            context = await self.fastmcp_service.get_context_async(user_id, query, k)
            
            self.logger.debug(f"Generated async FastMCP context for {user_id}: "
                            f"{len(context.get('recent_turns', []))} recent turns")
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get async FastMCP context for {user_id}: {e}")
            return self._empty_context(user_id)
    
    def update(self, user_id: str, turn: Dict[str, Any]) -> None:
        """
        Store interaction turn using FastMCP service.
        Synchronous wrapper around async operations.
        """
        try:
            if not self.fastmcp_service or not self.initialized:
                self.logger.warning("FastMCP service not initialized")
                return
            
            # Handle running event loop properly
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, can't run sync
                self.logger.warning("Cannot run sync update in async context - use update_async")
                return
                
            except RuntimeError:
                # No running loop, we can create one
                asyncio.run(self.fastmcp_service.update_async(user_id, turn))
                
                self.logger.debug(f"Stored FastMCP interaction for {user_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to update FastMCP memory for {user_id}: {e}")
    
    async def update_async(self, user_id: str, turn: Dict[str, Any]) -> None:
        """
        Async version of update - preferred for async environments.
        """
        try:
            if not self.fastmcp_service or not self.initialized:
                self.logger.warning("FastMCP service not initialized")
                return
            
            await self.fastmcp_service.update_async(user_id, turn)
            
            self.logger.debug(f"Stored async FastMCP interaction for {user_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update async FastMCP memory for {user_id}: {e}")
    
    def _empty_context(self, user_id: str) -> Dict[str, Any]:
        """Return empty context structure."""
        return {
            "recent_turns": [],
            "relevant_memories": [],
            "user_profile": {},
            "memory_stats": {
                "backend_type": "fastmcp_unavailable",
                "error": "FastMCP Memory Service not available or not initialized"
            },
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
    
    # ===== ADDITIONAL COMPATIBILITY METHODS =====
    
    def store_interaction(self, user_id: str, interaction_data: Dict[str, Any]) -> str:
        """Store interaction data (legacy compatibility)."""
        try:
            self.update(user_id, interaction_data)
            return f"interaction_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        except Exception as e:
            self.logger.error(f"Failed to store interaction for {user_id}: {e}")
            return ""
    
    async def store_interaction_async(self, user_id: str, interaction_data: Dict[str, Any]) -> str:
        """Async version of store_interaction."""
        try:
            await self.update_async(user_id, interaction_data)
            return f"interaction_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        except Exception as e:
            self.logger.error(f"Failed to store async interaction for {user_id}: {e}")
            return ""
    
    def search(self, user_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search memories (legacy compatibility)."""
        context = self.get_context(user_id, query, k)
        return context.get("relevant_memories", [])
    
    async def search_async(self, user_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Async version of search."""
        if not self.fastmcp_service or not self.initialized:
            return []
        
        try:
            results = await self.fastmcp_service._search_memory_internal(user_id, query, k)
            return results
        except Exception as e:
            self.logger.error(f"Failed to search FastMCP memory for {user_id}: {e}")
            return []
    
    def get_recent(self, user_id: str, k: int = 10) -> List[Dict[str, Any]]:
        """Get recent memories (legacy compatibility)."""
        context = self.get_context(user_id, "", k)
        return context.get("recent_turns", [])
    
    async def get_recent_async(self, user_id: str, k: int = 10) -> List[Dict[str, Any]]:
        """Async version of get_recent."""
        if not self.fastmcp_service or not self.initialized:
            return []
        
        try:
            results = await self.fastmcp_service._get_recent_internal(user_id, k)
            return results
        except Exception as e:
            self.logger.error(f"Failed to get recent FastMCP memories for {user_id}: {e}")
            return []
    
    def forget(self, user_id: str, memory_id: str) -> bool:
        """Forget a memory (legacy compatibility)."""
        if not self.fastmcp_service or not self.initialized:
            return False
        
        try:
            try:
                loop = asyncio.get_running_loop()
                self.logger.warning("Cannot run sync forget in async context")
                return False
            except RuntimeError:
                return asyncio.run(self.fastmcp_service._forget_memory_internal(user_id, memory_id))
        except Exception as e:
            self.logger.error(f"Failed to forget FastMCP memory for {user_id}: {e}")
            return False
    
    async def forget_async(self, user_id: str, memory_id: str) -> bool:
        """Async version of forget."""
        if not self.fastmcp_service or not self.initialized:
            return False
        
        try:
            return await self.fastmcp_service._forget_memory_internal(user_id, memory_id)
        except Exception as e:
            self.logger.error(f"Failed to forget async FastMCP memory for {user_id}: {e}")
            return False
    
    def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics."""
        if not self.fastmcp_service or not self.initialized:
            return {"error": "FastMCP service not initialized"}
        
        try:
            try:
                loop = asyncio.get_running_loop()
                self.logger.warning("Cannot run sync get_memory_stats in async context")
                return {"error": "Cannot run sync in async context"}
            except RuntimeError:
                # Run the resource method synchronously
                stats_json = asyncio.run(self.fastmcp_service.mcp_server._resources["memory_stats"](user_id))
                import json
                return json.loads(stats_json)
        except Exception as e:
            self.logger.error(f"Failed to get FastMCP memory stats for {user_id}: {e}")
            return {"error": str(e)}
    
    async def get_memory_stats_async(self, user_id: str) -> Dict[str, Any]:
        """Async version of get_memory_stats."""
        if not self.fastmcp_service or not self.initialized:
            return {"error": "FastMCP service not initialized"}
        
        try:
            stats_json = await self.fastmcp_service.mcp_server._resources["memory_stats"](user_id)
            import json
            return json.loads(stats_json)
        except Exception as e:
            self.logger.error(f"Failed to get async FastMCP memory stats for {user_id}: {e}")
            return {"error": str(e)}
    
    # ===== FASTMCP SERVER ACCESS =====
    
    def get_mcp_server(self):
        """Get the FastMCP server for direct MCP integration."""
        if self.fastmcp_service:
            return self.fastmcp_service.get_mcp_server()
        return None
    
    def is_initialized(self) -> bool:
        """Check if the service is properly initialized."""
        return self.initialized and self.fastmcp_service is not None
