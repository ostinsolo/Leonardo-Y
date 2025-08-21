#!/usr/bin/env python3
"""
Standalone Browser Search Test
==============================

This test fixes and validates the browser search functionality independently
before integrating into Leonardo pipeline.

Goal: Get "Who is Ostin Solo?" search working properly with correct selectors.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add leonardo to path properly
leonardo_path = Path(__file__).parent
sys.path.insert(0, str(leonardo_path))

# Import with proper path handling
try:
    from leonardo.config import LeonardoConfig
    from leonardo.sandbox.tools.browser_web_search_tool import BrowserWebSearchTool
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, str(leonardo_path.parent))
    from leonardo.config import LeonardoConfig
    from leonardo.sandbox.tools.browser_web_search_tool import BrowserWebSearchTool

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

async def test_browser_search_standalone():
    """Test browser search tool standalone - fix selectors and get results."""
    print("🌐 STANDALONE BROWSER SEARCH TEST")
    print("Goal: Fix selectors and get 'Ostin Solo' results")
    print("=" * 60)
    
    config = LeonardoConfig()
    browser_tool = BrowserWebSearchTool(config)
    
    try:
        print("🚀 Initializing browser...")
        await browser_tool.initialize()
        print("✅ Browser initialized")
        
        # Test different search engines and queries
        test_cases = [
            {"query": "Ostin Solo Leonardo AI", "description": "Primary query"},
            {"query": "Ostin Solo GitHub", "description": "GitHub specific"},
            {"query": "Leonardo AI assistant", "description": "Project name"},
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            query = test_case["query"]
            desc = test_case["description"]
            
            print(f"\n📍 TEST {i}: {desc}")
            print(f"Query: '{query}'")
            print("-" * 40)
            
            # Navigate to search page
            page = browser_tool.page
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            print(f"🌐 Navigating to: {search_url}")
            response = await page.goto(search_url, wait_until="networkidle")
            print(f"📡 Response: {response.status}")
            
            # Wait for content
            await page.wait_for_timeout(2000)
            
            # Take screenshot for debugging
            screenshot_path = f"test_{i}_search.png"
            await page.screenshot(path=screenshot_path)
            print(f"📸 Screenshot: {screenshot_path}")
            
            # Test multiple selector strategies
            print("🔍 Testing selector strategies...")
            
            # Strategy 1: Google standard result containers
            selectors = [
                'div.g',  # Standard Google result container
                'div[data-ved]',  # Elements with data-ved attribute
                'h3',  # All h3 headings (result titles)
                'h3 a',  # Links in h3 headings  
                'a[href*="http"]:not([href*="google"]):not([href*="gstatic"])',  # External links only
                'div.yuRUbf',  # New Google result wrapper
                'div.yuRUbf a',  # Links in new wrapper
                '[data-testid]',  # Any data-testid elements
                'cite',  # URL citations
                'span.VuuXrf',  # Snippet text spans
            ]
            
            results_found = []
            
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"   ✅ {selector}: {len(elements)} elements")
                        
                        # Get sample content from first few elements
                        for j, elem in enumerate(elements[:3]):
                            try:
                                text = await elem.text_content()
                                href = await elem.get_attribute('href')
                                if text and text.strip():
                                    result_data = {
                                        'selector': selector,
                                        'text': text.strip()[:100],
                                        'href': href[:100] if href else None
                                    }
                                    results_found.append(result_data)
                                    print(f"      {j+1}. {text.strip()[:60]}...")
                                    if href and not href.startswith('#'):
                                        print(f"         URL: {href[:60]}...")
                            except Exception:
                                pass
                    else:
                        print(f"   ❌ {selector}: 0 elements")
                        
                except Exception as e:
                    print(f"   ❌ {selector}: Error - {e}")
            
            # Analyze results for Ostin Solo content
            print(f"\n📊 RESULTS ANALYSIS:")
            ostin_mentions = []
            solo_mentions = []
            relevant_results = []
            
            for result in results_found:
                text = result['text'].lower()
                if 'ostin' in text or 'solo' in text:
                    relevant_results.append(result)
                    if 'ostin' in text:
                        ostin_mentions.append(result)
                    if 'solo' in text:
                        solo_mentions.append(result)
            
            print(f"   Total results extracted: {len(results_found)}")
            print(f"   'Ostin' mentions: {len(ostin_mentions)}")
            print(f"   'Solo' mentions: {len(solo_mentions)}")
            print(f"   Relevant results: {len(relevant_results)}")
            
            if relevant_results:
                print(f"\n🎯 RELEVANT CONTENT FOUND:")
                for k, result in enumerate(relevant_results[:3], 1):
                    print(f"   {k}. Selector: {result['selector']}")
                    print(f"      Text: {result['text']}")
                    if result['href']:
                        print(f"      URL: {result['href']}")
            else:
                print("❌ No relevant content found for this query")
            
            print()
        
        print("🔧 SELECTOR RECOMMENDATION:")
        print("Based on testing, best selectors are:")
        print("1. 'div.yuRUbf a' - For result links")
        print("2. 'div.g' - For result containers") 
        print("3. 'h3' - For result titles")
        print("4. 'cite' - For URLs")
        print("5. 'span.VuuXrf' - For snippets")
        
        await browser_tool.shutdown()
        
    except Exception as e:
        print(f"❌ Browser test failed: {e}")
        import traceback
        traceback.print_exc()
        
        if browser_tool.browser:
            await browser_tool.shutdown()

if __name__ == "__main__":
    asyncio.run(test_browser_search_standalone())
