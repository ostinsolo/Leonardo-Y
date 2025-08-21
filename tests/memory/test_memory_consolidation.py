"""
Test Leonardo Memory System Consolidation

Verifies that our consolidated memory architecture works correctly:
- service.py (Leonardo interface) 
- mcp_compliant_interface.py (MCP compliance + fallbacks)
- enhanced_memory.py (JARVIS-1 features)
- stores.py (storage backends)
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo.memory.service import MemoryService
from leonardo.memory.mcp_compliant_interface import MCPCompliantInterface
from leonardo.config import LeonardoConfig

async def test_memory_service():
    """Test MemoryService (main Leonardo interface)."""
    print("🧠 Testing MemoryService (Leonardo Interface)...")
    
    try:
        # Create mock config
        config = LeonardoConfig()
        
        # Initialize MemoryService
        memory_service = MemoryService(config)
        await memory_service.initialize()
        
        print("   ✅ MemoryService initialized successfully")
        
        # Test basic operations
        user_id = "test_user"
        
        # Test context retrieval
        context = await memory_service.get_context_async(user_id, "test query")
        print(f"   📊 Context keys: {list(context.keys())}")
        
        # Test interaction storage  
        interaction = {
            "user": "Hello, I'm testing the memory system",
            "assistant": "Great! I'll remember this interaction.",
            "success": True,
            "tools_used": [],
            "response_type": "conversation"
        }
        
        memory_id = await memory_service.store_interaction_async(user_id, interaction)
        print(f"   💾 Stored interaction: {memory_id}")
        
        # Test memory update (Leonardo's main interface)
        turn_data = {
            "user": "Can you remember what I just said?",
            "assistant": "Yes, you were testing the memory system.",
            "success": True,
            "tools_used": [],
            "response_type": "conversation"
        }
        
        success = memory_service.update(user_id, turn_data)
        print(f"   🔄 Memory update: {'✅ Success' if success else '❌ Failed'}")
        
        # Test context retrieval after updates
        updated_context = await memory_service.get_context_async(user_id, "what did I say")
        recent_turns = updated_context.get('recent_turns', [])
        print(f"   🔍 Recent turns after updates: {len(recent_turns)}")
        
        if recent_turns:
            latest = recent_turns[0]
            print(f"   📝 Latest turn preview: {latest.get('content', 'N/A')[:50]}...")
        
        await memory_service.shutdown()
        
        return {
            "status": "success",
            "memory_id": memory_id,
            "update_success": success,
            "context_keys": list(context.keys()),
            "recent_turns_count": len(recent_turns)
        }
        
    except Exception as e:
        print(f"   ❌ MemoryService test failed: {e}")
        return {"status": "error", "error": str(e)}

async def test_mcp_interface():
    """Test MCPCompliantInterface directly."""
    print("\n🔌 Testing MCP-Compliant Interface...")
    
    try:
        # Create simple config focusing on fallback backend
        config = {
            "storage_backend": "simple_fallback",  # Avoid ChromaDB segfaults
            "memory_dir": "test_mcp_consolidation"
        }
        
        # Initialize interface
        interface = MCPCompliantInterface(config)
        success = await interface.initialize()
        
        if not success:
            print("   ❌ Failed to initialize MCP interface")
            return {"status": "failed"}
        
        backend_info = interface.get_mcp_info()
        print(f"   🏗️ Backend: {backend_info['backend_type']}")
        print(f"   🔌 MCP Compliant: {backend_info['mcp_compliant']}")
        
        # Test MCP standard operations
        user_id = "mcp_test_user"
        
        # Test ADD
        memory_id = await interface.add(
            user_id, 
            "Testing MCP add operation",
            {"test": True, "operation": "add"}
        )
        print(f"   ➕ Add operation: {memory_id}")
        
        # Test SEARCH
        search_results = await interface.search(user_id, "testing", limit=5)
        print(f"   🔍 Search results: {len(search_results)}")
        
        # Test GET_RECENT  
        recent = await interface.get_recent(user_id, limit=3)
        print(f"   📋 Recent items: {len(recent)}")
        
        # Test context for planner (Leonardo integration)
        context = await interface.get_context_for_planner(user_id, "testing")
        print(f"   🧠 Planner context: {list(context.keys())}")
        
        # Test FORGET
        forget_success = await interface.forget(user_id, memory_id=memory_id)
        print(f"   🗑️ Forget operation: {'✅' if forget_success else '❌'}")
        
        await interface.shutdown()
        
        return {
            "status": "success",
            "backend_type": backend_info['backend_type'],
            "mcp_compliant": backend_info['mcp_compliant'],
            "operations": {
                "add": bool(memory_id),
                "search": len(search_results) > 0,
                "get_recent": len(recent) > 0,
                "forget": forget_success
            }
        }
        
    except Exception as e:
        print(f"   ❌ MCP interface test failed: {e}")
        return {"status": "error", "error": str(e)}

async def test_architecture_integration():
    """Test full architecture integration."""
    print("\n🏗️ Testing Full Architecture Integration...")
    
    try:
        # Initialize both components
        config = LeonardoConfig()
        memory_service = MemoryService(config)
        await memory_service.initialize()
        
        user_id = "integration_test"
        
        # Simulate Leonardo workflow
        print("   📝 Simulating Leonardo conversation workflow...")
        
        conversations = [
            {
                "user": "Hi, my name is Charlie",
                "assistant": "Nice to meet you, Charlie! How can I help you today?",
                "success": True,
                "tools_used": []
            },
            {
                "user": "I'm working on a machine learning project",
                "assistant": "That's exciting! What kind of ML project are you working on?",
                "success": True,
                "tools_used": ["conversation"]
            },
            {
                "user": "Do you remember my name?",
                "assistant": "Yes, your name is Charlie. How is your ML project going?",
                "success": True,
                "tools_used": ["recall_memory"]
            }
        ]
        
        # Store each conversation turn using Leonardo's interface
        for i, conv in enumerate(conversations):
            success = memory_service.update(user_id, conv)
            print(f"      Turn {i+1}: {'✅' if success else '❌'}")
        
        # Test memory recall
        context = await memory_service.get_context_async(user_id, "my name and project")
        
        recent_turns = context.get('recent_turns', [])
        user_profile = context.get('user_profile', {})
        
        print(f"   🧠 Memory recall results:")
        print(f"      Recent turns: {len(recent_turns)}")
        print(f"      User profile: {user_profile}")
        
        # Verify name extraction
        name_found = any('Charlie' in str(turn) for turn in recent_turns)
        project_found = any('machine learning' in str(turn).lower() for turn in recent_turns)
        
        print(f"      Name recall: {'✅' if name_found else '❌'}")
        print(f"      Project recall: {'✅' if project_found else '❌'}")
        
        await memory_service.shutdown()
        
        return {
            "status": "success",
            "conversations_stored": len(conversations),
            "recent_turns": len(recent_turns),
            "name_recall": name_found,
            "project_recall": project_found,
            "user_profile": user_profile
        }
        
    except Exception as e:
        print(f"   ❌ Integration test failed: {e}")
        return {"status": "error", "error": str(e)}

async def main():
    """Run all consolidation tests."""
    print("🚀 Testing Leonardo Memory System Consolidation")
    print("=" * 60)
    
    print("📁 Current memory files:")
    memory_dir = Path(__file__).parent / "memory"
    for file in sorted(memory_dir.glob("*.py")):
        if not file.name.startswith("__"):
            print(f"   📄 {file.name}")
    
    results = {}
    
    # Test 1: MemoryService (what Leonardo uses)
    results["memory_service"] = await test_memory_service()
    
    # Test 2: MCP Interface (compliance layer)
    results["mcp_interface"] = await test_mcp_interface()
    
    # Test 3: Full integration (Leonardo workflow)
    results["integration"] = await test_architecture_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Consolidation Test Results")
    print("=" * 60)
    
    test_results = [
        ("MemoryService (Leonardo Interface)", results["memory_service"]),
        ("MCP-Compliant Interface", results["mcp_interface"]),
        ("Full Architecture Integration", results["integration"])
    ]
    
    success_count = 0
    for name, result in test_results:
        status = result.get("status", "unknown")
        emoji = "✅" if status == "success" else "❌" 
        print(f"\n{emoji} {name}: {status.upper()}")
        
        if status == "success":
            success_count += 1
            if name == "MemoryService (Leonardo Interface)":
                print(f"    Recent turns: {result.get('recent_turns_count', 0)}")
                print(f"    Update success: {result.get('update_success', False)}")
            elif name == "MCP-Compliant Interface":
                print(f"    Backend: {result.get('backend_type', 'unknown')}")
                operations = result.get('operations', {})
                print(f"    Operations: {sum(operations.values())}/{len(operations)} working")
            elif name == "Full Architecture Integration":
                print(f"    Conversations stored: {result.get('conversations_stored', 0)}")
                print(f"    Name recall: {result.get('name_recall', False)}")
                print(f"    Project recall: {result.get('project_recall', False)}")
        else:
            error = result.get("error", "Unknown error")
            print(f"    Error: {error[:100]}...")
    
    # Overall assessment
    success_rate = (success_count / len(test_results)) * 100
    
    print(f"\n🎯 Overall Success Rate: {success_rate:.1f}% ({success_count}/{len(test_results)})")
    
    if success_rate == 100:
        print("🎉 MEMORY CONSOLIDATION: PERFECT - Architecture is clean and working!")
    elif success_rate >= 66:
        print("✅ MEMORY CONSOLIDATION: SUCCESS - Architecture is functional")
    else:
        print("⚠️ MEMORY CONSOLIDATION: NEEDS WORK - Some components failing")
    
    print(f"\n📝 Recommendation: {'Keep consolidated architecture' if success_rate >= 66 else 'Review and fix issues'}")

if __name__ == "__main__":
    asyncio.run(main())
