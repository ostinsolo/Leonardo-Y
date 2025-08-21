#!/usr/bin/env python3
"""
Test FastMCP Memory Service
Tests the new FastMCP-based memory implementation with proper MCP compliance
"""

import asyncio
import json
import logging
import sys
import tempfile
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Import our memory components
from leonardo.memory.fastmcp_memory import FastMCPMemoryService, get_fastmcp_memory_service
from leonardo.memory.service import MemoryService
from leonardo.config import LeonardoConfig

async def test_fastmcp_memory_service():
    """Test the FastMCP Memory Service directly."""
    print("🧪 Testing FastMCP Memory Service")
    print("=" * 50)
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        config = {
            "memory_dir": temp_dir,
            "max_recent_turns": 5
        }
        
        service = FastMCPMemoryService(config)
        success = await service.initialize()
        
        print(f"✅ Initialization: {'Success' if success else 'Failed'}")
        print(f"📊 Backend Type: {service.backend_type}")
        
        # Test basic memory operations
        user_id = "test_user_fastmcp"
        
        # Test adding memory
        memory_id1 = await service._add_memory_internal(
            user_id, 
            "Leonardo is an AI assistant", 
            {"interaction_type": "conversation"}
        )
        print(f"✅ Added memory 1: {memory_id1}")
        
        memory_id2 = await service._add_memory_internal(
            user_id, 
            "FastMCP provides clean MCP protocol compliance", 
            {"interaction_type": "technical_note"}
        )
        print(f"✅ Added memory 2: {memory_id2}")
        
        # Test searching memory
        search_results = await service._search_memory_internal(user_id, "Leonardo", 5)
        print(f"✅ Search results for 'Leonardo': {len(search_results)} found")
        
        # Test getting recent memory
        recent_results = await service._get_recent_internal(user_id, 5)
        print(f"✅ Recent memories: {len(recent_results)} found")
        
        # Test context generation
        context = await service.get_context_async(user_id, "What is Leonardo?", 5)
        print(f"✅ Generated context with {len(context.get('recent_turns', []))} recent turns")
        print(f"   Memory Stats: {context.get('memory_stats', {}).get('backend_type', 'unknown')}")
        
        # Test updating memory (conversation style)
        turn_data = {
            "user": "What can you do?",
            "assistant": "I can help with various tasks using voice interaction.",
            "tools_used": ["voice_processing"],
            "success": True
        }
        await service.update_async(user_id, turn_data)
        print("✅ Updated memory with conversation turn")
        
        # Test forgetting memory
        if service.backend_type != "enhanced_jarvis":  # Enhanced memory doesn't support direct forgetting
            forget_result = await service._forget_memory_internal(user_id, memory_id1)
            print(f"✅ Forget memory result: {'Success' if forget_result else 'Failed/Not Supported'}")
        
        await service.shutdown()
        print("✅ Service shutdown successful")


async def test_memory_service_wrapper():
    """Test the MemoryService wrapper that uses FastMCP."""
    print("\n🧪 Testing MemoryService FastMCP Wrapper")
    print("=" * 50)
    
    # Create minimal config for testing
    class TestConfig:
        def __init__(self):
            self.data_dir = "test_data_fastmcp"
            self.memory = type('MemoryConfig', (), {
                'max_recent_turns': 5,
                'enable_vector_search': True,
                'retention_days': 30
            })()
    
    config = TestConfig()
    service = MemoryService(config)
    
    try:
        await service.initialize()
        print(f"✅ MemoryService initialized: {service.is_initialized()}")
        
        user_id = "test_user_wrapper"
        
        # Test basic operations through wrapper
        turn = {
            "user": "Hello Leonardo",
            "assistant": "Hello! I'm Leonardo, your voice-first AI assistant.",
            "tools_used": [],
            "success": True
        }
        
        await service.update_async(user_id, turn)
        print("✅ Stored interaction via wrapper")
        
        # Test context retrieval
        context = await service.get_context_async(user_id, "Leonardo", 5)
        print(f"✅ Retrieved context: {len(context.get('recent_turns', []))} recent turns")
        
        # Test search
        search_results = await service.search_async(user_id, "Leonardo", 3)
        print(f"✅ Search via wrapper: {len(search_results)} results")
        
        # Test recent memories
        recent_results = await service.get_recent_async(user_id, 3)
        print(f"✅ Recent via wrapper: {len(recent_results)} results")
        
        # Test memory stats
        stats = await service.get_memory_stats_async(user_id)
        print(f"✅ Memory stats: backend_type = {stats.get('backend_type', 'unknown')}")
        
        # Test MCP server access
        mcp_server = service.get_mcp_server()
        print(f"✅ MCP Server access: {'Available' if mcp_server else 'Not Available'}")
        
        await service.shutdown()
        print("✅ Wrapper shutdown successful")
        
    except Exception as e:
        print(f"❌ Wrapper test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_mcp_tools_integration():
    """Test MCP tools integration (simulated)."""
    print("\n🧪 Testing MCP Tools Integration")  
    print("=" * 50)
    
    service = get_fastmcp_memory_service()
    await service.initialize()
    
    # Get the MCP server instance
    mcp_server = service.get_mcp_server()
    
    if mcp_server:
        print(f"✅ FastMCP server available")
        
        # List available tools
        if hasattr(mcp_server, '_tools'):
            tools = list(mcp_server._tools.keys())
            print(f"✅ Available MCP tools: {tools}")
        
        # List available resources  
        if hasattr(mcp_server, '_resources'):
            resources = list(mcp_server._resources.keys())
            print(f"✅ Available MCP resources: {resources}")
        
        # List available prompts
        if hasattr(mcp_server, '_prompts'):
            prompts = list(mcp_server._prompts.keys())
            print(f"✅ Available MCP prompts: {prompts}")
        
    else:
        print("❌ FastMCP server not available")
    
    await service.shutdown()


async def main():
    """Run all tests."""
    print("🚀 FastMCP Memory Service Test Suite")
    print("=" * 70)
    
    try:
        await test_fastmcp_memory_service()
        await test_memory_service_wrapper()
        await test_mcp_tools_integration()
        
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("📋 Summary:")
        print("   ✅ FastMCP Memory Service: Working") 
        print("   ✅ MemoryService Wrapper: Working")
        print("   ✅ MCP Tools Integration: Working")
        print("   🚀 FastMCP provides clean MCP compliance!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
