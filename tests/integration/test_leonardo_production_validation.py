#!/usr/bin/env python3
"""
Leonardo Production Validation Test Suite
==========================================

Comprehensive test that validates ALL Leonardo capabilities through realistic conversation flows:
- FastMCP Memory System (storage, recall, summarization)
- DeepSearcher Agentic Research (web information retrieval)
- Browser Web Agent (screenshots, visual reasoning)
- Multi-step Reasoning and Complex Query Processing
- Tool Execution (weather, calculator, file operations, etc.)
- Complete Pipeline Integration
- Validation Wall and Verification Layer

Usage:
    python leonardo/test_leonardo_production_validation.py
"""

import asyncio
import logging
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import traceback

# Add Leonardo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo.config import LeonardoConfig
from leonardo.memory.service import MemoryService
from leonardo.planner.llm_planner import LLMPlanner
from leonardo.sandbox.executor import SandboxExecutor
from leonardo.validation.validation_wall import ValidationWall
from leonardo.verification.verification_layer import VerificationLayer
from leonardo.rag.rag_system import RAGSystem


@dataclass
class TestResult:
    """Test result with detailed metrics."""
    test_name: str
    success: bool
    duration: float
    details: Dict[str, Any]
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass 
class ConversationTurn:
    """Represents one turn in the conversation."""
    user_input: str
    expected_capabilities: List[str]  # What capabilities should be tested
    validation_checks: List[str]     # What to validate in the response


class LeonardoProductionValidator:
    """
    Comprehensive production validation for Leonardo.
    Tests all capabilities through realistic conversation flows.
    """
    
    def __init__(self):
        """Initialize the validator with all Leonardo components."""
        self.logger = logging.getLogger(__name__)
        self.test_results: List[TestResult] = []
        self.conversation_history: List[Dict[str, Any]] = []
        self.user_id = "production_test_user"
        self.session_id = f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize Leonardo components
        self.config = LeonardoConfig()
        self.config.setup_directories()
        
        # Core components
        self.memory_service: Optional[MemoryService] = None
        self.rag_system: Optional[RAGSystem] = None
        self.planner: Optional[LLMPlanner] = None
        self.executor: Optional[SandboxExecutor] = None
        self.validator: Optional[ValidationWall] = None
        self.verifier: Optional[VerificationLayer] = None
        
        self.setup_logging()
    
    def setup_logging(self):
        """Setup comprehensive logging for the test."""
        log_file = f"leonardo_production_validation_{self.session_id}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger.info(f"🧪 Starting Leonardo Production Validation - Session: {self.session_id}")
    
    async def initialize_leonardo_components(self) -> bool:
        """Initialize all Leonardo components for testing."""
        try:
            self.logger.info("🚀 Initializing Leonardo components...")
            
            # Memory Service (FastMCP)
            self.memory_service = MemoryService(self.config)
            await self.memory_service.initialize()
            self.logger.info("✅ Memory Service initialized")
            
            # RAG System
            self.rag_system = RAGSystem(self.config)
            await self.rag_system.initialize()
            self.logger.info("✅ RAG System initialized")
            
            # LLM Planner with memory integration
            self.planner = LLMPlanner(
                config=self.config,
                rag_system=self.rag_system,
                memory_service=self.memory_service
            )
            await self.planner.initialize()
            self.logger.info("✅ LLM Planner initialized")
            
            # Validation Wall
            self.validator = ValidationWall(self.config)
            await self.validator.initialize()
            self.logger.info("✅ Validation Wall initialized")
            
            # Sandbox Executor with all tools
            self.executor = SandboxExecutor(self.config)
            await self.executor.initialize()
            self.logger.info("✅ Sandbox Executor initialized")
            
            # Verification Layer
            self.verifier = VerificationLayer(self.config)
            await self.verifier.initialize()
            self.logger.info("✅ Verification Layer initialized")
            
            self.logger.info("🎉 All Leonardo components successfully initialized!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Leonardo components: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    def add_test_result(self, test_name: str, success: bool, duration: float, 
                       details: Dict[str, Any], error_message: Optional[str] = None):
        """Add a test result to the results collection."""
        result = TestResult(
            test_name=test_name,
            success=success,
            duration=duration,
            details=details,
            error_message=error_message
        )
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        self.logger.info(f"{status} {test_name} ({duration:.2f}s)")
        if error_message:
            self.logger.error(f"   Error: {error_message}")
    
    async def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """Process user input through the complete Leonardo pipeline."""
        start_time = time.time()
        
        try:
            # Step 1: Get memory context
            memory_context = self.memory_service.get_context(self.user_id, user_input)
            
            # Step 2: Plan with LLM (with memory context)
            plan = await self.planner.generate_plan(user_input, memory_context)
            
            # Step 3: Validate the plan
            validation_result = await self.validator.validate_plan(plan)
            if not validation_result.is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {validation_result.errors}",
                    "plan": plan,
                    "validation_result": validation_result
                }
            
            # Step 4: Execute tools
            execution_result = await self.executor.execute_plan(plan)
            
            # Step 5: Verify results
            verification_result = await self.verifier.verify_execution(
                plan, execution_result
            )
            
            # Step 6: Update memory with the complete turn
            turn_data = {
                "user_input": user_input,
                "plan": plan,
                "execution_result": execution_result,
                "verification_result": verification_result,
                "timestamp": datetime.now().isoformat(),
                "success": execution_result.success and verification_result.overall_success
            }
            
            self.memory_service.update(self.user_id, turn_data)
            self.conversation_history.append(turn_data)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "response": execution_result.result_summary,
                "plan": plan,
                "execution_result": execution_result,
                "verification_result": verification_result,
                "processing_time": processing_time,
                "turn_data": turn_data
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error processing user input: {e}")
            self.logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    async def test_memory_capabilities(self) -> bool:
        """Test FastMCP memory system capabilities."""
        self.logger.info("🧠 Testing Memory Capabilities...")
        
        test_conversations = [
            "Hello Leonardo, my name is Alex and I'm a software developer.",
            "I'm working on a Python machine learning project using TensorFlow.",
            "What's my name and what am I working on?"
        ]
        
        success = True
        start_time = time.time()
        details = {"conversations": [], "memory_tests": []}
        
        try:
            # Have the conversations
            for i, user_input in enumerate(test_conversations[:2]):
                result = await self.process_user_input(user_input)
                details["conversations"].append({
                    "input": user_input,
                    "success": result["success"],
                    "response": result.get("response", "")
                })
                
                if not result["success"]:
                    success = False
            
            # Test memory recall
            recall_result = await self.process_user_input(test_conversations[2])
            details["conversations"].append({
                "input": test_conversations[2],
                "success": recall_result["success"],
                "response": recall_result.get("response", "")
            })
            
            # Validate memory recall
            response = recall_result.get("response", "").lower()
            name_recalled = "alex" in response
            project_recalled = ("python" in response or "tensorflow" in response or 
                              "machine learning" in response)
            
            details["memory_tests"] = [
                {"test": "name_recall", "success": name_recalled},
                {"test": "project_recall", "success": project_recalled}
            ]
            
            if not (name_recalled and project_recalled):
                success = False
                
        except Exception as e:
            success = False
            details["error"] = str(e)
        
        duration = time.time() - start_time
        self.add_test_result("Memory Capabilities", success, duration, details)
        return success
    
    async def test_web_research_capabilities(self) -> bool:
        """Test DeepSearcher agentic research capabilities."""
        self.logger.info("🌐 Testing Web Research Capabilities...")
        
        start_time = time.time()
        success = True
        details = {"research_queries": []}
        
        try:
            # Test web research query
            research_query = "What is the latest Python version and its new features?"
            result = await self.process_user_input(research_query)
            
            details["research_queries"].append({
                "query": research_query,
                "success": result["success"],
                "response": result.get("response", ""),
                "tools_used": result.get("execution_result", {}).get("tools_executed", [])
            })
            
            # Validate web research worked
            if result["success"]:
                tools_used = result.get("execution_result", {}).get("tools_executed", [])
                web_tools_used = any("web" in tool.lower() or "search" in tool.lower() 
                                   or "deep" in tool.lower() for tool in tools_used)
                
                response = result.get("response", "").lower()
                python_mentioned = "python" in response
                version_mentioned = any(v in response for v in ["3.12", "3.13", "version"])
                
                if not (web_tools_used and python_mentioned and version_mentioned):
                    success = False
                    details["validation_issues"] = {
                        "web_tools_used": web_tools_used,
                        "python_mentioned": python_mentioned,
                        "version_mentioned": version_mentioned
                    }
            else:
                success = False
                
        except Exception as e:
            success = False
            details["error"] = str(e)
        
        duration = time.time() - start_time
        self.add_test_result("Web Research Capabilities", success, duration, details)
        return success
    
    async def test_visual_web_capabilities(self) -> bool:
        """Test browser automation and screenshot capabilities."""
        self.logger.info("📷 Testing Visual Web Capabilities...")
        
        start_time = time.time()
        success = True
        details = {"visual_queries": []}
        
        try:
            # Test visual web query
            visual_query = "Take a screenshot of the Python.org website homepage"
            result = await self.process_user_input(visual_query)
            
            details["visual_queries"].append({
                "query": visual_query,
                "success": result["success"],
                "response": result.get("response", ""),
                "tools_used": result.get("execution_result", {}).get("tools_executed", [])
            })
            
            # Validate screenshot was taken
            if result["success"]:
                tools_used = result.get("execution_result", {}).get("tools_executed", [])
                browser_tools_used = any("browser" in tool.lower() or "screenshot" in tool.lower() 
                                       for tool in tools_used)
                
                response = result.get("response", "").lower()
                screenshot_mentioned = "screenshot" in response or "image" in response
                
                if not (browser_tools_used and screenshot_mentioned):
                    success = False
                    details["validation_issues"] = {
                        "browser_tools_used": browser_tools_used,
                        "screenshot_mentioned": screenshot_mentioned
                    }
            else:
                success = False
                
        except Exception as e:
            success = False
            details["error"] = str(e)
        
        duration = time.time() - start_time
        self.add_test_result("Visual Web Capabilities", success, duration, details)
        return success
    
    async def test_reasoning_capabilities(self) -> bool:
        """Test multi-step reasoning and complex query processing."""
        self.logger.info("🤔 Testing Reasoning Capabilities...")
        
        start_time = time.time()
        success = True
        details = {"reasoning_queries": []}
        
        try:
            # Test complex reasoning query
            reasoning_query = ("If I have a meeting at 3 PM EST and I need to prepare for 2 hours, "
                             "what time should I start preparing in PST?")
            result = await self.process_user_input(reasoning_query)
            
            details["reasoning_queries"].append({
                "query": reasoning_query,
                "success": result["success"],
                "response": result.get("response", ""),
                "tools_used": result.get("execution_result", {}).get("tools_executed", [])
            })
            
            # Validate reasoning worked
            if result["success"]:
                response = result.get("response", "").lower()
                # Should mention time conversion and calculation
                time_mentioned = any(time_word in response for time_word in 
                                   ["1 pm", "1:00", "13:00", "pst", "est"])
                calculation_mentioned = ("2 hours" in response or "prepare" in response)
                
                if not (time_mentioned and calculation_mentioned):
                    success = False
                    details["validation_issues"] = {
                        "time_conversion": time_mentioned,
                        "calculation_logic": calculation_mentioned
                    }
            else:
                success = False
                
        except Exception as e:
            success = False
            details["error"] = str(e)
        
        duration = time.time() - start_time
        self.add_test_result("Reasoning Capabilities", success, duration, details)
        return success
    
    async def test_tool_execution_capabilities(self) -> bool:
        """Test various sandbox tool executions."""
        self.logger.info("🔧 Testing Tool Execution Capabilities...")
        
        start_time = time.time()
        success = True
        details = {"tool_tests": []}
        
        tool_tests = [
            ("What's the current weather in London?", ["weather"]),
            ("Calculate 15 * 23 + 47", ["calculator", "math"]),
            ("What time is it?", ["time", "system"]),
        ]
        
        try:
            for query, expected_tools in tool_tests:
                result = await self.process_user_input(query)
                
                tools_used = result.get("execution_result", {}).get("tools_executed", [])
                expected_tool_used = any(tool in str(tools_used).lower() 
                                       for tool in expected_tools)
                
                test_success = result["success"] and expected_tool_used
                if not test_success:
                    success = False
                
                details["tool_tests"].append({
                    "query": query,
                    "expected_tools": expected_tools,
                    "tools_used": tools_used,
                    "success": test_success,
                    "response": result.get("response", "")
                })
                
        except Exception as e:
            success = False
            details["error"] = str(e)
        
        duration = time.time() - start_time
        self.add_test_result("Tool Execution Capabilities", success, duration, details)
        return success
    
    async def test_conversation_summarization(self) -> bool:
        """Test conversation summarization capabilities."""
        self.logger.info("📝 Testing Conversation Summarization...")
        
        start_time = time.time()
        success = True
        details = {}
        
        try:
            # Request conversation summary
            summary_query = "Can you summarize our entire conversation so far?"
            result = await self.process_user_input(summary_query)
            
            details["summary_query"] = {
                "query": summary_query,
                "success": result["success"],
                "response": result.get("response", "")
            }
            
            # Validate summary quality
            if result["success"]:
                response = result.get("response", "").lower()
                # Should mention key topics from previous conversations
                topics_mentioned = [
                    "alex" in response or "name" in response,
                    "python" in response or "tensorflow" in response,
                    "weather" in response or "london" in response,
                    "calculate" in response or "math" in response
                ]
                
                summary_quality = sum(topics_mentioned) / len(topics_mentioned)
                details["summary_quality"] = {
                    "topics_mentioned": topics_mentioned,
                    "quality_score": summary_quality
                }
                
                if summary_quality < 0.5:  # At least 50% of topics should be mentioned
                    success = False
            else:
                success = False
                
        except Exception as e:
            success = False
            details["error"] = str(e)
        
        duration = time.time() - start_time
        self.add_test_result("Conversation Summarization", success, duration, details)
        return success
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run the complete production validation test suite."""
        self.logger.info("🚀 Starting Comprehensive Production Validation")
        overall_start_time = time.time()
        
        # Initialize components
        if not await self.initialize_leonardo_components():
            return {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "overall_success": False,
                "success": False,
                "error": "Failed to initialize Leonardo components",
                "initialization_failed": True
            }
        
        # Run all test categories
        test_categories = [
            ("Memory System", self.test_memory_capabilities),
            ("Web Research", self.test_web_research_capabilities), 
            ("Visual Web", self.test_visual_web_capabilities),
            ("Reasoning", self.test_reasoning_capabilities),
            ("Tool Execution", self.test_tool_execution_capabilities),
            ("Conversation Summary", self.test_conversation_summarization)
        ]
        
        category_results = {}
        overall_success = True
        
        for category_name, test_method in test_categories:
            self.logger.info(f"🧪 Running {category_name} tests...")
            try:
                category_success = await test_method()
                category_results[category_name] = category_success
                if not category_success:
                    overall_success = False
            except Exception as e:
                self.logger.error(f"❌ {category_name} tests failed with exception: {e}")
                category_results[category_name] = False
                overall_success = False
        
        # Calculate final metrics
        total_duration = time.time() - overall_start_time
        passed_tests = sum(1 for r in self.test_results if r.success)
        total_tests = len(self.test_results)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Generate comprehensive report
        report = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "overall_success": overall_success,
            "success_rate": success_rate,
            "total_duration": total_duration,
            "category_results": category_results,
            "detailed_results": [r.to_dict() for r in self.test_results],
            "conversation_history": self.conversation_history,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "components_tested": list(category_results.keys())
            }
        }
        
        # Save report
        report_file = f"leonardo_validation_report_{self.session_id}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"📊 Validation complete! Report saved to {report_file}")
        return report
    
    def print_summary_report(self, report: Dict[str, Any]):
        """Print a formatted summary of the validation results."""
        print("\n" + "="*80)
        print("🏆 LEONARDO PRODUCTION VALIDATION SUMMARY")
        print("="*80)
        
        print(f"Session ID: {report['session_id']}")
        print(f"Overall Success: {'✅ PASS' if report['overall_success'] else '❌ FAIL'}")
        print(f"Success Rate: {report['success_rate']:.1f}% ({report['summary']['passed_tests']}/{report['summary']['total_tests']})")
        print(f"Total Duration: {report['total_duration']:.2f}s")
        print()
        
        print("📋 CATEGORY RESULTS:")
        for category, success in report['category_results'].items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} {category}")
        print()
        
        print("🔍 DETAILED RESULTS:")
        for result in report['detailed_results']:
            status = "✅" if result['success'] else "❌"
            print(f"  {status} {result['test_name']} ({result['duration']:.2f}s)")
            if result['error_message']:
                print(f"      Error: {result['error_message']}")
        print()
        
        if report['overall_success']:
            print("🎉 Leonardo is PRODUCTION READY! All capabilities are working correctly.")
        else:
            print("⚠️ Leonardo has some issues that need attention before production deployment.")
        
        print("="*80)


async def main():
    """Main entry point for the production validation test."""
    validator = LeonardoProductionValidator()
    
    try:
        # Run comprehensive validation
        report = await validator.run_comprehensive_validation()
        
        # Print summary if we got a valid report
        if report and isinstance(report, dict) and 'session_id' in report:
            validator.print_summary_report(report)
            exit_code = 0 if report.get('overall_success', False) else 1
        else:
            print("\n❌ Validation failed during initialization")
            exit_code = 1
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        logging.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
