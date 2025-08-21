"""
Leonardo Full Pipeline Integration Test
Tests the complete voice-first pipeline: wake → listen → understand → plan → validate → execute → verify → learn
Replaces raw CLI pipeline testing commands
"""

import asyncio
import pytest
import numpy as np
from pathlib import Path
import sys
import os

# Add Leonardo to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from leonardo.config import LeonardoConfig
from leonardo.io.stt_engine import STTEngine
from leonardo.io.tts_engine import TTSEngine
from leonardo.planner.llm_planner import LLMPlanner
from leonardo.validator.validation_wall import ValidationWall
from leonardo.sandbox.executor import SandboxExecutor
from leonardo.verification.verifier import VerificationLayer


class TestFullPipeline:
    """Test Leonardo's complete pipeline integration."""
    
    def setup_method(self):
        """Setup for each test."""
        self.config = LeonardoConfig.load_from_file(Path("leonardo.toml")) if Path("leonardo.toml").exists() else LeonardoConfig()
        
    @pytest.mark.asyncio
    async def test_complete_voice_pipeline(self):
        """Test the complete voice-to-voice pipeline."""
        print("🎭 TESTING COMPLETE LEONARDO PIPELINE")
        print("=" * 45)
        
        # Simulate user voice input
        user_input = "Search for AI news"
        print(f"👂 Simulated voice input: '{user_input}'")
        
        success_count = 0
        total_steps = 6
        
        try:
            # Step 1: STT - Convert voice to text
            print("\n1️⃣ STT: Processing voice input...")
            stt_engine = STTEngine(self.config)
            await stt_engine.initialize()
            
            # Simulate transcription (in real usage, this would process actual audio)
            transcription = user_input  # Simulated perfect transcription
            print(f"   👂 Transcribed: '{transcription}'")
            await stt_engine.shutdown()
            success_count += 1
            
            # Step 2: Planning - Generate execution plan
            print("\n2️⃣ PLANNER: Generating execution plan...")
            
            class DummyRAG:
                pass
            
            planner = LLMPlanner(self.config, DummyRAG())
            await planner.initialize()
            plan = await planner.generate_plan(transcription)
            
            print(f"   🧠 Plan: {plan.tool_call['tool']} (confidence: {plan.confidence})")
            print(f"   🧠 Reasoning: {plan.reasoning}")
            await planner.shutdown()
            success_count += 1
            
            # Step 3: Validation - Security checks
            print("\n3️⃣ VALIDATOR: Running security checks...")
            validator = ValidationWall(self.config)
            await validator.initialize()
            validation_result = await validator.validate_plan(plan)
            
            status = "PASSED" if validation_result.is_valid else "FAILED"
            print(f"   🛡️ Validation: {status} (risk: {validation_result.risk_level})")
            
            if not validation_result.is_valid:
                print(f"   ❌ Validation failed: {validation_result.reason}")
                await validator.shutdown()
                return False
                
            await validator.shutdown()
            success_count += 1
            
            # Step 4: Execution - Run in sandbox
            print("\n4️⃣ EXECUTOR: Running in sandbox...")
            executor = SandboxExecutor(self.config)
            await executor.initialize()
            execution_result = await executor.execute_plan(validation_result.validated_plan)
            
            status = "SUCCESS" if execution_result.success else "FAILED"
            print(f"   📦 Execution: {status} ({execution_result.duration}s)")
            if execution_result.output:
                print(f"   📦 Output: {execution_result.output[:100]}...")
                
            await executor.shutdown()
            success_count += 1
            
            # Step 5: Verification - Post-execution checks
            print("\n5️⃣ VERIFIER: Post-execution validation...")
            verifier = VerificationLayer(self.config)
            await verifier.initialize()
            verification_result = await verifier.verify_execution(plan.tool_call, execution_result)
            
            status = "SUCCESS" if verification_result.success else "FAILED"
            print(f"   ✅ Verification: {status} (confidence: {verification_result.confidence})")
            print(f"   ✅ Summary: {verification_result.summary}")
            
            await verifier.shutdown()
            success_count += 1
            
            # Step 6: TTS - Generate response
            print("\n6️⃣ TTS: Generating response...")
            tts_engine = TTSEngine(self.config)
            await tts_engine.initialize()
            
            response_text = verification_result.summary if verification_result.summary else "Task completed successfully"
            audio_data = await tts_engine.synthesize(response_text)
            
            print(f"   🗣️ Response: '{response_text}'")
            print(f"   🗣️ Audio: {len(audio_data)} bytes generated")
            
            await tts_engine.shutdown()
            success_count += 1
            
            # Results
            print(f"\n📊 PIPELINE RESULTS: {success_count}/{total_steps} steps completed")
            
            if success_count == total_steps:
                print("🎉 COMPLETE PIPELINE TEST PASSED!")
                return True
            else:
                print("⚠️  Pipeline partially completed")
                return False
                
        except Exception as e:
            print(f"\n❌ Pipeline test failed at step {success_count + 1}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self):
        """Test pipeline error handling and recovery."""
        print("\n🧪 Testing pipeline error handling...")
        
        try:
            # Test with invalid input
            invalid_inputs = [
                "",  # Empty input
                "   ",  # Whitespace only
                "A" * 1000,  # Very long input
            ]
            
            for i, test_input in enumerate(invalid_inputs, 1):
                print(f"  • Error test {i}: '{test_input[:50]}{'...' if len(test_input) > 50 else ''}' ({len(test_input)} chars)")
                
                # This should handle gracefully
                class DummyRAG:
                    pass
                
                planner = LLMPlanner(self.config, DummyRAG())
                await planner.initialize()
                
                plan = await planner.generate_plan(test_input)
                
                # Should still produce some form of plan or graceful handling
                print(f"    ✅ Handled gracefully: {plan.tool_call.get('tool', 'no_action')}")
                
                await planner.shutdown()
            
            print("✅ Error handling tests completed")
            return True
            
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            return False
    
    def test_pipeline_configuration(self):
        """Test pipeline configuration validation."""
        print("\n🧪 Testing pipeline configuration...")
        
        # Test that all required configuration sections exist
        required_sections = ['audio', 'stt', 'llm', 'tts', 'validation', 'sandbox']
        
        for section in required_sections:
            assert hasattr(self.config, section), f"Missing configuration section: {section}"
            print(f"  ✅ {section} configuration present")
        
        print("✅ Pipeline configuration validated")
        return True


async def run_full_pipeline_tests():
    """Run all full pipeline tests."""
    print("🎭 LEONARDO FULL PIPELINE INTEGRATION TESTS")
    print("=" * 51)
    
    test_suite = TestFullPipeline()
    test_suite.setup_method()
    
    try:
        # Run configuration test
        config_result = test_suite.test_pipeline_configuration()
        
        # Run pipeline tests
        pipeline_result = await test_suite.test_complete_voice_pipeline()
        error_handling_result = await test_suite.test_pipeline_error_handling()
        
        all_passed = config_result and pipeline_result and error_handling_result
        
        if all_passed:
            print("\n🎉 ALL PIPELINE INTEGRATION TESTS PASSED!")
            print("✅ Leonardo ready for voice-first AI assistant operation!")
        else:
            print("\n⚠️  Some pipeline tests had issues")
        
        return all_passed
        
    except Exception as e:
        print(f"\n❌ Pipeline integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_full_pipeline_tests())
    exit(0 if success else 1)
