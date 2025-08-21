"""
Test file for Search-R1 Integration with Leonardo's Verification Layer

This test verifies that Search-R1 can be integrated with our verification
pipeline and provides multi-step reasoning with citation tracking.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo.verification.search_r1_integration import (
    SearchR1Integration, 
    SearchR1Config, 
    quick_research
)

async def test_search_r1_basic():
    """Test basic Search-R1 integration functionality."""
    print("🔍 Testing Search-R1 Basic Integration...")
    
    # Create configuration
    config = SearchR1Config(
        max_search_steps=3,
        retrieval_topk=5,
        enable_nli_verification=True,
        enable_citation_store=True
    )
    
    # Initialize integration
    integration = SearchR1Integration(config)
    
    # Check status before initialization
    status = integration.get_integration_status()
    print(f"📊 Pre-initialization status:")
    print(f"   Search-R1 available: {status['search_r1_available']}")
    print(f"   Leonardo verification available: {status['leonardo_verification_available']}")
    
    # Initialize
    success = await integration.initialize()
    print(f"🔧 Initialization: {'✅ Success' if success else '❌ Failed'}")
    
    if success:
        # Check post-initialization status
        status = integration.get_integration_status()
        print(f"📊 Post-initialization status:")
        print(f"   Initialized: {status['initialized']}")
        print(f"   Components: {status['components']}")
        
        return integration
    
    return None

async def test_search_r1_research():
    """Test Search-R1 multi-step research functionality."""
    print("\n🔍 Testing Search-R1 Research Pipeline...")
    
    integration = await test_search_r1_basic()
    if not integration:
        print("❌ Cannot test research - initialization failed")
        return
    
    # Test research queries
    test_queries = [
        "What is Leonardo AI assistant and how does it work?",
        "How does Search-R1 improve reasoning with search?",
        "What are the benefits of multi-step research?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🎯 Test Query {i}: '{query[:50]}...'")
        
        try:
            result = await integration.research_with_reasoning(query, max_steps=2)
            
            print(f"📊 Results:")
            print(f"   Steps taken: {len(result.reasoning_chain)}")
            print(f"   Total citations: {result.total_citations}")
            print(f"   NLI pass rate: {result.nli_pass_rate:.1%}")
            print(f"   Confidence: {result.confidence_score:.1%}")
            print(f"   Answer preview: {result.final_answer[:100]}...")
            
            # Show reasoning chain
            print(f"🔗 Reasoning Chain:")
            for step in result.reasoning_chain:
                print(f"   Step {step.step_id}: {step.query[:40]}... → {len(step.citations)} citations")
                
        except Exception as e:
            print(f"❌ Research failed: {e}")

async def test_quick_research():
    """Test the convenience quick_research function."""
    print("\n⚡ Testing Quick Research Function...")
    
    try:
        config = SearchR1Config(
            max_search_steps=2,
            enable_nli_verification=True
        )
        
        result = await quick_research(
            "What makes Leonardo different from other AI assistants?",
            config=config
        )
        
        print(f"✅ Quick research completed:")
        print(f"   Steps: {len(result.reasoning_chain)}")
        print(f"   Citations: {result.total_citations}")
        print(f"   Final answer: {result.final_answer[:150]}...")
        
    except Exception as e:
        print(f"❌ Quick research failed: {e}")

async def test_error_handling():
    """Test error handling and edge cases."""
    print("\n🛡️ Testing Error Handling...")
    
    # Test with empty query
    try:
        result = await quick_research("", SearchR1Config(max_search_steps=1))
        print(f"✅ Empty query handled: {len(result.reasoning_chain)} steps")
    except Exception as e:
        print(f"⚠️ Empty query error: {e}")
    
    # Test with very long query
    try:
        long_query = "What is " + "very " * 50 + "long query about AI?"
        result = await quick_research(long_query, SearchR1Config(max_search_steps=1))
        print(f"✅ Long query handled: {result.confidence_score:.1%} confidence")
    except Exception as e:
        print(f"⚠️ Long query error: {e}")

async def main():
    """Run all Search-R1 integration tests."""
    print("🚀 Starting Search-R1 Integration Tests")
    print("=" * 60)
    
    # Run test suite
    await test_search_r1_basic()
    await test_search_r1_research()
    await test_quick_research()
    await test_error_handling()
    
    print("\n" + "=" * 60)
    print("✅ Search-R1 Integration Tests Complete")

if __name__ == "__main__":
    asyncio.run(main())
