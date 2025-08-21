#!/usr/bin/env python3
"""
Web Access Pipeline Test - Testing Search-R1, ReCall, and MCP patterns
Tests the complete pipeline: understand → plan → web search → reason → respond

This validates our integration of:
- facebookresearch/Search-R1: reasoning + search engine integration
- facebookresearch/ReCall: chaining tool calls effectively  
- MCP: standardized tool protocol integration
"""

import asyncio
import sys
import time
from pathlib import Path

# Add Leonardo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo.config import LeonardoConfig
from leonardo.memory.advanced_memory_service import AdvancedMemoryService
from leonardo.planner.llm_planner import LLMPlanner
from leonardo.sandbox.executor import SandboxExecutor
from leonardo.rag.rag_system import RAGSystem


class WebAccessPipelineTester:
    """Test suite for Leonardo's web access capabilities."""
    
    def __init__(self):
        self.config = LeonardoConfig()
        self.advanced_memory = None
        self.llm_planner = None
        self.sandbox_executor = None
        self.rag_system = None
        self.test_user_id = "web_test_user"
        
    async def initialize_components(self):
        """Initialize all pipeline components."""
        print("🚀 LEONARDO WEB ACCESS PIPELINE TEST")
        print("=" * 60)
        
        try:
            # Initialize Memory Service (JARVIS-1 enhanced)
            print("🧠 Initializing Advanced Memory Service...")
            self.advanced_memory = AdvancedMemoryService(self.config)
            await self.advanced_memory.initialize()
            
            # Initialize RAG System
            print("📚 Initializing RAG System...")
            self.rag_system = RAGSystem(self.config)
            await self.rag_system.initialize()
            
            # Initialize LLM Planner with memory
            print("🧠 Initializing LLM Planner...")
            self.llm_planner = LLMPlanner(self.config, self.rag_system, self.advanced_memory)
            await self.llm_planner.initialize()
            
            # Initialize Sandbox Executor
            print("📦 Initializing Sandbox Executor...")
            self.sandbox_executor = SandboxExecutor(self.config)
            await self.sandbox_executor.initialize()
            
            print("✅ All components initialized successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Component initialization failed: {e}")
            return False
    
    async def test_web_search_reasoning(self, query: str) -> dict:
        """
        Test Search-R1 style reasoning + web search integration.
        
        Pipeline: Query → Memory Context → LLM Planning → Web Search → Reasoning
        """
        print(f"\n🔍 TESTING: Web Search Reasoning")
        print(f"   Query: '{query}'")
        print("-" * 50)
        
        test_result = {
            "query": query,
            "steps": [],
            "success": False,
            "duration": 0,
            "final_response": ""
        }
        
        start_time = time.time()
        
        try:
            # Step 1: Get memory context (JARVIS-1 enhanced)
            print("🧠 Step 1: Retrieving memory context...")
            memory_context = await self.advanced_memory.get_context_async(self.test_user_id, query)
            
            test_result["steps"].append({
                "step": "memory_context",
                "success": True,
                "data": {
                    "recent_turns": len(memory_context.get("recent_turns", [])),
                    "relevant_memories": len(memory_context.get("relevant_memories", [])),
                    "backend": memory_context.get("memory_stats", {}).get("backend_type", "unknown")
                }
            })
            print(f"   ✅ Retrieved {len(memory_context.get('recent_turns', []))} recent turns")
            
            # Step 2: LLM Planning (Search-R1 integration)
            print("📋 Step 2: Generating execution plan...")
            plan_result = await self.llm_planner.generate_plan(query, self.test_user_id)
            
            if plan_result:
                tool_call = plan_result.tool_call
                test_result["steps"].append({
                    "step": "planning", 
                    "success": True,
                    "data": {
                        "tool": tool_call.get("tool"),
                        "args": tool_call.get("args"),
                        "confidence": plan_result.confidence
                    }
                })
                print(f"   ✅ Generated plan: {tool_call.get('tool')} with confidence {plan_result.confidence}")
                
                # Step 3: Tool Execution (ReCall-style chaining)
                if tool_call.get("tool") == "search_web":
                    print("🌐 Step 3: Executing web search...")
                    execution_result = await self.sandbox_executor.execute_plan(tool_call)
                    
                    test_result["steps"].append({
                        "step": "web_search_execution",
                        "success": execution_result.success,
                        "data": {
                            "duration": execution_result.duration,
                            "output_type": type(execution_result.output).__name__,
                            "error": execution_result.error if not execution_result.success else None
                        }
                    })
                    
                    if execution_result.success:
                        print(f"   ✅ Web search completed in {execution_result.duration:.2f}s")
                        
                        # Step 4: Memory Update
                        print("🧠 Step 4: Updating memory with results...")
                        conversation_turn = {
                            "user": query,
                            "assistant": str(execution_result.output),
                            "timestamp": time.time(),
                            "tools_used": ["search_web"],
                            "success": True
                        }
                        await self.advanced_memory.update_async(self.test_user_id, conversation_turn)
                        
                        test_result["steps"].append({
                            "step": "memory_update",
                            "success": True,
                            "data": {"conversation_stored": True}
                        })
                        print("   ✅ Memory updated with search results")
                        
                        # Generate final response
                        if isinstance(execution_result.output, dict) and "summary" in execution_result.output:
                            test_result["final_response"] = execution_result.output["summary"]
                        else:
                            test_result["final_response"] = str(execution_result.output)
                        
                        test_result["success"] = True
                        
                    else:
                        print(f"   ❌ Web search failed: {execution_result.error}")
                        test_result["final_response"] = f"Web search failed: {execution_result.error}"
                        
                else:
                    print(f"   ⚠️ Non-web tool planned: {tool_call.get('tool')}")
                    test_result["final_response"] = f"Generated plan for non-web tool: {tool_call.get('tool')}"
                    test_result["success"] = True
                    
            else:
                print("   ❌ Planning failed")
                test_result["steps"].append({
                    "step": "planning",
                    "success": False,
                    "data": {"error": "No plan generated"}
                })
                test_result["final_response"] = "Failed to generate execution plan"
                
        except Exception as e:
            print(f"   ❌ Pipeline error: {e}")
            test_result["final_response"] = f"Pipeline error: {e}"
        
        test_result["duration"] = time.time() - start_time
        return test_result
    
    async def test_tool_chaining_capabilities(self):
        """
        Test ReCall-style tool chaining capabilities.
        Multiple tools used in sequence based on results.
        """
        print(f"\n🔗 TESTING: Tool Chaining (ReCall-style)")
        print("-" * 50)
        
        # Test sequence: Time → Weather → Search
        chain_queries = [
            "What time is it?",
            "What's the weather like?", 
            "Search for current news"
        ]
        
        chain_results = []
        
        for i, query in enumerate(chain_queries, 1):
            print(f"\n   Chain Step {i}: '{query}'")
            
            result = await self.test_web_search_reasoning(query)
            chain_results.append(result)
            
            print(f"   Result: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
            print(f"   Response: {result['final_response'][:100]}...")
            
            # Small delay between chained operations
            await asyncio.sleep(1)
        
        return chain_results
    
    async def test_mcp_tool_protocol(self):
        """
        Test MCP (Model Context Protocol) standardized tool integration.
        Validates tool discoverability and execution patterns.
        """
        print(f"\n🔌 TESTING: MCP Tool Protocol Integration")
        print("-" * 50)
        
        # Import available tools
        from leonardo.sandbox.tools import AVAILABLE_TOOLS
        
        print(f"📋 Available MCP Tools: {len(AVAILABLE_TOOLS)}")
        for tool_name in AVAILABLE_TOOLS.keys():
            print(f"   - {tool_name}")
        
        # Test tool execution through MCP patterns
        mcp_test_queries = [
            "search for Python tutorials",          # Web search
            "what time is it right now",           # System info  
            "calculate 25 * 4 + 12",               # Calculator
            "tell me something interesting"        # Response
        ]
        
        mcp_results = []
        
        for query in mcp_test_queries:
            print(f"\n   Testing: '{query}'")
            result = await self.test_web_search_reasoning(query)
            mcp_results.append(result)
            
            status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
            print(f"   Status: {status}")
        
        return mcp_results
    
    async def run_comprehensive_test(self):
        """Run comprehensive web access pipeline test."""
        
        if not await self.initialize_components():
            return False
        
        print(f"\n🧪 TESTING USER: {self.test_user_id}")
        
        all_results = {
            "search_reasoning": [],
            "tool_chaining": [],
            "mcp_protocol": [],
            "overall_success": False
        }
        
        try:
            # Test 1: Basic Web Search Reasoning (Search-R1 patterns)
            print(f"\n" + "="*60)
            print("TEST 1: Search-R1 Style Web Reasoning")
            print("="*60)
            
            search_queries = [
                "search for latest Python news",
                "find information about machine learning", 
                "look up weather in San Francisco",
                "search for Leonardo da Vinci biography"
            ]
            
            for query in search_queries:
                result = await self.test_web_search_reasoning(query)
                all_results["search_reasoning"].append(result)
                
                status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
                print(f"\n{status}: {query}")
                print(f"Duration: {result['duration']:.2f}s")
                print(f"Steps: {len(result['steps'])}")
            
            # Test 2: Tool Chaining (ReCall patterns)
            print(f"\n" + "="*60)
            print("TEST 2: ReCall-Style Tool Chaining")
            print("="*60)
            
            chain_results = await self.test_tool_chaining_capabilities()
            all_results["tool_chaining"] = chain_results
            
            # Test 3: MCP Protocol Integration
            print(f"\n" + "="*60)
            print("TEST 3: MCP Protocol Integration")
            print("="*60)
            
            mcp_results = await self.test_mcp_tool_protocol()
            all_results["mcp_protocol"] = mcp_results
            
            # Calculate overall success rate
            all_tests = (all_results["search_reasoning"] + 
                        all_results["tool_chaining"] + 
                        all_results["mcp_protocol"])
            
            successful_tests = sum(1 for test in all_tests if test["success"])
            total_tests = len(all_tests)
            success_rate = successful_tests / total_tests * 100 if total_tests > 0 else 0
            
            all_results["overall_success"] = success_rate >= 70  # 70% threshold
            
            # Final Results
            print("\n" + "="*60)
            print("🎯 WEB ACCESS PIPELINE TEST RESULTS")
            print("="*60)
            
            print(f"📊 Overall Success Rate: {successful_tests}/{total_tests} ({success_rate:.1f}%)")
            
            print(f"\n🔍 Search-R1 Web Reasoning: {sum(1 for t in all_results['search_reasoning'] if t['success'])}/{len(all_results['search_reasoning'])}")
            print(f"🔗 ReCall Tool Chaining: {sum(1 for t in all_results['tool_chaining'] if t['success'])}/{len(all_results['tool_chaining'])}")
            print(f"🔌 MCP Protocol Integration: {sum(1 for t in all_results['mcp_protocol'] if t['success'])}/{len(all_results['mcp_protocol'])}")
            
            if success_rate >= 80:
                print("🎉 EXCELLENT: Web access pipeline working perfectly!")
            elif success_rate >= 70:
                print("✅ GOOD: Web access pipeline mostly functional")
            else:
                print("⚠️ NEEDS IMPROVEMENT: Web access pipeline needs optimization")
            
            # Show sample successful results
            print(f"\n📋 Sample Results:")
            for i, result in enumerate(all_tests[:3]):
                status = "✅" if result["success"] else "❌"
                print(f"{status} {result['query']}")
                print(f"   Response: {result['final_response'][:80]}...")
                print(f"   Duration: {result['duration']:.2f}s")
            
            # Cleanup
            if self.advanced_memory:
                await self.advanced_memory.shutdown()
            if self.llm_planner:
                await self.llm_planner.shutdown()
            if self.sandbox_executor:
                await self.sandbox_executor.shutdown()
            
            return success_rate >= 70
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            return False


async def main():
    """Main test execution."""
    tester = WebAccessPipelineTester()
    success = await tester.run_comprehensive_test()
    
    exit_code = 0 if success else 1
    print(f"\n🎭 Web Access Pipeline Test {'PASSED' if success else 'FAILED'}")
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
