#!/usr/bin/env python3
"""
Leonardo Diagnostic Test
========================

Single focused test to diagnose what's working vs broken after recent changes.
Tests each pipeline component individually to identify issues.

This is our "first aid" test to get Leonardo back to working state.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add Leonardo to path
sys.path.append(str(Path(__file__).parent.parent))

# Intel Mac optimizations
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1" 
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from leonardo.config import LeonardoConfig
from leonardo.memory.service import MemoryService
from leonardo.planner.llm_planner import LLMPlanner
from leonardo.validation.validation_wall import ValidationWall
from leonardo.sandbox.executor import SandboxExecutor
from leonardo.verification.verification_layer import VerificationLayer
from leonardo.rag.rag_system import RAGSystem

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LeonardoDiagnostic:
    """Single test class to diagnose Leonardo's current state."""
    
    def __init__(self):
        self.config_path = Path(__file__).parent.parent / "leonardo.toml"
        self.config = LeonardoConfig.load_from_file(self.config_path)
        self.results = {}
        
    async def test_01_config_loading(self):
        """Test: Configuration system"""
        try:
            logger.info("🔍 Testing: Configuration Loading")
            assert self.config is not None
            assert hasattr(self.config, 'llm')
            assert hasattr(self.config, 'data_dir')
            self.results['config'] = {'status': 'PASS', 'error': None}
            logger.info("✅ Configuration loading: PASS")
            return True
        except Exception as e:
            self.results['config'] = {'status': 'FAIL', 'error': str(e)}
            logger.error(f"❌ Configuration loading: FAIL - {e}")
            return False
    
    async def test_02_memory_service(self):
        """Test: Memory Service Initialization"""
        try:
            logger.info("🔍 Testing: Memory Service")
            memory_service = MemoryService(self.config)
            await memory_service.initialize()
            
            # Test basic memory operations
            test_turn = {
                "user_input": "Hello, I'm testing memory",
                "assistant": "Hello! Test response.",
                "timestamp": "2025-08-20T10:00:00Z"
            }
            await memory_service.update_async("test_user", test_turn)
            context = await memory_service.get_context_async("test_user", "test query")
            
            assert memory_service.is_initialized()
            assert 'recent_turns' in context
            self.results['memory'] = {'status': 'PASS', 'error': None}
            logger.info("✅ Memory Service: PASS")
            return True
        except Exception as e:
            self.results['memory'] = {'status': 'FAIL', 'error': str(e)}
            logger.error(f"❌ Memory Service: FAIL - {e}")
            return False
    
    async def test_03_llm_planner(self):
        """Test: LLM Planner with constrained generation"""
        try:
            logger.info("🔍 Testing: LLM Planner")
            memory_service = MemoryService(self.config)
            await memory_service.initialize()
            rag_system = RAGSystem(self.config)
            
            planner = LLMPlanner(self.config, rag_system, memory_service)
            await planner.initialize()
            
            # Test simple planning
            plan = await planner.generate_plan("Hello, I'm testing the planner")
            
            assert plan is not None
            assert plan.tool_call is not None
            assert 'tool' in plan.tool_call
            self.results['planner'] = {'status': 'PASS', 'error': None, 'plan': plan.tool_call}
            logger.info(f"✅ LLM Planner: PASS - Generated: {plan.tool_call['tool']}")
            return True
        except Exception as e:
            self.results['planner'] = {'status': 'FAIL', 'error': str(e)}
            logger.error(f"❌ LLM Planner: FAIL - {e}")
            return False
    
    async def test_04_validation_wall(self):
        """Test: Validation Wall"""
        try:
            logger.info("🔍 Testing: Validation Wall")
            audit_dir = str(Path(self.config.data_dir) / "audit_logs")
            Path(audit_dir).mkdir(parents=True, exist_ok=True)
            
            validator = ValidationWall(audit_dir)
            
            # Test safe tool call
            safe_tool_call = {"tool": "respond", "args": {"message": "Hello"}, "meta": {"risk": "safe"}}
            result = validator.validate_tool_call(safe_tool_call)
            
            assert result is not None
            self.results['validation'] = {'status': 'PASS', 'error': None, 'result': result.approved}
            logger.info(f"✅ Validation Wall: PASS - Safe tool approved: {result.approved}")
            return True
        except Exception as e:
            self.results['validation'] = {'status': 'FAIL', 'error': str(e)}
            logger.error(f"❌ Validation Wall: FAIL - {e}")
            return False
    
    async def test_05_sandbox_executor(self):
        """Test: Sandbox Executor"""
        try:
            logger.info("🔍 Testing: Sandbox Executor")
            executor = SandboxExecutor(self.config)
            
            # Test simple tool execution
            safe_tool_call = {"tool": "respond", "args": {"message": "Hello from executor"}, "meta": {"risk": "safe"}}
            result = await executor.execute_plan(safe_tool_call)
            
            assert result is not None
            assert result.success == True
            self.results['executor'] = {'status': 'PASS', 'error': None, 'output': result.output[:50]}
            logger.info(f"✅ Sandbox Executor: PASS - Output: {result.output[:50]}...")
            return True
        except Exception as e:
            self.results['executor'] = {'status': 'FAIL', 'error': str(e)}
            logger.error(f"❌ Sandbox Executor: FAIL - {e}")
            return False
    
    async def test_06_verification_layer(self):
        """Test: Verification Layer"""
        try:
            logger.info("🔍 Testing: Verification Layer")
            verification_config = {
                'research': {'entailment_threshold': 0.6, 'coverage_threshold': 0.8},
                'policy': {'max_retries': 1}
            }
            verifier = VerificationLayer(verification_config)
            await verifier.initialize()
            
            # Mock verification test
            mock_tool_call = {"tool": "respond", "args": {"message": "Test"}, "meta": {"risk": "safe"}}
            mock_execution_result = type('MockResult', (), {'success': True, 'output': 'Test output'})()
            mock_validation_result = type('MockResult', (), {'approved': True})()
            
            result = await verifier.verify_tool_execution(mock_tool_call, mock_execution_result, mock_validation_result)
            
            assert result is not None
            self.results['verification'] = {'status': 'PASS', 'error': None}
            logger.info("✅ Verification Layer: PASS")
            return True
        except Exception as e:
            self.results['verification'] = {'status': 'FAIL', 'error': str(e)}
            logger.error(f"❌ Verification Layer: FAIL - {e}")
            return False
    
    async def test_07_tool_availability(self):
        """Test: Available Tools Match LLM Expectations"""
        try:
            logger.info("🔍 Testing: Tool Availability")
            executor = SandboxExecutor(self.config)
            
            # Get available tools
            available_tools = list(executor.get_available_tools().keys())
            logger.info(f"Available tools: {available_tools}")
            
            # Check for common tools LLM might try to use
            expected_tools = ['respond', 'get_weather', 'system_info', 'calculate']
            missing_tools = [tool for tool in expected_tools if tool not in available_tools]
            problematic_tools = ['recall_memory']  # Tools LLM tries to use but don't exist
            
            self.results['tools'] = {
                'status': 'PASS' if not missing_tools else 'WARN',
                'available': available_tools,
                'missing_expected': missing_tools,
                'problematic': [tool for tool in problematic_tools if tool not in available_tools]
            }
            logger.info(f"✅ Tool Availability: Available={len(available_tools)}, Missing={missing_tools}")
            return True
        except Exception as e:
            self.results['tools'] = {'status': 'FAIL', 'error': str(e)}
            logger.error(f"❌ Tool Availability: FAIL - {e}")
            return False
    
    async def test_08_integration_mini_pipeline(self):
        """Test: Mini end-to-end pipeline"""
        try:
            logger.info("🔍 Testing: Mini Integration Pipeline")
            
            # Initialize components
            memory_service = MemoryService(self.config)
            await memory_service.initialize()
            rag_system = RAGSystem(self.config)
            planner = LLMPlanner(self.config, rag_system, memory_service)
            await planner.initialize()
            
            audit_dir = str(Path(self.config.data_dir) / "audit_logs")
            Path(audit_dir).mkdir(parents=True, exist_ok=True)
            validator = ValidationWall(audit_dir)
            executor = SandboxExecutor(self.config)
            
            # Mini pipeline test
            user_input = "Hello Leonardo, respond with a greeting"
            
            # 1. Plan
            plan = await planner.generate_plan(user_input)
            assert plan is not None and plan.tool_call is not None
            
            # 2. Validate
            validation_result = validator.validate_tool_call(plan.tool_call)
            assert validation_result.approved
            
            # 3. Execute
            execution_result = await executor.execute_plan(plan.tool_call)
            assert execution_result.success
            
            # 4. Store in memory
            turn = {
                "user_input": user_input,
                "assistant": execution_result.output,
                "tool_used": plan.tool_call['tool']
            }
            await memory_service.update_async("test_user", turn)
            
            self.results['integration'] = {'status': 'PASS', 'error': None, 'output': execution_result.output}
            logger.info(f"✅ Mini Integration: PASS - {execution_result.output[:50]}...")
            return True
        except Exception as e:
            self.results['integration'] = {'status': 'FAIL', 'error': str(e)}
            logger.error(f"❌ Mini Integration: FAIL - {e}")
            return False
    
    async def run_all_tests(self):
        """Run all diagnostic tests"""
        logger.info("🚀 Starting Leonardo Diagnostic Test Suite")
        logger.info("=" * 60)
        
        tests = [
            self.test_01_config_loading,
            self.test_02_memory_service,
            self.test_03_llm_planner,
            self.test_04_validation_wall,
            self.test_05_sandbox_executor,
            self.test_06_verification_layer,
            self.test_07_tool_availability,
            self.test_08_integration_mini_pipeline
        ]
        
        results = []
        for test in tests:
            try:
                success = await test()
                results.append(success)
            except Exception as e:
                logger.error(f"Test {test.__name__} crashed: {e}")
                results.append(False)
        
        # Summary
        logger.info("=" * 60)
        logger.info("🏆 LEONARDO DIAGNOSTIC SUMMARY")
        logger.info("=" * 60)
        
        passed = sum(results)
        total = len(results)
        
        for component, result in self.results.items():
            status_icon = "✅" if result['status'] == 'PASS' else "⚠️" if result['status'] == 'WARN' else "❌"
            logger.info(f"{status_icon} {component.upper()}: {result['status']}")
            if result.get('error'):
                logger.info(f"   Error: {result['error']}")
        
        logger.info(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        # Critical issues
        if self.results.get('config', {}).get('status') == 'FAIL':
            logger.error("🚨 CRITICAL: Configuration loading failed - fix this first!")
        if self.results.get('planner', {}).get('status') == 'FAIL':
            logger.error("🚨 CRITICAL: LLM Planner failed - Leonardo can't think!")
        if self.results.get('integration', {}).get('status') == 'FAIL':
            logger.error("🚨 CRITICAL: Integration pipeline failed - core functionality broken!")
        
        return passed == total

async def main():
    """Run Leonardo diagnostic tests"""
    diagnostic = LeonardoDiagnostic()
    success = await diagnostic.run_all_tests()
    
    if success:
        logger.info("🎉 Leonardo is healthy! All systems operational.")
        return 0
    else:
        logger.error("⚠️ Leonardo has issues that need fixing.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
