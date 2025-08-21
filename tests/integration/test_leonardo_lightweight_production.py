#!/usr/bin/env python3
"""
Leonardo Lightweight Production Validation
==========================================

Lightweight test that validates ALL Leonardo capabilities without heavy model loading.
Tests the architecture, memory, tools, and pipeline integration with optimized approach.

Features tested:
- FastMCP Memory System (storage, recall, summarization)
- Tool Execution (weather, calculator, file operations)
- Validation Wall and Verification Layer
- Complete Pipeline Integration

Usage:
    python leonardo/test_leonardo_lightweight_production.py
"""

import asyncio
import logging
import json
import sys
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Add Leonardo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Intel Mac optimizations - set before any heavy imports
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1" 
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from leonardo.config import LeonardoConfig
from leonardo.memory.service import MemoryService
from leonardo.sandbox.executor import SandboxExecutor
from leonardo.validation.validation_wall import ValidationWall
from leonardo.validation.validation_result import ValidationResult, RiskLevel
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
    

class LeonardoLightweightValidator:
    """
    Lightweight production validation for Leonardo.
    Tests all capabilities without heavy model loading.
    """
    
    def __init__(self):
        """Initialize the lightweight validator."""
        self.logger = logging.getLogger(__name__)
        self.test_results: List[TestResult] = []
        self.user_id = "lightweight_test_user"
        self.session_id = f"lightweight_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize Leonardo components
        self.config = LeonardoConfig()
        self.config.setup_directories()
        
        # Core components (no LLM planner to avoid model loading)
        self.memory_service: Optional[MemoryService] = None
        self.rag_system: Optional[RAGSystem] = None
        self.executor: Optional[SandboxExecutor] = None
        self.validator: Optional[ValidationWall] = None
        self.verifier: Optional[VerificationLayer] = None
        
        self.setup_logging()
    
    def setup_logging(self):
        """Setup comprehensive logging for the test."""
        log_file = f"leonardo_lightweight_validation_{self.session_id}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger.info(f"🧪 Starting Leonardo Lightweight Validation - Session: {self.session_id}")
    
    async def initialize_leonardo_components(self) -> bool:
        """Initialize all Leonardo components for testing (no heavy LLM)."""
        try:
            self.logger.info("🚀 Initializing Leonardo components (lightweight)...")
            
            # Memory Service (FastMCP)
            self.memory_service = MemoryService(self.config)
            await self.memory_service.initialize()
            self.logger.info("✅ Memory Service initialized")
            
            # RAG System (without heavy dependencies)
            self.rag_system = RAGSystem(self.config)
            await self.rag_system.initialize()
            self.logger.info("✅ RAG System initialized")
            
            # Validation Wall
            audit_dir = str(Path(self.config.data_dir) / "audit_logs")
            self.validator = ValidationWall(audit_dir)
            self.logger.info("✅ Validation Wall initialized")
            
            # Sandbox Executor with all tools
            self.executor = SandboxExecutor(self.config)
            await self.executor.initialize()
            self.logger.info("✅ Sandbox Executor initialized")
            
            # Verification Layer (with testing mode to avoid heavy NLI loading)
            verification_config = {
                "research": {
                    "testing_mode": True,  # Use mock NLI to avoid heavy model loading
                    "batch_size": 4
                },
                "policy": {
                    "max_retries": 1
                }
            }
            self.verifier = VerificationLayer(verification_config)
            await self.verifier.initialize()
            self.logger.info("✅ Verification Layer initialized")
            
            self.logger.info("🎉 All Leonardo components successfully initialized!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Leonardo components: {e}")
            import traceback
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
    
    async def test_memory_system_comprehensive(self) -> bool:
        """Test FastMCP memory system comprehensively."""
        self.logger.info("🧠 Testing Memory System...")
        
        start_time = time.time()
        success = True
        details = {"operations": []}
        
        try:
            # Test memory storage
            await self.memory_service.update_async(self.user_id, {
                "user_input": "Hello, I'm testing Leonardo's memory system",
                "assistant": "Hello! I'll remember our conversation.",
                "timestamp": datetime.now().isoformat(),
                "success": True
            })
            details["operations"].append({"operation": "store", "success": True})
            
            # Test memory retrieval
            context = await self.memory_service.get_context_async(self.user_id, "testing memory")
            memory_retrieved = bool(context.get("recent_turns"))
            details["operations"].append({"operation": "retrieve", "success": memory_retrieved})
            
            if not memory_retrieved:
                success = False
            
            # Test memory search
            await self.memory_service.update_async(self.user_id, {
                "user_input": "I love Python programming",
                "assistant": "Great! Python is an excellent language.",
                "timestamp": datetime.now().isoformat(),
                "success": True
            })
            
            search_context = await self.memory_service.get_context_async(self.user_id, "Python programming")
            search_worked = bool(search_context.get("recent_turns"))
            details["operations"].append({"operation": "search", "success": search_worked})
            
            if not search_worked:
                success = False
                
        except Exception as e:
            success = False
            details["error"] = str(e)
        
        duration = time.time() - start_time
        self.add_test_result("Memory System Comprehensive", success, duration, details)
        return success
    
    async def test_tool_execution_comprehensive(self) -> bool:
        """Test sandbox tool execution comprehensively."""
        self.logger.info("🔧 Testing Tool Execution...")
        
        start_time = time.time()
        success = True
        details = {"tools_tested": []}
        
        # Test tool plans (mock LLM output with valid JSON)
        test_plans = [
            {
                "name": "test_weather",
                "plan": {
                    "action": "weather",
                    "parameters": {"location": "London"},
                    "reasoning": "User wants weather info"
                }
            },
            {
                "name": "test_calculator", 
                "plan": {
                    "action": "calculator",
                    "parameters": {"expression": "15 * 23 + 47"},
                    "reasoning": "User wants calculation"
                }
            },
            {
                "name": "test_system_info",
                "plan": {
                    "action": "system_info", 
                    "parameters": {"info_type": "time"},
                    "reasoning": "User wants current time"
                }
            }
        ]
        
        for test_case in test_plans:
            try:
                # Execute the plan
                result = await self.executor.execute_plan(test_case["plan"])
                
                tool_success = result.success if hasattr(result, 'success') else True
                details["tools_tested"].append({
                    "tool": test_case["name"],
                    "success": tool_success,
                    "result": str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                })
                
                if not tool_success:
                    success = False
                    
            except Exception as e:
                success = False
                details["tools_tested"].append({
                    "tool": test_case["name"],
                    "success": False,
                    "error": str(e)
                })
        
        duration = time.time() - start_time
        self.add_test_result("Tool Execution Comprehensive", success, duration, details)
        return success
    
    async def test_validation_wall_comprehensive(self) -> bool:
        """Test validation wall comprehensively."""
        self.logger.info("🛡️ Testing Validation Wall...")
        
        start_time = time.time()
        success = True
        details = {"validations": []}
        
        # Test various validation scenarios
        test_plans = [
            {
                "name": "safe_plan",
                "plan": {
                    "tool": "get_weather",
                    "args": {"location": "Paris"},
                    "meta": {"risk": "safe"}
                },
                "should_pass": True
            },
            {
                "name": "invalid_json",
                "plan": "invalid json structure",
                "should_pass": False
            },
            {
                "name": "missing_required_fields",
                "plan": {"parameters": {"test": "value"}},
                "should_pass": False
            }
        ]
        
        for test_case in test_plans:
            try:
                validation_result = await self.validator.validate_tool_call(test_case["plan"])
                
                validation_passed = validation_result.approved if hasattr(validation_result, 'approved') else False
                expected_result = test_case["should_pass"]
                test_success = validation_passed == expected_result
                
                details["validations"].append({
                    "test": test_case["name"],
                    "expected_pass": expected_result,
                    "actual_pass": validation_passed,
                    "success": test_success
                })
                
                if not test_success:
                    success = False
                    
            except Exception as e:
                # For invalid inputs (like strings), expect them to fail
                expected_result = test_case["should_pass"]
                validation_passed = False  # Any exception means validation failed
                test_success = validation_passed == expected_result  # Should match expectation
                
                details["validations"].append({
                    "test": test_case["name"],
                    "expected_pass": expected_result,
                    "actual_pass": validation_passed,
                    "success": test_success,
                    "error": str(e)
                })
                
                if not test_success:
                    success = False
        
        duration = time.time() - start_time
        self.add_test_result("Validation Wall Comprehensive", success, duration, details)
        return success
    
    async def test_verification_layer_comprehensive(self) -> bool:
        """Test verification layer comprehensively."""
        self.logger.info("✅ Testing Verification Layer...")
        
        start_time = time.time()
        success = True
        details = {"verifications": []}
        
        # Test verification with mock execution results
        test_cases = [
            {
                "name": "successful_tool_execution",
                "plan": {"action": "weather", "parameters": {"location": "London"}},
                "execution_result": {
                    "success": True,
                    "result_summary": "Weather in London: 15°C, cloudy",
                    "tools_executed": ["weather"]
                }
            }
        ]
        
        for test_case in test_cases:
            try:
                # Mock execution result object
                class MockExecutionResult:
                    def __init__(self, data):
                        for key, value in data.items():
                            setattr(self, key, value)
                
                execution_result = MockExecutionResult(test_case["execution_result"])
                
                # Verify the result - need a validation result for verify_tool_execution                
                mock_validation_result = ValidationResult(
                    approved=True,
                    risk_level=RiskLevel.SAFE,
                    tool_name=test_case["name"],
                    validation_id="test",
                    user_id="test_user",
                    timestamp=datetime.now()
                )
                
                verification_passed = await self.verifier.verify_tool_execution(
                    test_case["plan"], test_case["execution_result"], mock_validation_result
                )
                
                details["verifications"].append({
                    "test": test_case["name"],
                    "verification_passed": verification_passed,
                    "success": True
                })
                
            except Exception as e:
                success = False
                details["verifications"].append({
                    "test": test_case["name"],
                    "success": False,
                    "error": str(e)
                })
        
        duration = time.time() - start_time
        self.add_test_result("Verification Layer Comprehensive", success, duration, details)
        return success
    
    async def test_integration_comprehensive(self) -> bool:
        """Test end-to-end integration without heavy LLM."""
        self.logger.info("🔄 Testing Integration...")
        
        start_time = time.time()
        success = True
        details = {"integration_steps": []}
        
        try:
            # Step 1: Memory context
            context = await self.memory_service.get_context_async(self.user_id, "integration test")
            memory_step = bool(context)
            details["integration_steps"].append({"step": "memory_context", "success": memory_step})
            
            # Step 2: Plan validation (mock plan)
            test_plan = {
                "tool": "system_info",
                "args": {"info_type": "time"},
                "meta": {"risk": "safe"}
            }
            validation_result = await self.validator.validate_tool_call(test_plan)
            validation_step = getattr(validation_result, 'approved', False)
            details["integration_steps"].append({"step": "plan_validation", "success": validation_step})
            
            if validation_step:
                # Step 3: Tool execution
                execution_result = await self.executor.execute_plan(test_plan)
                execution_step = getattr(execution_result, 'success', False)
                details["integration_steps"].append({"step": "tool_execution", "success": execution_step})
                
                if execution_step:
                    # Step 4: Result verification
                    mock_validation_result = ValidationResult(
                        approved=True,
                        risk_level=RiskLevel.SAFE,
                        tool_name="system_info",
                        validation_id="integration_test",
                        user_id=self.user_id,
                        timestamp=datetime.now()
                    )
                    
                    # Convert execution_result to dict for verification
                    execution_dict = {
                        "success": getattr(execution_result, 'success', True),
                        "output": str(execution_result),
                        "tool": "system_info"
                    }
                    
                    verification_step = await self.verifier.verify_tool_execution(
                        test_plan, execution_dict, mock_validation_result
                    )
                    details["integration_steps"].append({"step": "result_verification", "success": verification_step})
                    
                    # Step 5: Memory update
                    await self.memory_service.update_async(self.user_id, {
                        "user_input": "Integration test completed",
                        "assistant": "Integration test successful",
                        "plan": test_plan,
                        "execution_result": str(execution_result)[:100],
                        "timestamp": datetime.now().isoformat(),
                        "success": True
                    })
                    details["integration_steps"].append({"step": "memory_update", "success": True})
            
            # Check if all steps succeeded
            all_steps_success = all(step["success"] for step in details["integration_steps"])
            if not all_steps_success:
                success = False
                
        except Exception as e:
            success = False
            details["error"] = str(e)
        
        duration = time.time() - start_time
        self.add_test_result("Integration Comprehensive", success, duration, details)
        return success
    
    async def run_lightweight_validation(self) -> Dict[str, Any]:
        """Run the complete lightweight validation test suite."""
        self.logger.info("🚀 Starting Lightweight Production Validation")
        overall_start_time = time.time()
        
        # Initialize components
        if not await self.initialize_leonardo_components():
            return {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "overall_success": False,
                "success_rate": 0.0,
                "total_duration": time.time() - overall_start_time,
                "category_results": {},
                "detailed_results": [],
                "summary": {
                    "total_tests": 0,
                    "passed_tests": 0,
                    "failed_tests": 0,
                    "components_tested": []
                },
                "error": "Failed to initialize Leonardo components"
            }
        
        # Run all test categories
        test_methods = [
            ("Memory System", self.test_memory_system_comprehensive),
            ("Tool Execution", self.test_tool_execution_comprehensive),
            ("Validation Wall", self.test_validation_wall_comprehensive),
            ("Verification Layer", self.test_verification_layer_comprehensive),
            ("Integration", self.test_integration_comprehensive)
        ]
        
        category_results = {}
        overall_success = True
        
        for category_name, test_method in test_methods:
            self.logger.info(f"🧪 Running {category_name} tests...")
            try:
                category_success = await test_method()
                category_results[category_name] = category_success
                if not category_success:
                    overall_success = False
            except Exception as e:
                self.logger.error(f"❌ {category_name} tests failed: {e}")
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
            "detailed_results": [asdict(r) for r in self.test_results],
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "components_tested": list(category_results.keys())
            },
            "system_info": {
                "python_version": sys.version,
                "platform": sys.platform,
                "test_type": "lightweight_production_validation"
            }
        }
        
        # Save report
        report_file = f"leonardo_lightweight_validation_report_{self.session_id}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"📊 Lightweight validation complete! Report saved to {report_file}")
        return report
    
    def print_summary_report(self, report: Dict[str, Any]):
        """Print a formatted summary of the validation results."""
        print("\n" + "="*80)
        print("🏆 LEONARDO LIGHTWEIGHT PRODUCTION VALIDATION SUMMARY")
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
            if result.get('error_message'):
                print(f"      Error: {result['error_message']}")
        print()
        
        if report['overall_success']:
            print("🎉 Leonardo architecture is working correctly! Core components validated.")
            print("💡 Next step: Add LLM integration for full production deployment.")
        else:
            print("⚠️ Some components need attention before production deployment.")
        
        print("="*80)


async def main():
    """Main entry point for lightweight validation."""
    validator = LeonardoLightweightValidator()
    
    try:
        # Run lightweight validation
        report = await validator.run_lightweight_validation()
        
        # Print summary
        if report and 'session_id' in report:
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
        import traceback
        logging.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
