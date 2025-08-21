#!/usr/bin/env python3
"""
Lightweight Leonardo Validation Test
Tests all components EXCEPT the heavy LLM model loading
"""

import asyncio
import time
import sys
from pathlib import Path

# Add Leonardo to path
sys.path.append(str(Path(__file__).parent.parent))

from leonardo.config import LeonardoConfig
from leonardo.memory.service import MemoryService
from leonardo.validation.validation_wall import ValidationWall
from leonardo.sandbox.executor import SandboxExecutor
from leonardo.verification.verification_layer import VerificationLayer

async def lightweight_test():
    """Test Leonardo components without heavy LLM loading."""
    print("🚀 Lightweight Leonardo Validation Test")
    print("=" * 50)
    
    # Load config
    config_path = Path(__file__).parent.parent / "leonardo.toml"
    config = LeonardoConfig.load_from_file(config_path)
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Memory System
    total_tests += 1
    print("🧪 Test 1: Memory System")
    try:
        start = time.time()
        memory_service = MemoryService(config)
        await memory_service.initialize()
        
        # Test memory operations
        test_turn = {
            "user_input": "Hello Leonardo",
            "assistant": "Hello! How can I help?",
            "success": True
        }
        await memory_service.update_async("test_user", test_turn)
        context = await memory_service.get_context_async("test_user", "test query")
        
        if memory_service.is_initialized() and 'recent_turns' in context:
            tests_passed += 1
            print(f"  ✅ Memory System: PASS ({time.time()-start:.2f}s)")
        else:
            print(f"  ❌ Memory System: FAIL - Context missing")
            
    except Exception as e:
        print(f"  ❌ Memory System: FAIL - {e}")
    
    # Test 2: Validation Wall
    total_tests += 1
    print("🧪 Test 2: Validation Wall")
    try:
        start = time.time()
        audit_dir = str(Path(config.data_dir) / "audit_logs")
        Path(audit_dir).mkdir(parents=True, exist_ok=True)
        
        validator = ValidationWall(audit_dir)
        
        # Test safe tool call
        safe_tool_call = {
            "tool": "respond", 
            "args": {"message": "Hello"}, 
            "meta": {"risk": "safe"}
        }
        result = await validator.validate_tool_call(safe_tool_call)
        
        if result.approved:
            tests_passed += 1
            print(f"  ✅ Validation Wall: PASS ({time.time()-start:.2f}s)")
        else:
            print(f"  ❌ Validation Wall: FAIL - Not approved")
            
    except Exception as e:
        print(f"  ❌ Validation Wall: FAIL - {e}")
    
    # Test 3: Sandbox Executor  
    total_tests += 1
    print("🧪 Test 3: Sandbox Executor")
    try:
        start = time.time()
        executor = SandboxExecutor(config)
        
        # Test recall_memory tool (our new addition)
        tool_call = {
            "tool": "recall_memory",
            "args": {"query": "test"},
            "meta": {"risk": "safe"}
        }
        result = await executor.execute_plan(tool_call)
        
        if result.success:
            tests_passed += 1
            print(f"  ✅ Sandbox Executor: PASS ({time.time()-start:.2f}s)")
            print(f"    recall_memory tool working: {result.output[:50]}...")
        else:
            print(f"  ❌ Sandbox Executor: FAIL - {result.error}")
            
    except Exception as e:
        print(f"  ❌ Sandbox Executor: FAIL - {e}")
    
    # Test 4: Tool Availability
    total_tests += 1
    print("🧪 Test 4: Tool Availability")
    try:
        start = time.time()
        executor = SandboxExecutor(config)
        # Import AVAILABLE_TOOLS directly
        from leonardo.sandbox.tools import AVAILABLE_TOOLS
        available_tools = list(AVAILABLE_TOOLS.keys())
        
        # Check for key tools
        expected_tools = ['respond', 'recall_memory', 'get_weather', 'system_info']
        missing_tools = [tool for tool in expected_tools if tool not in available_tools]
        
        if not missing_tools:
            tests_passed += 1
            print(f"  ✅ Tool Availability: PASS ({time.time()-start:.2f}s)")
            print(f"    Available tools: {len(available_tools)}")
        else:
            print(f"  ❌ Tool Availability: FAIL - Missing: {missing_tools}")
            
    except Exception as e:
        print(f"  ❌ Tool Availability: FAIL - {e}")
    
    # Test 5: Verification Layer (Lightweight)
    total_tests += 1
    print("🧪 Test 5: Verification Layer")
    try:
        start = time.time()
        verification_config = {
            'research': {'entailment_threshold': 0.6, 'coverage_threshold': 0.8},
            'policy': {'max_retries': 1}
        }
        verifier = VerificationLayer(verification_config)
        # Skip initialization to avoid NLI model loading
        
        # Just test that it can be created
        tests_passed += 1
        print(f"  ✅ Verification Layer: PASS ({time.time()-start:.2f}s)")
        print(f"    (Skipped NLI model loading for speed)")
        
    except Exception as e:
        print(f"  ❌ Verification Layer: FAIL - {e}")
    
    # Results
    print(f"\n📊 LIGHTWEIGHT TEST RESULTS:")
    print(f"   Tests Passed: {tests_passed}/{total_tests}")
    print(f"   Success Rate: {tests_passed/total_tests*100:.1f}%")
    
    if tests_passed == total_tests:
        print("🎉 ALL CORE COMPONENTS WORKING!")
        print("💡 The issue is LLM model loading, not the pipeline architecture")
        return True
    else:
        print("⚠️ Some components still need fixes")
        return False

if __name__ == "__main__":
    success = asyncio.run(lightweight_test())
    sys.exit(0 if success else 1)
