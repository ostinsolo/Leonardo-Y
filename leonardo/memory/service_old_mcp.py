"""
Leonardo Memory Service (MCP-Compatible)
Wrapper around MCP Memory Interface for backward compatibility
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..config import LeonardoConfig
from .fastmcp_memory import FastMCPMemoryService


class MemoryService:
    """
    Leonardo's Memory Service - MCP-Compatible wrapper.
    Provides backward compatibility while using MCP Memory Interface.
    """
    
    def __init__(self, config: LeonardoConfig, store=None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize MCP-compliant interface
        self.mcp_interface: Optional[MCPCompliantInterface] = None
        
        # Configuration from memory config
        memory_config = getattr(config, 'memory', {})
        self.max_recent_turns = getattr(memory_config, 'max_recent_turns', 8)
        self.summary_target_tokens = getattr(memory_config, 'summary_target_tokens', 200)
        self.enable_vector_search = getattr(memory_config, 'enable_vector_search', True)
        self.retention_days = getattr(memory_config, 'retention_days', 30)
        
        self.logger.info("🧠 Memory Service (MCP-Compatible) initialized")
    
    async def initialize(self) -> None:
        """Initialize MCP memory interface."""
        try:
            # Create MCP interface with config
            mcp_config = {
                "max_recent_turns": self.max_recent_turns,
                "enable_vector_search": self.enable_vector_search,
                "retention_days": self.retention_days
            }
            
            self.mcp_interface = MCPCompliantInterface(mcp_config)
            await self.mcp_interface.initialize()
            
            self.logger.info("✅ Memory Service ready (MCP-Compatible)")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize MCP memory interface: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown MCP memory interface."""
        if self.mcp_interface:
            await self.mcp_interface.shutdown()
        self.logger.info("✅ Memory Service shutdown")
    
    def get_context(self, user_id: str, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Return comprehensive context for the Planner using MCP interface.
        Synchronous wrapper around async MCP operations.
        """
        try:
            if not self.mcp_interface:
                self.logger.warning("MCP interface not initialized")
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
                    self.mcp_interface.get_context_for_planner(user_id, query)
                )
                
                self.logger.debug(f"Generated MCP context for {user_id}: "
                                f"{len(context.get('recent_turns', []))} recent turns")
                
                return context
                
        except Exception as e:
            self.logger.error(f"Failed to get MCP context for {user_id}: {e}")
            return self._empty_context(user_id)
    
    async def get_context_async(self, user_id: str, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Async version of get_context - preferred for async environments.
        """
        try:
            if not self.mcp_interface:
                self.logger.warning("MCP interface not initialized")
                return self._empty_context(user_id)
            
            context = await self.mcp_interface.get_context_for_planner(user_id, query)
            
            self.logger.debug(f"Generated MCP context for {user_id}: "
                            f"{len(context.get('recent_turns', []))} recent turns")
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get MCP context for {user_id}: {e}")
            return self._empty_context(user_id)
    
    def _empty_context(self, user_id: str) -> Dict[str, Any]:
        """Return empty context structure."""
        return {
            "recent_turns": [],
            "relevant_memories": [],
            "user_profile": {},
            "conversation_summary": "",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
    
    def update(self, user_id: str, turn: Dict[str, Any]) -> None:
        """
        Persist complete turn results using MCP interface.
        Synchronous wrapper around async MCP operations.
        """
        try:
            if not self.mcp_interface:
                self.logger.warning("MCP interface not initialized")
                return
            
            # Use asyncio to run async MCP method
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Store interaction using MCP interface
            memory_id = loop.run_until_complete(
                self.mcp_interface.store_interaction(user_id, turn)
            )
            
            self.logger.debug(f"Updated MCP memory for {user_id}: {memory_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update MCP memory for {user_id}: {e}")
    
    async def update_async(self, user_id: str, turn: Dict[str, Any]) -> None:
        """
        Async version of update for use in async contexts.
        Persist complete turn results using MCP interface.
        """
        try:
            if not self.mcp_interface:
                self.logger.warning("MCP interface not initialized")
                return
                
            memory_id = await self.mcp_interface.store_interaction(user_id, turn)
            self.logger.debug(f"Updated MCP memory for {user_id}: {memory_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update MCP memory for {user_id}: {e}")
    
    def teach_synonym(self, user_id: str, phrase: str, canonical: str, scope: str = "general") -> bool:
        """Store a user-taught synonym using MCP interface."""
        try:
            if not self.mcp_interface:
                self.logger.warning("MCP interface not initialized")
                return False
            
            # Use asyncio to run async MCP method
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Store synonym as a memory item
            content = f"User taught synonym: '{phrase}' means '{canonical}'"
            metadata = {
                "type": "synonym",
                "phrase": phrase,
                "canonical": canonical,
                "scope": scope
            }
            
            memory_id = loop.run_until_complete(
                self.mcp_interface.add(user_id, content, metadata)
            )
            
            return bool(memory_id)
            
        except Exception as e:
            self.logger.error(f"Failed to teach synonym '{phrase}' -> '{canonical}': {e}")
            return False
    
    def forget_memory(self, user_id: str, memory_type: str, identifier: str = None, 
                     date_range: tuple = None) -> bool:
        """Delete specific memories using MCP interface."""
        try:
            if not self.mcp_interface:
                self.logger.warning("MCP interface not initialized")
                return False
            
            # Use asyncio to run async MCP method
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Use MCP forget operation
            if memory_type == "all":
                # Search for all memories and delete them
                success = loop.run_until_complete(
                    self.mcp_interface.forget(user_id, query="*")
                )
            elif identifier:
                success = loop.run_until_complete(
                    self.mcp_interface.forget(user_id, memory_id=identifier)
                )
            else:
                success = loop.run_until_complete(
                    self.mcp_interface.forget(user_id, query=memory_type)
                )
            
            return success
                
        except Exception as e:
            self.logger.error(f"Failed to forget {memory_type} memory: {e}")
            return False
    
    def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory usage statistics."""
        try:
            if not self.mcp_interface:
                return {"error": "MCP interface not initialized"}
            
            # Use asyncio to run async MCP method
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Get recent memories to estimate stats
            recent = loop.run_until_complete(
                self.mcp_interface.get_recent(user_id, limit=100)
            )
            
            backend_info = self.mcp_interface.get_backend_info()
            
            return {
                "recent_turns": len(recent),
                "backend_type": backend_info["backend_type"],
                "mcp_available": backend_info["mcp_available"],
                "mem0_available": backend_info["mem0_available"],
                "operations": backend_info["operations"],
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get memory stats for {user_id}: {e}")
            return {"error": str(e)}
    
    def resolve_synonym(self, user_id: str, phrase: str) -> Optional[str]:
        """Resolve a phrase to its canonical form using MCP interface."""
        try:
            if not self.mcp_interface:
                return None
            
            # Use asyncio to run async MCP method
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Search for synonym memories
            results = loop.run_until_complete(
                self.mcp_interface.search(user_id, f"synonym {phrase}", limit=5)
            )
            
            # Look for exact phrase match in synonym memories
            for result in results:
                content = result.get("content", "")
                metadata = result.get("metadata", {})
                
                if metadata.get("type") == "synonym" and metadata.get("phrase") == phrase.lower():
                    return metadata.get("canonical")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to resolve synonym '{phrase}': {e}")
            return None
    
    def update(self, user_id: str, turn_data: Dict[str, Any]) -> bool:
        """
        Update memory with new turn data - Leonardo's main interface.
        This is called by main.py after each conversation turn.
        """
        try:
            if not self.mcp_interface:
                self.logger.warning("MCP interface not initialized")
                return False
            
            # Use asyncio to run async MCP method
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Store the interaction using MCP interface
            memory_id = loop.run_until_complete(
                self.mcp_interface.store_interaction(user_id, turn_data)
            )
            
            success = bool(memory_id)
            if success:
                self.logger.debug(f"💾 Stored turn for {user_id}: {memory_id}")
            else:
                self.logger.warning(f"Failed to store turn for {user_id}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update memory for {user_id}: {e}")
            return False
    
    async def store_interaction_async(self, user_id: str, interaction: Dict[str, Any]) -> str:
        """
        Async version of store_interaction - preferred for async environments.
        """
        try:
            if not self.mcp_interface:
                self.logger.warning("MCP interface not initialized")
                return ""
            
            memory_id = await self.mcp_interface.store_interaction(user_id, interaction)
            
            if memory_id:
                self.logger.debug(f"💾 Stored interaction for {user_id}: {memory_id}")
            else:
                self.logger.warning(f"Failed to store interaction for {user_id}")
                
            return memory_id
            
        except Exception as e:
            self.logger.error(f"Failed to store interaction for {user_id}: {e}")
            return ""
    
    def store_interaction(self, user_id: str, interaction: Dict[str, Any]) -> str:
        """
        Store interaction - synchronous wrapper for compatibility.
        """
        try:
            # Use asyncio to run async MCP method
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            memory_id = loop.run_until_complete(
                self.store_interaction_async(user_id, interaction)
            )
            
            return memory_id
            
        except Exception as e:
            self.logger.error(f"Failed to store interaction for {user_id}: {e}")
            return ""