"""
Leonardo Memory System (MCP-Compatible + JARVIS-1 Enhanced)
Provides three-tier memory: short-term, episodic, and long-term memory
Uses Model Context Protocol (MCP) interface with swappable backends
Enhanced with JARVIS-1 inspired semantic clustering and growing memory
"""

from .service import MemoryService
from .mcp_compliant_interface import MCPCompliantInterface
from .enhanced_memory import EnhancedMemorySystem, ADVANCED_MEMORY_AVAILABLE

# Legacy stores (for reference/migration)
from .stores import SQLiteMemoryStore, JSONLMemoryStore

__all__ = [
    'MemoryService', 
    'MCPCompliantInterface',     # MCP-compliant interface
    'EnhancedMemorySystem',      # JARVIS-1 advanced features
    'ADVANCED_MEMORY_AVAILABLE', # Feature flag
    'SQLiteMemoryStore', 
    'JSONLMemoryStore'
]
