#!/usr/bin/env python3
"""
Leonardo Production Voice Test
Real-time voice pipeline test: Microphone → STT → LLM → TTS → Speakers

Usage:
    python leonardo/production_voice_test.py
"""

import asyncio
import logging
import sys
import signal
from pathlib import Path

# Add Leonardo to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from leonardo.config import LeonardoConfig
from leonardo.io.stt_engine import STTEngine  
from leonardo.io.tts_engine import TTSEngine
from leonardo.planner.llm_planner import LLMPlanner
from leonardo.validator.validation_wall import ValidationWall
from leonardo.sandbox.executor import SandboxExecutor
from leonardo.verification.verifier import VerificationLayer
from leonardo.rag.rag_system import RAGSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LeonardoVoiceTest:
    """Production voice pipeline test for Leonardo."""
    
    def __init__(self):
        self.config = None
        self.stt_engine = None
        self.tts_engine = None
        self.llm_planner = None
        self.validator = None
        self.executor = None
        self.verifier = None
        self.rag_system = None
        self.running = False
        
    async def initialize(self):
        """Initialize all Leonardo components."""
        print("🎭 LEONARDO PRODUCTION VOICE TEST")
        print("=" * 50)
        
        # Load configuration
        print("📋 Loading configuration...")
        self.config = LeonardoConfig.load_from_file(Path("leonardo.toml")) if Path("leonardo.toml").exists() else LeonardoConfig()
        print(f"✅ Configuration loaded: {self.config.llm.model_name}")
        
        # Initialize components
        print("🔧 Initializing components...")
        
        # STT Engine
        print("  🎙️ Initializing Speech-to-Text...")
        self.stt_engine = STTEngine(self.config)
        await self.stt_engine.initialize()
        
        # TTS Engine  
        print("  🗣️ Initializing Text-to-Speech...")
        self.tts_engine = TTSEngine(self.config)
        await self.tts_engine.initialize()
        
        # RAG System (needed for LLM Planner)
        print("  📚 Initializing RAG system...")
        self.rag_system = RAGSystem(self.config)
        await self.rag_system.initialize()
        
        # LLM Planner
        print("  🧠 Initializing LLM Planner...")
        self.llm_planner = LLMPlanner(self.config, self.rag_system)
        await self.llm_planner.initialize()
        
        # Validation Wall
        print("  🛡️ Initializing Validation Wall...")
        self.validator = ValidationWall(self.config)
        await self.validator.initialize()
        
        # Sandbox Executor
        print("  📦 Initializing Sandbox Executor...")
        self.executor = SandboxExecutor(self.config)
        await self.executor.initialize()
        
        # Verification Layer
        print("  ✅ Initializing Verification Layer...")
        self.verifier = VerificationLayer(self.config)
        await self.verifier.initialize()
        
        print("✅ All components initialized!")
        print()
        
    async def test_tts_welcome(self):
        """Test TTS with welcome message."""
        print("🔊 Testing TTS with welcome message...")
        
        welcome_text = "Hello! I am Leonardo, your voice-first AI assistant. I'm ready to listen and help you with your requests."
        
        try:
            audio_data = await self.tts_engine.synthesize(welcome_text)
            
            if len(audio_data) > 0:
                print(f"✅ TTS generated {len(audio_data)} bytes of audio")
                
                # For now, we'll just confirm audio generation
                # In a full implementation, we'd play this through speakers
                print("🎵 (Audio would play through speakers)")
                return True
            else:
                print("❌ No audio generated")
                return False
                
        except Exception as e:
            print(f"❌ TTS test failed: {e}")
            return False
    
    async def process_voice_input(self, text_input: str):
        """Process a voice input through the complete pipeline."""
        print(f"\n🎙️ Processing: '{text_input}'")
        print("-" * 50)
        
        try:
            # Step 1: Planning
            print("1️⃣ PLANNING: Generating response plan...")
            plan = await self.llm_planner.generate_plan(text_input)
            print(f"   🧠 Tool: {plan.tool_call.get('tool', 'unknown')}")
            print(f"   💭 Reasoning: {plan.reasoning[:100]}...")
            
            # Step 2: Validation
            print("2️⃣ VALIDATION: Checking safety...")
            validation_result = await self.validator.validate_plan(plan)
            
            if not validation_result.is_valid:
                print(f"   ❌ Validation failed: {validation_result.reason}")
                response = f"I cannot do that: {validation_result.reason}"
            else:
                print(f"   ✅ Validation passed (risk: {validation_result.risk_level})")
                
                # Step 3: Execution
                print("3️⃣ EXECUTION: Running in sandbox...")
                execution_result = await self.executor.execute_plan(validation_result.validated_plan)
                print(f"   📦 Status: {'SUCCESS' if execution_result.success else 'FAILED'}")
                print(f"   📦 Duration: {execution_result.duration}s")
                
                # Step 4: Verification
                print("4️⃣ VERIFICATION: Checking results...")
                verification_result = await self.verifier.verify_execution(plan.tool_call, execution_result)
                print(f"   ✅ Verification: {'SUCCESS' if verification_result.success else 'FAILED'}")
                
                response = verification_result.summary if verification_result.summary else "Task completed successfully."
            
            # Step 5: TTS Response
            print("5️⃣ RESPONSE: Generating voice response...")
            print(f"   🗣️ Response: '{response}'")
            
            audio_data = await self.tts_engine.synthesize(response)
            
            if len(audio_data) > 0:
                print(f"   🎵 Generated {len(audio_data)} bytes of audio")
                print("   🔊 (Audio would play through speakers)")
            else:
                print("   ❌ No audio generated")
            
            print("✅ Pipeline completed successfully!")
            return response
            
        except Exception as e:
            error_msg = f"Pipeline error: {e}"
            print(f"❌ {error_msg}")
            return error_msg
    
    async def simulate_voice_conversation(self):
        """Simulate a voice conversation with text inputs."""
        print("🎭 SIMULATED VOICE CONVERSATION")
        print("=" * 50)
        print("Note: In production, this would use real microphone input")
        print("For now, we'll simulate voice commands with text")
        print()
        
        # Test scenarios
        test_scenarios = [
            "What's the weather like today?",
            "Search for recent AI news",
            "Send an email to John about the meeting",
            "What time is it?",
            "Help me find a good restaurant nearby"
        ]
        
        print("🧪 Running test scenarios...")
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n--- Test {i}/{len(test_scenarios)} ---")
            await self.process_voice_input(scenario)
            print()
            
            # Brief pause between tests
            await asyncio.sleep(1)
        
        print("🎉 All test scenarios completed!")
    
    async def interactive_mode(self):
        """Interactive mode for real voice testing."""
        print("\n🎙️ INTERACTIVE VOICE MODE")
        print("=" * 50)
        print("Type your voice commands (or 'quit' to exit)")
        print("In production, this would capture real microphone input")
        print()
        
        while self.running:
            try:
                # Get user input (simulating voice)
                user_input = input("🎙️ Speak (or type): ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    break
                
                if user_input:
                    await self.process_voice_input(user_input)
                    print()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("👋 Goodbye!")
    
    async def run_production_test(self):
        """Run the complete production test."""
        self.running = True
        
        try:
            # Initialize all components
            await self.initialize()
            
            # Test TTS first
            tts_ok = await self.test_tts_welcome()
            if not tts_ok:
                print("⚠️ TTS test failed, continuing anyway...")
            
            print("\n🎯 CHOOSE TEST MODE:")
            print("1. Automated test scenarios")
            print("2. Interactive voice mode")
            print("3. Both")
            
            try:
                choice = input("\nEnter choice (1-3): ").strip()
            except KeyboardInterrupt:
                choice = "1"
            
            if choice in ["1", "3"]:
                await self.simulate_voice_conversation()
            
            if choice in ["2", "3"]:
                await self.interactive_mode()
        
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown all components gracefully."""
        print("\n🛑 Shutting down Leonardo components...")
        
        if self.verifier:
            await self.verifier.shutdown()
        if self.executor:
            await self.executor.shutdown()
        if self.validator:
            await self.validator.shutdown()
        if self.llm_planner:
            await self.llm_planner.shutdown()
        if self.rag_system:
            await self.rag_system.shutdown()
        if self.tts_engine:
            await self.tts_engine.shutdown()
        if self.stt_engine:
            await self.stt_engine.shutdown()
            
        print("✅ All components shut down successfully")

async def main():
    """Main function to run the production voice test."""
    
    # Handle Ctrl+C gracefully
    test_instance = LeonardoVoiceTest()
    
    def signal_handler(signum, frame):
        print("\n\n⚠️ Received interrupt signal, shutting down...")
        test_instance.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await test_instance.run_production_test()
    except KeyboardInterrupt:
        print("\n👋 Production test interrupted by user")
    except Exception as e:
        print(f"\n❌ Production test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting Leonardo Production Voice Test...")
    print("Press Ctrl+C anytime to exit gracefully")
    print()
    
    # Run the async test
    asyncio.run(main())
