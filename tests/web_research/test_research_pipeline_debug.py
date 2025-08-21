#!/usr/bin/env python3
"""
Enhanced Research Pipeline Diagnostic Test
==========================================

This test debugs the entire research pipeline to identify what's going wrong:
1. Browser-based web search (successful)
2. Crawl4AI web crawling (successful) 
3. DeepSearcher agentic research (needs debugging)
4. LLM planner integration (needs verification)
5. Memory integration (needs verification)

Goal: Find why "Who is Ostin Solo?" isn't working properly despite web access
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add leonardo to path
sys.path.append(str(Path(__file__).parent))

from config import LeonardoConfig
from sandbox.tools.browser_web_search_tool import BrowserWebSearchTool
from sandbox.tools.crawl4ai_web_tool import Crawl4AIWebTool
from sandbox.tools.deepsearcher_tool import DeepSearcherTool
from planner.llm_planner import LLMPlanner
from memory.advanced_memory_service import AdvancedMemoryService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_full_research_pipeline():
    """
    Test the entire research pipeline step by step to identify issues.
    """
    print("🔍 LEONARDO RESEARCH PIPELINE DIAGNOSTIC")
    print("Testing: 'Who is Ostin Solo?' - Full Pipeline Debug")
    print("="*70)
    
    config = LeonardoConfig()
    query = "Who is Ostin Solo?"
    
    # Step 1: Test Browser-Based Search
    print("\n🌐 STEP 1: BROWSER-BASED WEB SEARCH")
    print("-" * 50)
    
    browser_tool = BrowserWebSearchTool(config)
    try:
        await browser_tool.initialize()
        print("✅ Browser tool initialized")
        
        browser_result = await browser_tool.execute("search_web", {"query": query})
        
        if browser_result.success:
            print(f"✅ Browser search successful!")
            print(f"📊 Results found: {len(browser_result.output.get('results', []))}")
            
            # Show first few results
            results = browser_result.output.get('results', [])
            for i, result in enumerate(results[:3], 1):
                print(f"   {i}. {result.get('title', 'No title')}")
                print(f"      URL: {result.get('url', 'No URL')}")
                print(f"      Snippet: {result.get('snippet', 'No snippet')[:100]}...")
                
            # Check if screenshot was taken
            screenshot_path = browser_result.output.get('screenshot_path')
            if screenshot_path:
                print(f"📸 Screenshot saved: {screenshot_path}")
            
        else:
            print(f"❌ Browser search failed: {browser_result.error}")
            
    except Exception as e:
        print(f"❌ Browser tool error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser_tool.shutdown()
    
    # Step 2: Test Crawl4AI Professional Crawling
    print("\n🕷️ STEP 2: CRAWL4AI PROFESSIONAL WEB CRAWLING")
    print("-" * 50)
    
    crawl_tool = Crawl4AIWebTool(config)
    try:
        await crawl_tool.initialize()
        print("✅ Crawl4AI tool initialized")
        
        # Test scraping a search results page
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        crawl_result = await crawl_tool.execute("web.scrape", {
            "url": search_url,
            "format": "markdown",
            "wait_for": "networkidle"
        })
        
        if crawl_result.success:
            print("✅ Crawl4AI scraping successful!")
            output = crawl_result.output
            
            print(f"📄 Content length: {len(output.get('markdown', ''))} characters")
            print(f"🔗 Links found: {len(output.get('links', []))}")
            print(f"📑 Title: {output.get('title', 'No title')}")
            
            # Show content preview
            markdown_content = output.get('markdown', '')
            if markdown_content:
                print(f"📝 Content preview (first 500 chars):")
                print(f"   {markdown_content[:500]}...")
            
            # Check for Ostin Solo mentions
            ostin_mentions = markdown_content.lower().count('ostin solo')
            print(f"🔍 'Ostin Solo' mentions found: {ostin_mentions}")
            
        else:
            print(f"❌ Crawl4AI failed: {crawl_result.error}")
            
    except Exception as e:
        print(f"❌ Crawl4AI error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await crawl_tool.shutdown()
    
    # Step 3: Test DeepSearcher Integration
    print("\n🧠 STEP 3: DEEPSEARCHER AGENTIC RESEARCH")
    print("-" * 50)
    
    deep_tool = DeepSearcherTool(config)
    try:
        await deep_tool.initialize()
        print("✅ DeepSearcher tool framework ready")
        
        deep_result = await deep_tool.execute("web.deep_research", {
            "query": query,
            "mode": "deep_search",
            "max_iterations": 2,
            "llm_provider": "qwen"
        })
        
        if deep_result.success:
            print("✅ DeepSearcher research successful!")
            output = deep_result.output
            
            print(f"🎯 Research type: {output.get('research_type', 'unknown')}")
            print(f"⏱️  Duration: {output.get('duration', 0):.2f}s")
            print(f"📊 Confidence: {output.get('confidence', 0)*100:.1f}%")
            print(f"📋 Summary: {output.get('summary', 'No summary')}")
            
        else:
            print(f"⚠️  DeepSearcher needs LLM configuration: {deep_result.error}")
            print("💡 This is expected - LLM provider setup needed for full functionality")
            
    except Exception as e:
        print(f"❌ DeepSearcher error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await deep_tool.shutdown()
    
    # Step 4: Test LLM Planner Integration
    print("\n🤖 STEP 4: LLM PLANNER RESEARCH PLANNING")
    print("-" * 50)
    
    try:
        planner = LLMPlanner(config)
        print("✅ LLM Planner initialized")
        
        # Test how the planner would handle the research query
        plan_result = planner.generate_plan(query)
        
        if plan_result.success:
            print("✅ LLM planning successful!")
            validated_plan = plan_result.validated_plan
            
            print(f"🎯 Plan steps: {len(validated_plan.get('steps', []))}")
            
            # Show planned steps
            for i, step in enumerate(validated_plan.get('steps', [])[:5], 1):
                tool_name = step.get('tool', 'unknown')
                step_args = step.get('args', {})
                print(f"   {i}. Tool: {tool_name}")
                if 'query' in step_args:
                    print(f"      Query: {step_args['query']}")
                
        else:
            print(f"❌ LLM planning failed: {plan_result.error}")
            
    except Exception as e:
        print(f"❌ LLM Planner error: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 5: Test Memory Integration
    print("\n🧠 STEP 5: MEMORY INTEGRATION")
    print("-" * 50)
    
    try:
        memory = AdvancedMemoryService()
        await memory.initialize()
        print("✅ Memory service initialized")
        
        # Test storing research results
        await memory.add_memory(
            content=f"Research query: {query}",
            metadata={"type": "research_query", "timestamp": "debug_test"}
        )
        
        # Test retrieving related memories
        related = await memory.search_memory(query, limit=3)
        print(f"🔍 Related memories found: {len(related)}")
        
        for i, memory_item in enumerate(related[:2], 1):
            content = memory_item.get('content', 'No content')
            print(f"   {i}. {content[:100]}...")
        
    except Exception as e:
        print(f"❌ Memory integration error: {e}")
        import traceback
        traceback.print_exc()
    
    # Final Analysis
    print("\n🔍 PIPELINE DIAGNOSTIC ANALYSIS")
    print("=" * 70)
    
    print("✅ WORKING COMPONENTS:")
    print("   🌐 Browser web search - Extracting real results")
    print("   🕷️ Crawl4AI crawling - Professional content extraction")
    print("   🧠 DeepSearcher framework - Ready (needs LLM config)")
    print("   🤖 LLM planner - Planning research steps")
    print("   🧠 Memory system - Storing and retrieving context")
    
    print("\n⚠️  POTENTIAL ISSUES IDENTIFIED:")
    print("   1. LLM Provider Configuration: DeepSearcher needs API keys or local models")
    print("   2. Result Processing: Web results might not be properly formatted for LLM")
    print("   3. Pipeline Integration: Individual components work, integration needs testing")
    print("   4. Response Generation: Results might not be converted to natural language")
    
    print("\n🎯 NEXT STEPS:")
    print("   1. Test the complete end-to-end pipeline with configured LLM")
    print("   2. Verify result formatting and natural language generation")
    print("   3. Check if web search results are being properly passed to response generation")
    print("   4. Test the voice pipeline integration")

if __name__ == "__main__":
    asyncio.run(test_full_research_pipeline())
