"""
Main Leonardo assistant class.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from .config import LeonardoConfig
from .io.audio_pipeline import AudioPipeline
from .planner.llm_planner import LLMPlanner
from .validator.validation_wall import ValidationWall
from .sandbox.executor import SandboxExecutor
from .verification.verification_layer import VerificationLayer
from .rag.rag_system import RAGSystem
from .learn.learning_system import LearningSystem
# Legacy MCP interface removed - using FastMCP for memory instead
from .memory.service import MemoryService


class Leonardo:
    """
    Main Leonardo voice-first AI assistant.
    
    Architecture: wake → listen → understand → plan → validate → execute → verify → learn
    """
    
    def __init__(self, config: Optional[LeonardoConfig] = None):
        """Initialize Leonardo with configuration."""
        self.config = config or LeonardoConfig()
        self.config.setup_directories()
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Core components (initialized in startup)
        self.audio_pipeline: Optional[AudioPipeline] = None
        self.planner: Optional[LLMPlanner] = None
        self.validator: Optional[ValidationWall] = None
        self.executor: Optional[SandboxExecutor] = None
        self.verifier: Optional[VerificationLayer] = None
        self.rag_system: Optional[RAGSystem] = None
        self.learning_system: Optional[LearningSystem] = None
        self.memory_service: Optional[MemoryService] = None
        
        # Runtime state
        self._running = False
        self._session_id: Optional[str] = None
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        log_level = getattr(logging, self.config.log_level.upper())
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.data_dir / "logs" / "leonardo.log"),
                logging.StreamHandler()
            ]
        )
    
    async def startup(self) -> None:
        """Initialize all Leonardo components."""
        self.logger.info("🎭 Initializing Leonardo...")
        
        try:
            # Initialize Memory Service first (needed by planner)
            self.logger.info("🧠 Initializing Memory Service...")
            self.memory_service = MemoryService(self.config)
            await self.memory_service.initialize()
            
            # Initialize RAG system (needed by planner)
            self.logger.info("📚 Initializing RAG system...")
            self.rag_system = RAGSystem(self.config)
            await self.rag_system.initialize()
            
            # Initialize audio pipeline
            self.logger.info("🎙️ Initializing audio pipeline...")
            self.audio_pipeline = AudioPipeline(self.config)
            await self.audio_pipeline.initialize()
            
            # Initialize LLM planner (with memory and RAG)
            self.logger.info("🤔 Initializing LLM planner...")
            self.planner = LLMPlanner(self.config, self.rag_system, self.memory_service)
            await self.planner.initialize()
            
            # Initialize validation wall
            self.logger.info("🛡️ Initializing validation wall...")
            self.validator = ValidationWall(self.config)
            await self.validator.initialize()
            
            # Initialize sandbox executor
            self.logger.info("📦 Initializing sandbox executor...")
            self.executor = SandboxExecutor(self.config)
            await self.executor.initialize()
            
            # Initialize verification layer
            self.logger.info("✅ Initializing verification layer...")
            self.verifier = VerificationLayer(self.config)
            await self.verifier.initialize()
            
            # Initialize learning system
            self.logger.info("🧑‍🎓 Initializing learning system...")
            self.learning_system = LearningSystem(self.config)
            await self.learning_system.initialize()
            
            # Note: Using FastMCP for memory operations instead of general MCP interface
            
            self.logger.info("🚀 Leonardo initialization complete!")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Leonardo: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Cleanup all Leonardo components."""
        self.logger.info("🛑 Shutting down Leonardo...")
        self._running = False
        
        # Shutdown components in reverse order
        components = [
            ("Learning System", self.learning_system),
            ("Verification Layer", self.verifier),
            ("Sandbox Executor", self.executor),
            ("Validation Wall", self.validator),
            ("LLM Planner", self.planner),
            ("Audio Pipeline", self.audio_pipeline),
            ("RAG System", self.rag_system),
            ("Memory Service", self.memory_service),
        ]
        
        for name, component in components:
            if component:
                try:
                    await component.shutdown()
                    self.logger.info(f"✅ {name} shutdown complete")
                except Exception as e:
                    self.logger.error(f"❌ Error shutting down {name}: {e}")
        
        self.logger.info("👋 Leonardo shutdown complete")
    
    async def start_voice_loop(self) -> None:
        """Start the main voice interaction loop."""
        if not all([self.audio_pipeline, self.planner, self.validator, self.executor]):
            raise RuntimeError("Leonardo not properly initialized. Call startup() first.")
        
        self.logger.info("🎙️ Starting voice interaction loop...")
        self._running = True
        
        try:
            # Start audio pipeline
            audio_stream = self.audio_pipeline.start_streaming()
            
            async for audio_chunk in audio_stream:
                if not self._running:
                    break
                
                await self._process_audio_chunk(audio_chunk)
                
        except Exception as e:
            self.logger.error(f"❌ Voice loop error: {e}")
            raise
        finally:
            await self.audio_pipeline.stop_streaming()
    
    async def _process_audio_chunk(self, audio_chunk: bytes) -> None:
        """Process a single audio chunk through the complete pipeline."""
        try:
            # Step 1: Speech-to-Text
            transcription = await self.audio_pipeline.transcribe(audio_chunk)
            if not transcription.strip():
                return
            
            self.logger.info(f"👂 Heard: {transcription}")
            
            # Step 2: Plan (LLM generates JSON tool calls with memory context)
            user_id = self._session_id or "default"  # Use session ID or default
            plan = await self.planner.generate_plan(transcription, user_id)
            if not plan:
                return
            
            self.logger.info(f"🧠 Plan: {plan}")
            
            # Step 3: Validate (Safety checks)
            validation_result = await self.validator.validate_plan(plan)
            if not validation_result.is_valid:
                self.logger.warning(f"🚫 Plan rejected: {validation_result.reason}")
                await self._speak_response(f"I can't do that: {validation_result.reason}")
                return
            
            # Step 4: Execute (Sandbox execution)
            execution_result = await self.executor.execute_plan(validation_result.validated_plan)
            
            # Step 5: Verify (Post-execution checks)
            verification_result = await self.verifier.verify_execution(
                plan, execution_result
            )
            
            # Step 6: Respond (TTS output)
            response = self._generate_response(verification_result)
            await self._speak_response(response)
            
            # Step 7: Update Memory (Store complete turn)
            if self.memory_service:
                turn_data = {
                    "user": transcription,
                    "assistant": response,
                    "assistant_plan": plan.tool_call,
                    "validation": validation_result.dict(),
                    "execution": execution_result.dict(),
                    "verification": verification_result.dict(),
                    "response_type": plan.tool_call.get("tool", "unknown"),
                    "success": verification_result.success
                }
                self.memory_service.update(user_id, turn_data)
            
            # Step 8: Learn (Update rewards and potentially fine-tune)
            await self.learning_system.record_interaction(
                transcription, plan, execution_result, verification_result
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error processing audio: {e}")
            await self._speak_response("I encountered an error processing that request.")
    
    async def _speak_response(self, text: str) -> None:
        """Convert text to speech and play."""
        try:
            await self.audio_pipeline.speak(text)
        except Exception as e:
            self.logger.error(f"❌ TTS error: {e}")
    
    def _generate_response(self, verification_result) -> str:
        """Generate spoken response from verification result."""
        if verification_result.success:
            if verification_result.summary:
                return verification_result.summary
            return "Done."
        else:
            return f"I couldn't complete that task: {verification_result.error}"
    
    async def teach_command(self, command_id: str, description: str, 
                           tool: str, schema: Dict[str, Any], 
                           examples: list, permission_level: str = "safe") -> bool:
        """Teach Leonardo a new command."""
        try:
            success = await self.learning_system.register_command(
                command_id, description, tool, schema, examples, permission_level
            )
            
            if success:
                # Hot-reload command registry
                await self.rag_system.refresh_command_registry()
                self.logger.info(f"✅ Taught new command: {command_id}")
                return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to teach command {command_id}: {e}")
        
        return False
    
    async def teach_synonym(self, phrase: str, canonical: str, scope: str = "global") -> bool:
        """Teach Leonardo a new phrase synonym."""
        try:
            success = await self.learning_system.register_synonym(phrase, canonical, scope)
            
            if success:
                # Hot-reload lexicon
                await self.rag_system.refresh_lexicon()
                self.logger.info(f"✅ Taught synonym: '{phrase}' -> '{canonical}'")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Failed to teach synonym: {e}")
        
        return False
    
    @asynccontextmanager
    async def session(self):
        """Async context manager for Leonardo session."""
        await self.startup()
        try:
            yield self
        finally:
            await self.shutdown()


async def main():
    """Main entry point for Leonardo."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Leonardo Voice-First AI Assistant")
    parser.add_argument("--config", type=Path, help="Configuration file path")
    parser.add_argument("--voice", action="store_true", help="Start voice interaction")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--init", action="store_true", help="Initialize Leonardo")
    
    args = parser.parse_args()
    
    # Load configuration
    config = LeonardoConfig()
    if args.config and args.config.exists():
        config = LeonardoConfig.load_from_file(args.config)
    
    if args.debug:
        config.debug = True
        config.log_level = "DEBUG"
    
    # Initialize Leonardo
    leonardo = Leonardo(config)
    
    if args.init:
        print("🎭 Initializing Leonardo for first run...")
        async with leonardo.session():
            print("✅ Leonardo initialized successfully!")
        return
    
    if args.voice:
        print("🎙️ Starting Leonardo voice assistant...")
        print("Say 'Leonardo' to wake up, or Ctrl+C to exit.")
        
        try:
            async with leonardo.session() as assistant:
                await assistant.start_voice_loop()
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
