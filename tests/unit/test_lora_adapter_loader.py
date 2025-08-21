"""
Leonardo LoRA Adapter Loader Tests
Tests the Colab-to-Leonardo LoRA adapter workflow
"""

import pytest
import asyncio
import json
from pathlib import Path
import tempfile
import shutil
import sys
import os

# Add Leonardo to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from leonardo.config import LeonardoConfig
from leonardo.learn.lora_adapter_loader import LoRAAdapterLoader


class TestLoRAAdapterLoader:
    """Test Leonardo's LoRA adapter loading system."""
    
    def setup_method(self):
        """Setup for each test."""
        self.config = LeonardoConfig()
        
    def create_mock_adapter(self, adapter_path: Path, metadata: dict = None):
        """Create a mock LoRA adapter directory for testing."""
        adapter_path.mkdir(parents=True, exist_ok=True)
        
        # Create mock adapter files
        (adapter_path / "adapter_config.json").write_text('{"adapter_type": "lora", "r": 16}')
        (adapter_path / "adapter_model.safetensors").write_text("mock_model_data")
        
        # Create metadata
        default_metadata = {
            "adapter_name": adapter_path.name,
            "base_model": "Qwen/Qwen2.5-7B-Instruct",
            "training_date": "20241219_140000",
            "lora_rank": 16,
            "training_steps": 100,
            "dataset_size": 500,
            "colab_gpu": "T4"
        }
        
        if metadata:
            default_metadata.update(metadata)
        
        with open(adapter_path / "leonardo_metadata.json", "w") as f:
            json.dump(default_metadata, f, indent=2)
    
    def test_adapter_loader_initialization(self):
        """Test LoRA adapter loader initialization."""
        print("🧪 Testing LoRA adapter loader initialization...")
        
        loader = LoRAAdapterLoader(self.config)
        
        # Check basic properties
        assert loader.config == self.config
        assert loader.registry_path.name == "lora_registry"
        assert loader.current_adapter is None
        
        print("✅ LoRA adapter loader initialized successfully")
    
    def test_list_available_adapters(self):
        """Test listing available adapters."""
        print("🧪 Testing adapter listing...")
        
        loader = LoRAAdapterLoader(self.config)
        
        # Create temp registry with mock adapters
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "lora_registry"
            loader.registry_path = registry_path
            
            # Create mock adapters
            self.create_mock_adapter(
                registry_path / "leonardo-v1",
                {"adapter_name": "leonardo-v1", "training_steps": 100}
            )
            self.create_mock_adapter(
                registry_path / "leonardo-v2", 
                {"adapter_name": "leonardo-v2", "training_steps": 200}
            )
            
            # List adapters
            adapters = loader.list_available_adapters()
            
            assert len(adapters) == 2
            assert "leonardo-v1" in adapters
            assert "leonardo-v2" in adapters
            assert adapters["leonardo-v1"]["training_steps"] == 100
            assert adapters["leonardo-v2"]["training_steps"] == 200
            
            print(f"✅ Found {len(adapters)} adapters: {list(adapters.keys())}")
    
    @pytest.mark.asyncio
    async def test_install_adapter_from_colab(self):
        """Test installing adapter from Colab directory."""
        print("🧪 Testing Colab adapter installation...")
        
        loader = LoRAAdapterLoader(self.config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup paths
            colab_path = Path(temp_dir) / "colab_adapter"
            registry_path = Path(temp_dir) / "lora_registry"
            loader.registry_path = registry_path
            
            # Create mock Colab adapter
            self.create_mock_adapter(colab_path, {"source": "colab"})
            
            # Install adapter
            success = await loader.install_adapter_from_colab(
                str(colab_path), 
                "test-adapter"
            )
            
            assert success
            assert (registry_path / "test-adapter").exists()
            assert (registry_path / "test-adapter" / "leonardo_metadata.json").exists()
            
            # Verify metadata
            with open(registry_path / "test-adapter" / "leonardo_metadata.json") as f:
                metadata = json.load(f)
            assert metadata["source"] == "colab"
            
            print("✅ Colab adapter installed successfully")
    
    def test_adapter_info_retrieval(self):
        """Test getting adapter information."""
        print("🧪 Testing adapter info retrieval...")
        
        loader = LoRAAdapterLoader(self.config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "lora_registry"
            loader.registry_path = registry_path
            
            # Create mock adapter
            test_metadata = {
                "adapter_name": "test-adapter",
                "base_model": "Qwen/Qwen2.5-7B-Instruct",
                "training_steps": 150,
                "colab_gpu": "A100"
            }
            self.create_mock_adapter(registry_path / "test-adapter", test_metadata)
            
            # Simulate loading adapter
            loader.current_adapter = "test-adapter"
            
            # Get info
            info = loader.get_adapter_info()
            
            assert info is not None
            assert info["adapter_name"] == "test-adapter"
            assert info["training_steps"] == 150
            assert info["colab_gpu"] == "A100"
            
            print(f"✅ Retrieved adapter info: {info['adapter_name']}")
    
    def test_adapter_workflow_documentation(self):
        """Test that workflow documentation is complete."""
        print("🧪 Testing Colab workflow documentation...")
        
        # Check notebook exists
        notebook_path = Path("leonardo/learn/notebooks/leonardo_unsloth_training.ipynb")
        assert notebook_path.exists(), "Colab training notebook not found"
        
        # Check registry directory exists
        registry_path = Path("leonardo/learn/lora_registry")
        assert registry_path.exists(), "LoRA registry directory not found"
        
        print("✅ Colab workflow documentation complete")
        print("  • Training notebook: leonardo/learn/notebooks/leonardo_unsloth_training.ipynb")
        print("  • Adapter registry: leonardo/learn/lora_registry/")


async def run_lora_adapter_tests():
    """Run all LoRA adapter tests."""
    print("🎭 LEONARDO LORA ADAPTER LOADER TESTS")
    print("=" * 45)
    
    test_suite = TestLoRAAdapterLoader()
    test_suite.setup_method()
    
    try:
        # Run sync tests
        test_suite.test_adapter_loader_initialization()
        test_suite.test_list_available_adapters()
        test_suite.test_adapter_info_retrieval()
        test_suite.test_adapter_workflow_documentation()
        
        # Run async tests
        await test_suite.test_install_adapter_from_colab()
        
        print("\n🎉 ALL LORA ADAPTER TESTS PASSED!")
        print("✅ Colab-to-Leonardo workflow ready!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ LoRA adapter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_lora_adapter_tests())
    exit(0 if success else 1)
