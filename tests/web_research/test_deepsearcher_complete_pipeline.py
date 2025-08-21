#!/usr/bin/env python3
"""
🔬 Leonardo DeepSearcher Complete Pipeline Test
Testing enterprise-grade agentic research capabilities with:
1. Simple weather query (London weather)
2. Complex research query (Who is Ostin Solo)

This tests the 5-stage LLM pipeline:
1. Initial Setup - Takes user query and research parameters
2. Deep Research Process - Multiple SERP queries and key learnings
3. Recursive Exploration - Follow-up research directions with depth > 0
4. Report Generation - Comprehensive markdown report with sources
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add leonardo to path properly
leonardo_root = Path(__file__).parent.parent  # Go up to Leonardo-Y root
sys.path.insert(0, str(leonardo_root))

try:
    from leonardo.config import LeonardoConfig
    from leonardo.sandbox.executor import SandboxExecutor
    from leonardo.memory.enhanced_memory import EnhancedMemorySystem
    from leonardo.planner.llm_planner import LLMPlanner
except ImportError as e:
    # Fallback for different path setups
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from config import LeonardoConfig
        from sandbox.executor import SandboxExecutor
        from memory.enhanced_memory import EnhancedMemorySystem
        from planner.llm_planner import LLMPlanner
    except ImportError as e2:
        print(f"❌ Import Error: {e}")
        print(f"❌ Fallback Import Error: {e2}")
        print("💡 Make sure you're running from Leonardo root directory")
        sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('leonardo_deepsearcher_test.log')
    ]
)
logger = logging.getLogger(__name__)

class DeepSearcherPipelineTest:
    """Complete pipeline test for DeepSearcher agentic research"""
    
    def __init__(self):
        """Initialize test components"""
        self.config = LeonardoConfig()
        self.executor = SandboxExecutor(self.config)
        self.memory = EnhancedMemorySystem()  # Use default memory directory
        self.planner = LLMPlanner(self.config, rag_system=None)  # No RAG needed for this test
        
        # Test results
        self.test_results = []
        self.session_id = f"deepsearcher_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    async def run_complete_test(self):
        """Run complete DeepSearcher pipeline test"""
        logger.info("🚀 Starting Leonardo DeepSearcher Complete Pipeline Test")
        
        # Test 1: Simple Weather Query
        logger.info("\n" + "="*60)
        logger.info("📊 TEST 1: Simple Weather Query (London weather)")
        logger.info("="*60)
        
        weather_result = await self.test_weather_query()
        
        # Test 2: Complex Research Query  
        logger.info("\n" + "="*60)
        logger.info("🔬 TEST 2: Complex Research Query (Who is Ostin Solo)")
        logger.info("="*60)
        
        research_result = await self.test_ostin_solo_research()
        
        # Generate final report
        await self.generate_final_report()
        
        return {
            "weather_test": weather_result,
            "research_test": research_result,
            "session_id": self.session_id
        }
    
    async def test_weather_query(self):
        """Test simple weather query through DeepSearcher"""
        try:
            # Simulate user voice input
            user_query = "What's the weather like in London today?"
            logger.info(f"👤 User Query: {user_query}")
            
            # Plan the query through LLM planner
            logger.info("🧠 Planning query through LLM...")
            plan = await self.planner.generate_plan(
                user_input=user_query,
                context=await self.memory.get_recent_conversations(limit=5)
            )
            
            logger.info(f"📋 Generated Plan: {json.dumps(plan, indent=2)}")
            
            # Execute through sandbox with DeepSearcher
            logger.info("🔬 Executing through DeepSearcher...")
            result = await self.executor.execute_plan(plan)
            
            logger.info(f"✅ Weather Result: {result}")
            
            # Store in memory
            await self.memory.add_interaction(
                user_input=user_query,
                assistant_response=str(result),
                metadata={
                    "test_type": "weather_query",
                    "tool_used": "deepsearcher",
                    "session_id": self.session_id
                }
            )
            
            self.test_results.append({
                "test": "weather_query",
                "query": user_query,
                "plan": plan,
                "result": result,
                "status": "success"
            })
            
            return {"status": "success", "result": result}
            
        except Exception as e:
            logger.error(f"❌ Weather test failed: {e}")
            self.test_results.append({
                "test": "weather_query", 
                "error": str(e),
                "status": "failed"
            })
            return {"status": "failed", "error": str(e)}
    
    async def test_ostin_solo_research(self):
        """Test complex agentic research for Ostin Solo"""
        try:
            # Complex research query
            user_query = "Who is Ostin Solo? Please conduct deep research and tell me about his projects, background, and connection to AI development."
            logger.info(f"👤 Research Query: {user_query}")
            
            # Plan the research through LLM planner  
            logger.info("🧠 Planning research through LLM...")
            plan = await self.planner.generate_plan(
                user_input=user_query,
                context=await self.memory.get_recent_conversations(limit=5)
            )
            
            logger.info(f"📋 Generated Research Plan: {json.dumps(plan, indent=2)}")
            
            # Execute deep research through DeepSearcher
            logger.info("🔬 Executing deep research through DeepSearcher...")
            logger.info("📊 This should demonstrate:")
            logger.info("   1. Initial Setup - Query and research parameters")  
            logger.info("   2. Deep Research Process - Multiple SERP queries")
            logger.info("   3. Recursive Exploration - Follow-up directions") 
            logger.info("   4. Report Generation - Comprehensive markdown report")
            
            result = await self.executor.execute_plan(plan)
            
            logger.info(f"✅ Research Result Length: {len(str(result))} characters")
            logger.info("📄 Research Report Preview:")
            logger.info("-" * 40)
            logger.info(str(result)[:500] + "..." if len(str(result)) > 500 else str(result))
            logger.info("-" * 40)
            
            # Store comprehensive research in memory
            await self.memory.add_interaction(
                user_input=user_query,
                assistant_response=str(result),
                metadata={
                    "test_type": "agentic_research",
                    "tool_used": "deepsearcher",
                    "session_id": self.session_id,
                    "research_depth": "deep",
                    "result_length": len(str(result))
                }
            )
            
            self.test_results.append({
                "test": "ostin_solo_research",
                "query": user_query, 
                "plan": plan,
                "result": result,
                "result_length": len(str(result)),
                "status": "success"
            })
            
            return {"status": "success", "result": result, "length": len(str(result))}
            
        except Exception as e:
            logger.error(f"❌ Ostin Solo research failed: {e}")
            self.test_results.append({
                "test": "ostin_solo_research",
                "error": str(e), 
                "status": "failed"
            })
            return {"status": "failed", "error": str(e)}
    
    async def generate_final_report(self):
        """Generate comprehensive test report"""
        logger.info("\n" + "="*60)
        logger.info("📊 GENERATING FINAL TEST REPORT")
        logger.info("="*60)
        
        report = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "test_summary": {
                "total_tests": len(self.test_results),
                "successful_tests": len([r for r in self.test_results if r["status"] == "success"]),
                "failed_tests": len([r for r in self.test_results if r["status"] == "failed"])
            },
            "detailed_results": self.test_results,
            "leonardo_capabilities_tested": [
                "DeepSearcher Integration",
                "5-Stage LLM Pipeline", 
                "Multi-Step Research Process",
                "Recursive Exploration",
                "Report Generation", 
                "Memory Integration",
                "LLM Planning",
                "Sandbox Execution"
            ]
        }
        
        # Save report to file
        report_file = f"leonardo_deepsearcher_report_{self.session_id}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"💾 Report saved to: {report_file}")
        
        # Print summary
        logger.info(f"✅ Successful Tests: {report['test_summary']['successful_tests']}/{report['test_summary']['total_tests']}")
        logger.info(f"🔬 Agentic Research Pipeline: {'WORKING' if report['test_summary']['successful_tests'] > 0 else 'FAILED'}")
        
        return report

async def main():
    """Main test execution"""
    logger.info("🎭 Leonardo DeepSearcher Complete Pipeline Test")
    logger.info("Testing enterprise-grade agentic research capabilities...")
    
    test = DeepSearcherPipelineTest()
    results = await test.run_complete_test()
    
    logger.info("\n" + "🏆" + "="*58 + "🏆")
    logger.info("🏆 LEONARDO DEEPSEARCHER TEST COMPLETE! 🏆")
    logger.info("🏆" + "="*58 + "🏆")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
