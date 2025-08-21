"""
Test MCP Memory Compliance for Leonardo

This test verifies that Leonardo's memory system is fully MCP-compliant
and can use the official MCP Memory Service with proper fallbacks.
"""

import asyncio
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo.memory.mcp_compliant_interface import MCPCompliantInterface, create_mcp_compliant_interface
from leonardo.memory.service import MemoryService
from leonardo.config import LeonardoConfig

async def test_mcp_memory_backends():
    """Test different MCP memory backends."""
    print("🔍 Testing MCP Memory Backends...")
    
    # Test configurations for different backends
    test_configs = [
        {
            "name": "Simple Fallback (Safe)",
            "config": {
                "storage_backend": "simple_fallback",
                "collection_name": "leonardo_test_simple", 
                "memory_dir": "test_mcp_simple"
            }
        },
        {
            "name": "MCP SQLite-vec (Modern)",
            "config": {
                "storage_backend": "sqlite_vec", 
                "collection_name": "leonardo_test_sqlite_vec",
                "memory_dir": "test_mcp_sqlite_vec"
            }
        },
        {
            "name": "Enhanced Fallback",
            "config": {
                "storage_backend": "enhanced_fallback",
                "memory_dir": "test_enhanced_fallback"
            }
        }
    ]
    
    results = {}
    
    for test_case in test_configs:
        name = test_case["name"]
        config = test_case["config"]
        
        print(f"\n🧪 Testing {name}...")
        
        try:
            # Create interface
            interface = MCPCompliantInterface(config)
            success = await interface.initialize()
            
            if not success:
                results[name] = {"status": "failed", "error": "initialization failed"}
                continue
            
            # Get backend info
            backend_info = interface.get_mcp_info()
            print(f"   Backend: {backend_info['backend_type']}")
            print(f"   MCP Compliant: {backend_info['mcp_compliant']}")
            
            # Test basic MCP operations
            test_user_id = "test_user_001"
            
            # Test ADD operation
            memory_id = await interface.add(
                test_user_id, 
                "Test memory content for MCP compliance",
                {"test": True, "backend": backend_info['backend_type']}
            )
            
            if not memory_id:
                results[name] = {"status": "failed", "error": "add operation failed"}
                await interface.shutdown()
                continue
            
            # Test SEARCH operation
            search_results = await interface.search(test_user_id, "test memory", limit=5)
            
            # Test GET_RECENT operation
            recent_results = await interface.get_recent(test_user_id, limit=3)
            
            # Test context retrieval (Leonardo integration)
            context = await interface.get_context_for_planner(test_user_id, "test query")
            
            results[name] = {
                "status": "success",
                "backend_type": backend_info['backend_type'],
                "mcp_compliant": backend_info['mcp_compliant'],
                "memory_id": memory_id,
                "search_results": len(search_results),
                "recent_results": len(recent_results),
                "context_keys": list(context.keys())
            }
            
            print(f"   ✅ {name}: All operations successful")
            print(f"      Memory ID: {memory_id}")
            print(f"      Search results: {len(search_results)}")
            print(f"      Recent results: {len(recent_results)}")
            
            # Test FORGET operation
            if memory_id:
                forgot = await interface.forget(test_user_id, memory_id=memory_id)
                print(f"      Forget operation: {'✅' if forgot else '⚠️'}")
            
            await interface.shutdown()
            
        except Exception as e:
            results[name] = {"status": "error", "error": str(e)}
            print(f"   ❌ {name}: {e}")
    
    return results

async def test_memory_service_integration():
    """Test full MemoryService integration with MCP compliance."""
    print("\n🔗 Testing MemoryService Integration...")
    
    try:
        # Create mock Leonardo config
        config = LeonardoConfig()
        
        # Create MemoryService (which should use MCP-compliant interface)
        memory_service = MemoryService(config)
        await memory_service.initialize()
        
        print(f"   ✅ MemoryService initialized")
        
        # Test storing interaction (Leonardo's main use case)
        user_id = "integration_test_user"
        interaction = {
            "user": "Hello, my name is Alice and I like programming",
            "assistant": "Nice to meet you, Alice! I'd be happy to help with programming questions.",
            "success": True,
            "tools_used": [],
            "response_type": "conversation"
        }
        
        memory_id = await memory_service.store_interaction(user_id, interaction)
        print(f"   💾 Stored interaction: {memory_id}")
        
        # Test retrieving context for planner
        context = await memory_service.get_context_for_planner(user_id, "programming help")
        
        print(f"   🧠 Context retrieval:")
        print(f"      Recent turns: {len(context.get('recent_turns', []))}")
        print(f"      Relevant memories: {len(context.get('relevant_memories', []))}")
        print(f"      User profile: {context.get('user_profile', {})}")
        print(f"      Memory stats: {context.get('memory_stats', {})}")
        
        # Test recall functionality
        if context.get('recent_turns'):
            recent_turn = context['recent_turns'][0]
            print(f"      Latest turn content: {recent_turn.get('content', '')[:50]}...")
            print(f"      User input: {recent_turn.get('user_input', 'N/A')[:30]}...")
            print(f"      AI response: {recent_turn.get('ai_response', 'N/A')[:30]}...")
        
        await memory_service.shutdown()
        
        return {
            "status": "success",
            "memory_id": memory_id,
            "context_keys": list(context.keys()),
            "recent_count": len(context.get('recent_turns', [])),
            "backend_info": context.get('memory_stats', {})
        }
        
    except Exception as e:
        print(f"   ❌ MemoryService integration failed: {e}")
        return {"status": "error", "error": str(e)}

async def test_conversation_memory():
    """Test conversation memory flow (like Leonardo's actual usage)."""
    print("\n💬 Testing Conversation Memory Flow...")
    
    try:
        config = {
            "storage_backend": "simple_fallback",  # Use simple backend to avoid ChromaDB segfaults
            "collection_name": "leonardo_conversation_test",
            "memory_dir": "test_conversation_memory"
        }
        
        interface = await create_mcp_compliant_interface(config)
        backend_info = interface.get_mcp_info()
        
        print(f"   Using backend: {backend_info['backend_type']}")
        print(f"   MCP compliant: {backend_info['mcp_compliant']}")
        
        user_id = "conversation_test_user"
        
        # Simulate a conversation flow
        conversations = [
            {
                "user": "Hi, I'm Bob and I'm working on a Python project",
                "assistant": "Hello Bob! I'd be happy to help with your Python project. What are you working on?"
            },
            {
                "user": "I need help with async programming",
                "assistant": "Async programming in Python is great! Let me explain async/await patterns..."
            },
            {
                "user": "Can you remember what I told you about my project?",
                "assistant": "Yes, you mentioned you're Bob and you're working on a Python project. How can I help?"
            }
        ]
        
        # Store each conversation turn
        memory_ids = []
        for i, conv in enumerate(conversations):
            interaction = {
                **conv,
                "success": True,
                "tools_used": ["conversation"],
                "response_type": "conversation",
                "turn_number": i + 1
            }
            
            memory_id = await interface.store_interaction(user_id, interaction)
            memory_ids.append(memory_id)
            print(f"   💾 Turn {i+1} stored: {memory_id}")
        
        # Test memory recall at different points
        print(f"\n   🧠 Testing Memory Recall:")
        
        # Recent context
        recent = await interface.get_recent(user_id, limit=3)
        print(f"      Recent turns: {len(recent)}")
        
        # Search for specific topics
        python_search = await interface.search(user_id, "Python project", limit=5)
        print(f"      Python search results: {len(python_search)}")
        
        name_search = await interface.search(user_id, "Bob", limit=5)
        print(f"      Name search results: {len(name_search)}")
        
        # Get full context for planner (as Leonardo would)
        context = await interface.get_context_for_planner(user_id, "remember my project")
        print(f"      Planner context:")
        print(f"        Recent turns: {len(context.get('recent_turns', []))}")
        print(f"        Relevant memories: {len(context.get('relevant_memories', []))}")
        print(f"        User profile: {context.get('user_profile', {})}")
        
        # Verify conversation parsing
        if context.get('recent_turns'):
            latest = context['recent_turns'][0]
            print(f"        Latest user input: {latest.get('user_input', 'N/A')[:40]}...")
            print(f"        Latest AI response: {latest.get('ai_response', 'N/A')[:40]}...")
        
        await interface.shutdown()
        
        return {
            "status": "success",
            "backend_type": backend_info['backend_type'],
            "mcp_compliant": backend_info['mcp_compliant'],
            "conversations_stored": len(memory_ids),
            "memory_ids": memory_ids,
            "recall_stats": {
                "recent_count": len(recent),
                "python_results": len(python_search),
                "name_results": len(name_search),
                "context_available": bool(context.get('recent_turns'))
            }
        }
        
    except Exception as e:
        print(f"   ❌ Conversation memory test failed: {e}")
        return {"status": "error", "error": str(e)}

async def main():
    """Run all MCP compliance tests."""
    print("🚀 Starting MCP Memory Compliance Tests")
    print("=" * 60)
    
    # Test backend availability
    try:
        from mcp_memory_service import Memory, ChromaMemoryStorage
        print("✅ MCP Memory Service available")
    except ImportError as e:
        print(f"⚠️ MCP Memory Service not available: {e}")
    
    try:
        from leonardo.memory.enhanced_memory import EnhancedMemorySystem
        print("✅ Enhanced Memory available") 
    except ImportError as e:
        print(f"⚠️ Enhanced Memory not available: {e}")
    
    # Run tests
    results = {}
    
    # Test 1: Backend compatibility
    results["backends"] = await test_mcp_memory_backends()
    
    # Test 2: MemoryService integration
    results["integration"] = await test_memory_service_integration()
    
    # Test 3: Conversation flow
    results["conversation"] = await test_conversation_memory()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 MCP Compliance Test Results")
    print("=" * 60)
    
    # Backend results
    print("\n🔍 Backend Tests:")
    for backend, result in results["backends"].items():
        status = result["status"]
        emoji = "✅" if status == "success" else "❌"
        print(f"   {emoji} {backend}: {status}")
        if status == "success":
            print(f"      Backend: {result.get('backend_type', 'unknown')}")
            print(f"      MCP Compliant: {result.get('mcp_compliant', False)}")
    
    # Integration results
    print(f"\n🔗 Integration Test:")
    integration = results["integration"]
    status = integration["status"]
    emoji = "✅" if status == "success" else "❌"
    print(f"   {emoji} MemoryService: {status}")
    if status == "success":
        backend_info = integration.get("backend_info", {})
        print(f"      Backend: {backend_info.get('backend_type', 'unknown')}")
        print(f"      MCP Compliant: {backend_info.get('mcp_compliant', False)}")
    
    # Conversation results  
    print(f"\n💬 Conversation Test:")
    conversation = results["conversation"]
    status = conversation["status"]
    emoji = "✅" if status == "success" else "❌"
    print(f"   {emoji} Conversation Flow: {status}")
    if status == "success":
        print(f"      Backend: {conversation.get('backend_type', 'unknown')}")
        print(f"      MCP Compliant: {conversation.get('mcp_compliant', False)}")
        recall_stats = conversation.get('recall_stats', {})
        print(f"      Memory Recall: {recall_stats.get('context_available', False)}")
    
    # Overall compliance
    successful_tests = sum(1 for test_results in results.values() 
                          for result in (test_results.values() if isinstance(test_results, dict) else [test_results])
                          if isinstance(result, dict) and result.get("status") == "success")
    
    total_tests = sum(len(test_results) if isinstance(test_results, dict) else 1 
                     for test_results in results.values())
    
    compliance_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n🎯 Overall MCP Compliance: {compliance_rate:.1f}% ({successful_tests}/{total_tests} tests passed)")
    
    if compliance_rate >= 80:
        print("✅ MCP COMPLIANCE: EXCELLENT - Ready for production!")
    elif compliance_rate >= 60:
        print("⚠️ MCP COMPLIANCE: GOOD - Minor improvements needed")
    else:
        print("❌ MCP COMPLIANCE: NEEDS WORK - Major issues detected")

if __name__ == "__main__":
    asyncio.run(main())
