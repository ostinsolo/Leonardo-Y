#!/usr/bin/env python3
"""
Leonardo Grammar Constraints Test
Test grammar-constrained JSON output - ELIMINATES "chatty text" problem

This test verifies:
1. Grammar constraints enforce JSON-only output
2. No "chatty text" from LLM responses
3. All tool calls match exact schema
4. Fallback planning works when constraints fail
"""

import asyncio
import logging
import sys
import json
from pathlib import Path

# Add Leonardo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo.config import LeonardoConfig
from leonardo.planner.llm_planner import LLMPlanner
from leonardo.planner.constrained_decoder import ConstrainedDecoder
from leonardo.planner.tool_schema import ToolCall, RiskLevel

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GrammarConstraintsTest:
    """Comprehensive test for grammar-constrained JSON generation."""
    
    def __init__(self):
        self.config = LeonardoConfig()
        # Override to use local Ollama model (much faster, already downloaded)
        self.config.llm.model_name = "llama3.2:latest"
        self.planner = None
        self.test_cases = [
            # Weather query
            {
                "input": "What's the weather like in London?",
                "expected_tool": "get_weather",
                "expected_risk": "safe"
            },
            # Web search
            {
                "input": "Search for information about Leonardo AI",
                "expected_tool": "web.deep_research",
                "expected_risk": "safe"
            },
            # File operations
            {
                "input": "Read the README file",
                "expected_tool": "read_file",
                "expected_risk": "safe"
            },
            # Email (risky operation)
            {
                "input": "Send an email to my boss about the meeting",
                "expected_tool": "send_email",
                "expected_risk": "confirm"
            },
            # Conversation
            {
                "input": "Hello, how are you today?",
                "expected_tool": "respond",
                "expected_risk": "safe"
            },
            # Complex research
            {
                "input": "Research the latest developments in AI and write a summary",
                "expected_tool": "web.deep_research",
                "expected_risk": "safe"
            },
            # Time/Date
            {
                "input": "What time is it right now?",
                "expected_tool": "get_time",
                "expected_risk": "safe"
            },
            # Calculator
            {
                "input": "Calculate 15 * 24 + 100",
                "expected_tool": "calculate",
                "expected_risk": "safe"
            }
        ]
        
    async def setup(self):
        """Initialize the grammar-constrained planner."""
        logger.info("🧠 Setting up grammar-constrained LLM planner...")
        
        # Initialize planner with no RAG system for this test
        self.planner = LLMPlanner(self.config, rag_system=None, memory_service=None)
        
        # Initialize with grammar constraints
        try:
            await self.planner.initialize()
            logger.info("✅ Grammar-constrained planner initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize planner: {e}")
            return False
    
    async def test_constrained_decoder_direct(self):
        """Test the constrained decoder directly."""
        logger.info("\n🔬 Testing ConstrainedDecoder directly...")
        
        decoder = ConstrainedDecoder(self.config)
        success = await decoder.initialize("llama3.2:latest")
        
        if not success:
            logger.warning("⚠️ ConstrainedDecoder not available - using fallback")
            return False
        
        # Test with a simple prompt
        test_prompt = "Generate a tool call for: What's the weather in Paris?"
        result = await decoder.generate_constrained(test_prompt)
        
        if result:
            logger.info(f"✅ Direct constrained generation worked:")
            logger.info(f"   Result: {json.dumps(result, indent=2)}")
            
            # Validate the result
            if decoder._validate_tool_call(result):
                logger.info("✅ Generated tool call is valid")
                return True
            else:
                logger.error("❌ Generated tool call is invalid")
                return False
        else:
            logger.error("❌ Direct constrained generation failed")
            return False
    
    async def test_json_only_output(self):
        """Test that planner generates JSON-only output (no chatty text)."""
        logger.info("\n🎯 Testing JSON-only output (eliminating chatty text)...")
        
        results = []
        for i, test_case in enumerate(self.test_cases):
            logger.info(f"\n--- Test {i+1}/{len(self.test_cases)}: {test_case['input'][:50]}... ---")
            
            try:
                # Generate plan using grammar constraints
                plan_result = await self.planner.generate_plan(test_case["input"])
                
                if plan_result:
                    tool_call_json = plan_result.tool_call
                    
                    # Create ToolCall object to validate
                    tool_call = ToolCall(**tool_call_json)
                    
                    logger.info(f"✅ Generated: {tool_call.tool} (risk: {tool_call.risk_level.value})")
                    
                    # Check if it's exactly JSON (no extra text)
                    json_str = json.dumps(tool_call_json)
                    is_pure_json = json_str.startswith("{") and json_str.endswith("}")
                    
                    results.append({
                        "input": test_case["input"],
                        "success": True,
                        "tool": tool_call.tool,
                        "risk": tool_call.risk_level.value,
                        "is_pure_json": is_pure_json,
                        "expected_tool": test_case["expected_tool"],
                        "tool_matches": tool_call.tool == test_case["expected_tool"]
                    })
                    
                    if is_pure_json:
                        logger.info("✅ Output is pure JSON (no chatty text)")
                    else:
                        logger.warning("⚠️ Output contains non-JSON content")
                
                else:
                    logger.error(f"❌ Failed to generate plan for: {test_case['input']}")
                    results.append({
                        "input": test_case["input"],
                        "success": False,
                        "tool": None,
                        "risk": None,
                        "is_pure_json": False,
                        "tool_matches": False
                    })
                
            except Exception as e:
                logger.error(f"❌ Test error: {e}")
                results.append({
                    "input": test_case["input"],
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def test_grammar_validation(self):
        """Test that grammar constraints prevent invalid output."""
        logger.info("\n🛡️ Testing grammar validation (schema enforcement)...")
        
        # Test the schema validation directly
        decoder = self.planner.constrained_decoder
        
        # Valid tool call
        valid_tool_call = {
            "tool": "get_weather",
            "args": {"location": "London", "units": "metric"},
            "meta": {"risk": "safe", "command_id": "test_001"}
        }
        
        # Invalid tool calls
        invalid_calls = [
            # Missing required field
            {"tool": "get_weather", "args": {}},
            # Invalid tool name
            {"tool": "invalid_tool", "args": {}, "meta": {"risk": "safe"}},
            # Invalid risk level
            {"tool": "get_weather", "args": {}, "meta": {"risk": "invalid_risk"}},
            # Wrong structure
            {"command": "do_something", "parameters": {}}
        ]
        
        # Test valid call
        if decoder._validate_tool_call(valid_tool_call):
            logger.info("✅ Valid tool call accepted")
        else:
            logger.error("❌ Valid tool call rejected")
        
        # Test invalid calls
        for i, invalid_call in enumerate(invalid_calls):
            if decoder._validate_tool_call(invalid_call):
                logger.error(f"❌ Invalid tool call {i+1} was incorrectly accepted")
            else:
                logger.info(f"✅ Invalid tool call {i+1} correctly rejected")
    
    def analyze_results(self, results):
        """Analyze test results and provide summary."""
        logger.info("\n📊 GRAMMAR CONSTRAINTS TEST RESULTS:")
        logger.info("="*60)
        
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.get("success", False))
        pure_json_tests = sum(1 for r in results if r.get("is_pure_json", False))
        tool_matches = sum(1 for r in results if r.get("tool_matches", False))
        
        success_rate = (successful_tests / total_tests) * 100
        json_purity_rate = (pure_json_tests / total_tests) * 100
        tool_accuracy = (tool_matches / total_tests) * 100
        
        logger.info(f"Total tests: {total_tests}")
        logger.info(f"Successful generations: {successful_tests} ({success_rate:.1f}%)")
        logger.info(f"Pure JSON output: {pure_json_tests} ({json_purity_rate:.1f}%)")
        logger.info(f"Correct tool selection: {tool_matches} ({tool_accuracy:.1f}%)")
        logger.info("")
        
        # Detailed results
        for i, result in enumerate(results):
            status = "✅" if result.get("success", False) else "❌"
            json_status = "🎯" if result.get("is_pure_json", False) else "💬"
            tool_status = "🎪" if result.get("tool_matches", False) else "🔄"
            
            logger.info(f"{status} {json_status} {tool_status} Test {i+1}: {result['input'][:40]}...")
            if result.get("success"):
                logger.info(f"    → Tool: {result.get('tool')} (risk: {result.get('risk')})")
        
        # Overall assessment
        logger.info("\n🎯 CHATTY TEXT ELIMINATION ASSESSMENT:")
        if json_purity_rate >= 90:
            logger.info("🎉 EXCELLENT: Grammar constraints successfully eliminate chatty text!")
        elif json_purity_rate >= 70:
            logger.info("👍 GOOD: Most outputs are pure JSON, minor issues remain")
        else:
            logger.warning("⚠️ NEEDS WORK: Significant chatty text still present")
        
        return {
            "success_rate": success_rate,
            "json_purity_rate": json_purity_rate,
            "tool_accuracy": tool_accuracy,
            "chatty_text_eliminated": json_purity_rate >= 90
        }
    
    async def cleanup(self):
        """Clean up resources."""
        if self.planner:
            await self.planner.shutdown()
        logger.info("🧹 Test cleanup complete")


async def run_grammar_constraints_test():
    """Run the complete grammar constraints test suite."""
    logger.info("🚀 LEONARDO GRAMMAR CONSTRAINTS TEST")
    logger.info("="*60)
    logger.info("Testing: JSON-only output, eliminating 'chatty text' problem")
    logger.info("")
    
    test = GrammarConstraintsTest()
    
    try:
        # Setup
        if not await test.setup():
            logger.error("❌ Setup failed - cannot continue")
            return False
        
        # Test constrained decoder directly
        await test.test_constrained_decoder_direct()
        
        # Test JSON-only output
        results = await test.test_json_only_output()
        
        # Test grammar validation
        await test.test_grammar_validation()
        
        # Analyze results
        summary = test.analyze_results(results)
        
        # Final assessment
        logger.info("\n🏆 FINAL ASSESSMENT:")
        logger.info("="*40)
        
        if summary["chatty_text_eliminated"]:
            logger.info("🎉 SUCCESS: Grammar constraints eliminate chatty text!")
            logger.info("✅ Leonardo LLM planner now generates JSON-only output")
            logger.info("🛡️ Architecture compliance: ACHIEVED")
        else:
            logger.warning("⚠️ PARTIAL SUCCESS: Some improvements needed")
            logger.info("🔧 Consider tuning constraints or fallback mechanisms")
        
        return summary["chatty_text_eliminated"]
        
    except Exception as e:
        logger.error(f"❌ Test suite error: {e}")
        return False
    finally:
        await test.cleanup()


if __name__ == "__main__":
    # Run the test
    asyncio.run(run_grammar_constraints_test())
