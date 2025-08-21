"""
Leonardo Test Runner
Professional test suite runner that replaces raw CLI testing commands
"""

import asyncio
import sys
import os
from pathlib import Path
import time

# Add Leonardo to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import test modules
from unit.test_config_system import run_config_tests
from unit.test_stt_engine import run_stt_tests
from unit.test_tts_engine import run_tts_tests
from unit.test_external_repos import run_external_repo_tests
from unit.test_lora_adapter_loader import run_lora_adapter_tests
from integration.test_full_pipeline import run_full_pipeline_tests


class LeonardoTestRunner:
    """Professional test runner for Leonardo AI Assistant."""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        
    def print_header(self):
        """Print test suite header."""
        print("=" * 80)
        print("🎭 LEONARDO AI ASSISTANT - PROFESSIONAL TEST SUITE")
        print("=" * 80)
        print("Comprehensive testing of all Leonardo components")
        print("Replaces raw CLI testing commands with structured tests")
        print("=" * 80)
        
    def print_footer(self, total_time):
        """Print test suite results summary."""
        print("=" * 80)
        print("📊 LEONARDO TEST SUITE RESULTS")
        print("=" * 80)
        
        passed = sum(1 for result in self.results.values() if result)
        total = len(self.results)
        
        for test_name, result in self.results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:<35}: {status}")
        
        print("-" * 80)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        print(f"Total Time: {total_time:.2f}s")
        print("=" * 80)
        
        if passed == total:
            print("🎉 ALL LEONARDO TESTS PASSED - SYSTEM READY!")
        else:
            print("⚠️  Some tests failed - check individual results above")
        
        return passed == total
    
    async def run_unit_tests(self):
        """Run all unit tests."""
        print("\n🔧 UNIT TESTS")
        print("-" * 40)
        
        # Configuration system tests
        print("\n📋 Configuration System Tests:")
        self.results["Configuration System"] = run_config_tests()
        
        # External repository tests
        print("\n📦 External Repository Tests:")
        self.results["External Repositories"] = run_external_repo_tests()
        
        # STT engine tests
        print("\n🎙️ STT Engine Tests:")
        self.results["STT Engine"] = await run_stt_tests()
        
        # TTS engine tests
        print("\n🗣️ TTS Engine Tests:")
        self.results["TTS Engine"] = await run_tts_tests()
        
        # LoRA adapter loader tests
        print("\n🧑‍🎓 LoRA Adapter Loader Tests:")
        self.results["LoRA Adapter Loader"] = await run_lora_adapter_tests()
    
    async def run_integration_tests(self):
        """Run all integration tests."""
        print("\n🔗 INTEGRATION TESTS")
        print("-" * 40)
        
        # Full pipeline tests
        print("\n🎭 Full Pipeline Integration Tests:")
        self.results["Full Pipeline"] = await run_full_pipeline_tests()
    
    async def run_all_tests(self):
        """Run the complete Leonardo test suite."""
        self.start_time = time.time()
        self.print_header()
        
        try:
            # Check environment
            print("🔍 Environment Check:")
            python_version = sys.version.split()[0]
            print(f"  • Python version: {python_version}")
            print(f"  • Working directory: {os.getcwd()}")
            
            if not Path("leonardo.toml").exists():
                print("  ⚠️  leonardo.toml not found - using default config")
            else:
                print("  ✅ leonardo.toml found")
            
            # Run test suites
            await self.run_unit_tests()
            await self.run_integration_tests()
            
            # Print results
            total_time = time.time() - self.start_time
            return self.print_footer(total_time)
            
        except Exception as e:
            print(f"❌ Test runner failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def run_specific_test(test_name):
    """Run a specific test by name."""
    test_map = {
        "config": run_config_tests,
        "external": run_external_repo_tests,
        "stt": run_stt_tests,
        "tts": run_tts_tests,
        "lora": run_lora_adapter_tests,
        "pipeline": run_full_pipeline_tests,
    }
    
    if test_name not in test_map:
        print(f"❌ Unknown test: {test_name}")
        print(f"Available tests: {', '.join(test_map.keys())}")
        return False
    
    print(f"🧪 Running {test_name} tests only...")
    
    if test_name in ["stt", "tts", "lora", "pipeline"]:
        # Async tests
        return asyncio.run(test_map[test_name]())
    else:
        # Sync tests
        return test_map[test_name]()


if __name__ == "__main__":
    # Check for specific test argument
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        success = run_specific_test(test_name)
    else:
        # Run all tests
        runner = LeonardoTestRunner()
        success = asyncio.run(runner.run_all_tests())
    
    exit(0 if success else 1)
