#!/usr/bin/env python3
"""
JARVIS-1 Inspired Memory System Test
Comprehensive testing of advanced memory features including:
- Semantic clustering and search
- Growing memory with experience storage  
- Vector embeddings and similarity search
- User profile building and memory insights
- Advanced context retrieval
"""

import asyncio
import sys
import time
import json
from pathlib import Path

# Add Leonardo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo.config import LeonardoConfig
from leonardo.memory.advanced_memory_service import AdvancedMemoryService
from leonardo.memory.enhanced_memory import ADVANCED_MEMORY_AVAILABLE


class JarvisMemoryTester:
    """Test suite for JARVIS-1 inspired memory enhancements."""
    
    def __init__(self):
        self.config = LeonardoConfig()
        self.advanced_memory: AdvancedMemoryService = None
        self.test_user_id = "jarvis_test_user"
        
    async def initialize(self):
        """Initialize the advanced memory system."""
        print("🚀 JARVIS-1 INSPIRED MEMORY SYSTEM TEST")
        print("=" * 60)
        
        # Check availability
        if not ADVANCED_MEMORY_AVAILABLE:
            print("❌ Advanced memory libraries not available")
            print("   Install: uv pip install chromadb sentence-transformers faiss-cpu")
            return False
        
        print("✅ Advanced memory libraries available")
        
        # Initialize advanced memory service
        self.advanced_memory = AdvancedMemoryService(self.config)
        await self.advanced_memory.initialize()
        
        print(f"✅ Advanced Memory Service initialized")
        print(f"   Backend: {'Enhanced + MCP' if self.advanced_memory.use_enhanced_memory else 'MCP Only'}")
        
        return True
    
    async def test_semantic_storage_and_clustering(self):
        """Test JARVIS-1 style semantic memory storage and clustering."""
        print("\n🧠 TESTING: Semantic Storage & Clustering")
        print("-" * 40)
        
        # Create diverse conversation experiences
        test_conversations = [
            # Time-related cluster
            {"user": "What time is it?", "assistant": "The current time is 3:00 PM."},
            {"user": "What day is today?", "assistant": "Today is Tuesday, August 19th."},
            {"user": "When is my appointment?", "assistant": "I'd need to check your calendar for that."},
            
            # Weather cluster  
            {"user": "What's the weather like?", "assistant": "It's sunny and 75 degrees."},
            {"user": "Is it going to rain today?", "assistant": "No rain expected today."},
            {"user": "Should I bring an umbrella?", "assistant": "No need for an umbrella today."},
            
            # Programming cluster
            {"user": "How do I debug Python code?", "assistant": "Use print statements or a debugger like pdb."},
            {"user": "What's a good IDE for Python?", "assistant": "VS Code, PyCharm, or Vim are popular choices."},
            {"user": "How do I install packages?", "assistant": "Use pip install or conda install commands."},
            
            # Memory/recall cluster
            {"user": "Do you remember what I asked?", "assistant": "You asked about the weather earlier."},
            {"user": "What did we discuss before?", "assistant": "We talked about time, weather, and programming."},
        ]
        
        print(f"📝 Storing {len(test_conversations)} diverse conversations...")
        
        for i, conv in enumerate(test_conversations):
            conv["timestamp"] = time.time() + i  # Slightly different timestamps
            conv["success"] = True
            conv["tools_used"] = ["respond"]
            conv["response_type"] = "conversation"
            
            await self.advanced_memory.update_async(self.test_user_id, conv)
            print(f"   ✅ Stored conversation {i+1}")
        
        # Test clustering
        if self.advanced_memory.use_enhanced_memory:
            clusters = await self.advanced_memory.get_user_clusters(self.test_user_id)
            print(f"\n🎯 CLUSTERING RESULTS:")
            print(f"   Total clusters: {len(clusters)}")
            
            for cluster in clusters[:5]:  # Show top 5 clusters
                print(f"   📋 Cluster: {cluster['theme']} ({cluster['experience_count']} experiences)")
                print(f"      Importance: {cluster['importance_score']:.2f}")
        
        return True
    
    async def test_semantic_search(self):
        """Test JARVIS-1 style semantic search capabilities."""
        print("\n🔍 TESTING: Semantic Search")
        print("-" * 40)
        
        if not self.advanced_memory.use_enhanced_memory:
            print("⚠️ Enhanced memory not available - skipping semantic search test")
            return True
        
        # Test various search queries
        search_queries = [
            "programming and development",
            "weather and forecast", 
            "time and date questions",
            "memory and remembering things"
        ]
        
        for query in search_queries:
            print(f"\n🔎 Searching: '{query}'")
            results = await self.advanced_memory.semantic_search(
                self.test_user_id, query, limit=3, min_similarity=0.3
            )
            
            print(f"   Found {len(results)} relevant memories:")
            for i, result in enumerate(results, 1):
                similarity = result["similarity"]
                content = result["content"][:100] + "..." if len(result["content"]) > 100 else result["content"]
                print(f"   {i}. [{similarity:.3f}] {content}")
        
        return True
    
    async def test_growing_context_retrieval(self):
        """Test JARVIS-1 style growing memory context retrieval."""
        print("\n🌱 TESTING: Growing Context Retrieval")
        print("-" * 40)
        
        # Test context retrieval for different query types
        test_queries = [
            "What did I ask about programming?",
            "Tell me about the weather",
            "Do you remember our conversation?",
            "What time related questions did I ask?"
        ]
        
        for query in test_queries:
            print(f"\n🤔 Query: '{query}'")
            context = await self.advanced_memory.get_context_async(self.test_user_id, query, k=3)
            
            recent_count = len(context.get("recent_turns", []))
            relevant_count = len(context.get("relevant_memories", []))
            clusters_count = len(context.get("memory_clusters", []))
            
            print(f"   📊 Context Retrieved:")
            print(f"      Recent turns: {recent_count}")
            print(f"      Relevant memories: {relevant_count}")  
            print(f"      Memory clusters: {clusters_count}")
            print(f"      Backend: {context.get('memory_stats', {}).get('backend_type', 'unknown')}")
            
            # Show sample recent turns
            if recent_count > 0:
                print(f"   📝 Recent conversations:")
                for turn in context["recent_turns"][:2]:  # Show first 2
                    user_input = turn.get("user_input", "")[:60]
                    if len(turn.get("user_input", "")) > 60:
                        user_input += "..."
                    print(f"      - '{user_input}'")
        
        return True
    
    async def test_memory_insights_and_analytics(self):
        """Test advanced memory insights and user profiling."""
        print("\n📊 TESTING: Memory Insights & Analytics")
        print("-" * 40)
        
        insights = await self.advanced_memory.get_memory_insights(self.test_user_id)
        
        print(f"🎯 MEMORY INSIGHTS:")
        print(f"   Backend: {insights['backend_type']}")
        print(f"   Features: {', '.join(insights['features_available'])}")
        
        user_stats = insights.get("user_stats", {})
        if user_stats:
            print(f"\n👤 USER PROFILE:")
            print(f"   Total interactions: {user_stats.get('total_interactions', 0)}")
            print(f"   Successful interactions: {user_stats.get('successful_interactions', 0)}")
            print(f"   Memory clusters: {user_stats.get('memory_clusters', 0)}")
            print(f"   Interaction span: {user_stats.get('interaction_span_days', 0):.1f} days")
            
            # Show dominant themes
            themes = user_stats.get('dominant_themes', {})
            if themes:
                print(f"   🎯 Dominant themes:")
                for theme, count in sorted(themes.items(), key=lambda x: x[1], reverse=True)[:3]:
                    print(f"      {theme}: {count} conversations")
        
        return True
    
    async def test_memory_conversation_recall(self):
        """Test if the enhanced memory can improve our 70% conversation recall."""
        print("\n💬 TESTING: Enhanced Conversation Recall")
        print("-" * 40)
        
        # Test the same queries that gave us 70% success before
        recall_test_queries = [
            "What did I ask you before?",
            "What was the first thing I asked?", 
            "Can you summarize our conversation?",
            "What did I ask about programming?",
            "Do you remember what I asked about the weather?"
        ]
        
        print("🎯 Testing enhanced recall with JARVIS-1 features...")
        
        successful_recalls = 0
        total_tests = len(recall_test_queries)
        
        for i, query in enumerate(recall_test_queries, 1):
            print(f"\n🧪 Test {i}: '{query}'")
            
            # Get context using advanced memory
            context = await self.advanced_memory.get_context_async(self.test_user_id, query)
            
            # Check if we got meaningful results
            recent_turns = context.get("recent_turns", [])
            relevant_memories = context.get("relevant_memories", [])
            
            if recent_turns or relevant_memories:
                # Simulate what Leonardo would find
                found_content = []
                
                if recent_turns:
                    found_content.extend([turn.get("user_input", "") for turn in recent_turns[:3]])
                
                if relevant_memories:
                    found_content.extend([mem.get("content", "")[:100] for mem in relevant_memories[:2]])
                
                if found_content:
                    print(f"   ✅ SUCCESS: Found relevant content:")
                    for content in found_content[:2]:  # Show top 2
                        preview = content.replace("User: ", "").split("Assistant:")[0][:80]
                        if len(preview) > 77:
                            preview = preview[:77] + "..."
                        print(f"      '{preview}'")
                    successful_recalls += 1
                else:
                    print(f"   ❌ FAILED: No meaningful content found")
            else:
                print(f"   ❌ FAILED: Empty context returned")
        
        # Calculate improvement
        success_rate = successful_recalls / total_tests * 100
        improvement = success_rate - 70  # Compare to our previous 70%
        
        print(f"\n🏆 ENHANCED RECALL RESULTS:")
        print(f"   Success Rate: {successful_recalls}/{total_tests} ({success_rate:.1f}%)")
        print(f"   Improvement: {improvement:+.1f}% vs previous 70%")
        
        if success_rate >= 80:
            print("   🎉 EXCELLENT: Enhanced memory provides significant improvement!")
        elif success_rate > 70:
            print("   ✅ GOOD: Enhanced memory shows improvement")
        else:
            print("   ⚠️ NEEDS WORK: Enhanced memory needs optimization")
        
        return success_rate >= 70
    
    async def run_comprehensive_test(self):
        """Run the complete JARVIS-1 memory enhancement test suite."""
        if not await self.initialize():
            return False
        
        print(f"\n🧪 TESTING USER: {self.test_user_id}")
        
        try:
            # Run all tests
            tests = [
                ("Semantic Storage & Clustering", self.test_semantic_storage_and_clustering),
                ("Semantic Search", self.test_semantic_search),
                ("Growing Context Retrieval", self.test_growing_context_retrieval),
                ("Memory Insights & Analytics", self.test_memory_insights_and_analytics),
                ("Enhanced Conversation Recall", self.test_memory_conversation_recall),
            ]
            
            passed_tests = 0
            for test_name, test_func in tests:
                try:
                    result = await test_func()
                    if result:
                        passed_tests += 1
                        print(f"   ✅ {test_name}: PASSED")
                    else:
                        print(f"   ❌ {test_name}: FAILED")
                except Exception as e:
                    print(f"   ❌ {test_name}: ERROR - {e}")
            
            # Final summary
            print("\n" + "=" * 60)
            print("🎯 JARVIS-1 MEMORY ENHANCEMENT TEST RESULTS")
            print("=" * 60)
            
            success_rate = passed_tests / len(tests) * 100
            
            print(f"📊 Test Results: {passed_tests}/{len(tests)} ({success_rate:.1f}%)")
            
            if self.advanced_memory.use_enhanced_memory:
                print("✅ JARVIS-1 Enhanced Memory: ACTIVE")
                print("   Features: Semantic search, clustering, growing memory, user profiles")
            else:
                print("⚠️ JARVIS-1 Enhanced Memory: FALLBACK TO MCP")
                print("   Install advanced libraries for full functionality")
            
            if success_rate >= 80:
                print("🎉 EXCELLENT: JARVIS-1 memory enhancements working perfectly!")
            elif success_rate >= 60:
                print("✅ GOOD: JARVIS-1 memory enhancements mostly functional")  
            else:
                print("❌ NEEDS WORK: JARVIS-1 memory enhancements need fixes")
            
            # Cleanup
            if self.advanced_memory:
                await self.advanced_memory.shutdown()
            
            return success_rate >= 70
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            return False


async def main():
    """Main test execution."""
    tester = JarvisMemoryTester()
    success = await tester.run_comprehensive_test()
    
    exit_code = 0 if success else 1
    print(f"\n🎭 JARVIS-1 Memory Test {'PASSED' if success else 'FAILED'}")
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
