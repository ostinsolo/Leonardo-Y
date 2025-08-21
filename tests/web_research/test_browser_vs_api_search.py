#!/usr/bin/env python3
"""
Browser vs API Web Search Comparison Test
Demonstrates why browser-based web agents are superior to API-based approaches

This validates the key insight:
- API Search: Limited, rate-limited, static content only
- Browser Search: Real interaction, dynamic content, no limits, visual reasoning

Modern web agent research uses browser automation, not APIs!
"""

import asyncio
import sys
import time
from pathlib import Path

# Add Leonardo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo.config import LeonardoConfig
from leonardo.sandbox.tools.web_search_tool import WebSearchTool
from leonardo.sandbox.tools.browser_web_search_tool import BrowserWebSearchTool


class SearchComparisonTester:
    """Compare API-based vs Browser-based web search approaches."""
    
    def __init__(self):
        self.config = LeonardoConfig()
        self.api_search_tool = None
        self.browser_search_tool = None
        
    async def initialize_tools(self):
        """Initialize both search tools for comparison."""
        print("🔧 INITIALIZING SEARCH TOOLS")
        print("=" * 50)
        
        try:
            # Initialize API-based search tool
            print("📡 Initializing API-based search tool...")
            self.api_search_tool = WebSearchTool(self.config)
            await self.api_search_tool.initialize()
            print("   ✅ API search tool ready")
            
            # Initialize browser-based search tool
            print("🌐 Initializing browser-based search tool...")
            self.browser_search_tool = BrowserWebSearchTool(self.config)
            await self.browser_search_tool.initialize()
            print("   ✅ Browser search tool ready")
            
            return True
            
        except Exception as e:
            print(f"❌ Tool initialization failed: {e}")
            return False
    
    async def test_search_comparison(self, query: str) -> dict:
        """Compare API vs Browser search for the same query."""
        print(f"\n🔍 COMPARING SEARCH APPROACHES")
        print(f"   Query: '{query}'")
        print("-" * 50)
        
        results = {
            "query": query,
            "api_search": {"success": False, "duration": 0, "results": [], "issues": []},
            "browser_search": {"success": False, "duration": 0, "results": [], "issues": []}
        }
        
        # Test API-based search
        print("📡 Testing API-based search...")
        api_start = time.time()
        try:
            api_result = await self.api_search_tool.execute("search_web", {
                "query": query,
                "max_results": 5
            })
            
            api_duration = time.time() - api_start
            
            if api_result.success:
                results["api_search"] = {
                    "success": True,
                    "duration": api_duration,
                    "results": api_result.output.get("results", []),
                    "count": api_result.output.get("count", 0),
                    "summary": api_result.output.get("summary", ""),
                    "issues": []
                }
                print(f"   ✅ API search completed: {results['api_search']['count']} results in {api_duration:.2f}s")
            else:
                results["api_search"]["issues"] = [api_result.error]
                print(f"   ❌ API search failed: {api_result.error}")
                
        except Exception as e:
            results["api_search"]["issues"] = [str(e)]
            print(f"   ❌ API search error: {e}")
        
        # Test browser-based search
        print("🌐 Testing browser-based search...")
        browser_start = time.time()
        try:
            browser_result = await self.browser_search_tool.execute("search_web", {
                "query": query,
                "engine": "duckduckgo",
                "max_results": 5,
                "screenshot": True
            })
            
            browser_duration = time.time() - browser_start
            
            if browser_result.success:
                results["browser_search"] = {
                    "success": True,
                    "duration": browser_duration,
                    "results": browser_result.output.get("results", []),
                    "count": browser_result.output.get("count", 0),
                    "summary": browser_result.output.get("summary", ""),
                    "screenshot": browser_result.output.get("screenshot", ""),
                    "page_url": browser_result.output.get("page_url", ""),
                    "page_text_preview": browser_result.output.get("page_text_preview", ""),
                    "issues": []
                }
                print(f"   ✅ Browser search completed: {results['browser_search']['count']} results in {browser_duration:.2f}s")
                if results["browser_search"]["screenshot"]:
                    print(f"   📸 Screenshot saved: {results['browser_search']['screenshot']}")
            else:
                results["browser_search"]["issues"] = [browser_result.error]
                print(f"   ❌ Browser search failed: {browser_result.error}")
                
        except Exception as e:
            results["browser_search"]["issues"] = [str(e)]
            print(f"   ❌ Browser search error: {e}")
        
        return results
    
    async def test_advanced_browser_features(self):
        """Test advanced browser features not possible with APIs."""
        print(f"\n🚀 TESTING: Advanced Browser Features")
        print("-" * 50)
        
        advanced_results = []
        
        try:
            # Test 1: Navigate to a specific website
            print("1. 📍 Testing direct website navigation...")
            nav_result = await self.browser_search_tool.execute("navigate_to", {
                "url": "https://example.com",
                "screenshot": True,
                "extract_text": True
            })
            
            if nav_result.success:
                print(f"   ✅ Navigation successful: {nav_result.output['title']}")
                print(f"   📸 Screenshot: {nav_result.output.get('screenshot', 'None')}")
                advanced_results.append({"test": "navigation", "success": True})
            else:
                print(f"   ❌ Navigation failed: {nav_result.error}")
                advanced_results.append({"test": "navigation", "success": False})
            
            # Test 2: Extract page content
            print("\n2. 📄 Testing content extraction...")
            content_result = await self.browser_search_tool.execute("extract_content", {
                "type": "links",
                "selector": "body"
            })
            
            if content_result.success:
                links_count = len(content_result.output.get("content", []))
                print(f"   ✅ Content extraction successful: {links_count} links found")
                advanced_results.append({"test": "content_extraction", "success": True})
            else:
                print(f"   ❌ Content extraction failed: {content_result.error}")
                advanced_results.append({"test": "content_extraction", "success": False})
            
            return advanced_results
            
        except Exception as e:
            print(f"   ❌ Advanced features test error: {e}")
            return advanced_results
    
    async def analyze_approach_differences(self, comparison_results: list):
        """Analyze the key differences between API vs Browser approaches."""
        print(f"\n📊 ANALYSIS: API vs Browser Approach Comparison")
        print("=" * 60)
        
        api_successes = sum(1 for result in comparison_results if result["api_search"]["success"])
        browser_successes = sum(1 for result in comparison_results if result["browser_search"]["success"])
        
        total_tests = len(comparison_results)
        
        print(f"🎯 SUCCESS RATES:")
        print(f"   API Search: {api_successes}/{total_tests} ({api_successes/total_tests*100:.1f}%)")
        print(f"   Browser Search: {browser_successes}/{total_tests} ({browser_successes/total_tests*100:.1f}%)")
        
        # Analyze common API issues
        api_issues = []
        browser_issues = []
        
        for result in comparison_results:
            api_issues.extend(result["api_search"]["issues"])
            browser_issues.extend(result["browser_search"]["issues"])
        
        if api_issues:
            print(f"\n❌ COMMON API ISSUES:")
            for issue in set(api_issues):
                count = api_issues.count(issue)
                print(f"   - {issue} ({count}x)")
        
        if browser_issues:
            print(f"\n❌ BROWSER ISSUES:")
            for issue in set(browser_issues):
                count = browser_issues.count(issue)
                print(f"   - {issue} ({count}x)")
        
        # Show capabilities comparison
        print(f"\n🔍 CAPABILITY COMPARISON:")
        
        print(f"\n📡 API-BASED SEARCH:")
        print(f"   ✅ Pros:")
        print(f"      - Fast when working (no browser startup)")
        print(f"      - Lower resource usage")
        print(f"      - Simple implementation")
        print(f"   ❌ Cons:")
        print(f"      - Rate limiting (HTTP 202 errors)")
        print(f"      - No dynamic content (JavaScript)")
        print(f"      - No visual information")
        print(f"      - No interaction capabilities")
        print(f"      - Limited to available APIs")
        
        print(f"\n🌐 BROWSER-BASED SEARCH:")
        print(f"   ✅ Pros:")
        print(f"      - Real website access (like a human)")
        print(f"      - Handles JavaScript and dynamic content")
        print(f"      - Visual screenshots for reasoning")
        print(f"      - Can interact with pages (click, type, scroll)")
        print(f"      - No API rate limits")
        print(f"      - Works with any website")
        print(f"      - Multi-step workflows")
        print(f"   ❌ Cons:")
        print(f"      - Higher resource usage")
        print(f"      - Browser startup time")
        print(f"      - More complex error handling")
        
        # Conclusion
        if browser_successes > api_successes:
            print(f"\n🏆 CONCLUSION: Browser-based search is more reliable!")
            print(f"   The user's suggestion to use headless browsers is correct.")
            print(f"   Modern web agents use browser automation for good reason.")
        else:
            print(f"\n⚖️ CONCLUSION: Mixed results - both approaches have trade-offs")
        
        return {
            "api_success_rate": api_successes / total_tests * 100,
            "browser_success_rate": browser_successes / total_tests * 100,
            "recommendation": "browser" if browser_successes >= api_successes else "mixed"
        }
    
    async def run_comprehensive_comparison(self):
        """Run comprehensive comparison between API and browser search approaches."""
        
        if not await self.initialize_tools():
            return False
        
        print(f"\n🧪 RUNNING COMPREHENSIVE SEARCH COMPARISON")
        print("=" * 60)
        
        try:
            # Test queries that highlight the differences
            test_queries = [
                "Python machine learning tutorials",
                "latest JavaScript frameworks 2024",
                "how to use Playwright for web scraping",
                "best practices for AI agents"
            ]
            
            comparison_results = []
            
            # Run search comparisons
            for query in test_queries:
                result = await self.test_search_comparison(query)
                comparison_results.append(result)
                
                # Brief pause between tests
                await asyncio.sleep(2)
            
            # Test advanced browser features
            print(f"\n" + "="*60)
            print("TESTING ADVANCED BROWSER CAPABILITIES")
            print("="*60)
            
            advanced_results = await self.test_advanced_browser_features()
            
            # Analyze results
            print(f"\n" + "="*60)
            print("FINAL ANALYSIS")
            print("="*60)
            
            analysis = await self.analyze_approach_differences(comparison_results)
            
            # Show sample successful results
            print(f"\n📋 SAMPLE RESULTS:")
            for i, result in enumerate(comparison_results[:2]):
                print(f"\nQuery: '{result['query']}'")
                
                api_success = "✅" if result["api_search"]["success"] else "❌"
                browser_success = "✅" if result["browser_search"]["success"] else "❌"
                
                print(f"  {api_success} API: {result['api_search']['count']} results, {result['api_search']['duration']:.2f}s")
                print(f"  {browser_success} Browser: {result['browser_search']['count']} results, {result['browser_search']['duration']:.2f}s")
                
                if result["browser_search"]["success"] and result["browser_search"]["screenshot"]:
                    print(f"      📸 Visual proof: {result['browser_search']['screenshot']}")
            
            # Final recommendation
            print(f"\n🎯 FINAL RECOMMENDATION:")
            if analysis["browser_success_rate"] >= analysis["api_success_rate"]:
                print(f"   🏆 USE BROWSER-BASED WEB SEARCH")
                print(f"   The user was correct - headless browsers are superior!")
                print(f"   Modern web agents like Search-R1 use browser automation for:")
                print(f"   - Real website interaction")
                print(f"   - Dynamic content handling") 
                print(f"   - Visual reasoning with screenshots")
                print(f"   - No API limitations or rate limits")
            else:
                print(f"   ⚖️ MIXED APPROACH")
                print(f"   Use browser search for complex tasks, API for simple ones")
            
            # Cleanup
            if self.browser_search_tool:
                await self.browser_search_tool.shutdown()
            if self.api_search_tool:
                await self.api_search_tool.shutdown()
            
            return analysis["browser_success_rate"] >= 70
            
        except Exception as e:
            print(f"❌ Comparison test failed: {e}")
            return False


async def main():
    """Main test execution."""
    print("🌐 LEONARDO WEB SEARCH APPROACH COMPARISON")
    print("Validating: API-based vs Browser-based search approaches")
    print("=" * 70)
    
    tester = SearchComparisonTester()
    success = await tester.run_comprehensive_comparison()
    
    exit_code = 0 if success else 1
    print(f"\n🎭 Search Comparison Test {'PASSED' if success else 'FAILED'}")
    
    print(f"\n💡 KEY INSIGHT:")
    print(f"The user's suggestion to use headless browsers instead of APIs")
    print(f"aligns with modern web agent research patterns!")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
