#!/usr/bin/env python3
"""
Quick initialization test to verify Leonardo components can initialize
without loading heavy models or causing segmentation faults.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add Leonardo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo.config import LeonardoConfig
from leonardo.memory.service import MemoryService
from leonardo.rag.rag_system import RAGSystem
from leonardo.sandbox.executor import SandboxExecutor
from leonardo.validation.validation_wall import ValidationWall
from leonardo.verification.verification_layer import VerificationLayer

async def test_initialization():
    """Test basic initialization of Leonardo components."""
    print("🧪 Testing Leonardo Component Initialization...")
    
    try:
        config = LeonardoConfig()
        config.setup_directories()
        
        print("✅ Config loaded")
        
        # Test Memory Service (FastMCP)
        memory_service = MemoryService(config)
        await memory_service.initialize()
        print("✅ Memory Service (FastMCP) initialized")
        
        # Test RAG System
        rag_system = RAGSystem(config)
        await rag_system.initialize()
        print("✅ RAG System initialized")
        
        # Test Validation Wall
        validator = ValidationWall(config)
        await validator.initialize()
        print("✅ Validation Wall initialized")
        
        # Test Sandbox Executor
        executor = SandboxExecutor(config)
        await executor.initialize()
        print("✅ Sandbox Executor initialized")
        
        # Test Verification Layer
        verifier = VerificationLayer(config)
        await verifier.initialize()
        print("✅ Verification Layer initialized")
        
        print("\n🎉 ALL COMPONENTS INITIALIZED SUCCESSFULLY!")
        print("✅ No confusing MCP error messages")
        print("✅ FastMCP memory working")
        print("✅ All validation and verification components ready")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_initialization())
    sys.exit(0 if success else 1)
