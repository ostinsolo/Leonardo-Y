#!/usr/bin/env python3
"""
Quick Leonardo Conversation Test
Test response speed and functionality after fixes
"""

import asyncio
import time
import sys
from pathlib import Path

# Add Leonardo to path
sys.path.append(str(Path(__file__).parent.parent))

from leonardo.config import LeonardoConfig
from leonardo.memory.service import MemoryService
from leonardo.planner.llm_planner import LLMPlanner
from leonardo.rag.rag_system import RAGSystem

async def quick_test():
    """Quick test of Leonardo's core components."""
    print("🚀 Quick Leonardo Conversation Test")
    print("=" * 50)
    
    # Load config
    config_path = Path(__file__).parent.parent / "leonardo.toml"
    config = LeonardoConfig.load_from_file(config_path)
    
    # Initialize components
    print("⏱️ Initializing components...")
    start_init = time.time()
    
    memory_service = MemoryService(config)
    await memory_service.initialize()
    
    rag_system = RAGSystem(config)
    planner = LLMPlanner(config, rag_system, memory_service)
    await planner.initialize()
    
    init_time = time.time() - start_init
    print(f"✅ Components initialized in {init_time:.2f}s")
    
    # Test simple planning
    test_inputs = [
        "Hello Leonardo!",
        "What's the weather?",
        "Remember my name is Alex"
    ]
    
    total_planning_time = 0
    successful_plans = 0
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n🧪 Test {i}: '{user_input}'")
        
        start_plan = time.time()
        try:
            plan = await planner.generate_plan(user_input)
            plan_time = time.time() - start_plan
            total_planning_time += plan_time
            
            if plan and plan.tool_call:
                successful_plans += 1
                tool_name = plan.tool_call.get('tool', 'unknown')
                confidence = plan.confidence
                print(f"  ✅ Plan: {tool_name} (confidence: {confidence:.2f}) in {plan_time:.2f}s")
            else:
                print(f"  ❌ Failed to generate plan in {plan_time:.2f}s")
                
        except Exception as e:
            plan_time = time.time() - start_plan
            total_planning_time += plan_time
            print(f"  ❌ Error: {e} in {plan_time:.2f}s")
    
    # Results
    print(f"\n📊 Results:")
    print(f"   Successful Plans: {successful_plans}/{len(test_inputs)}")
    print(f"   Average Planning Time: {total_planning_time/len(test_inputs):.2f}s")
    print(f"   Total Test Time: {total_planning_time + init_time:.2f}s")
    
    if successful_plans == len(test_inputs) and total_planning_time/len(test_inputs) < 30:
        print("🎉 LEONARDO IS FAST AND WORKING!")
        return True
    else:
        print("⚠️ Leonardo needs optimization")
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    sys.exit(0 if success else 1)
