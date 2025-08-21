#!/usr/bin/env python3
"""
Browser-Based Web Search Tool - Modern Web Agent Implementation
Uses headless browser automation for real web interaction and reasoning

This implements the proper approach for web agents:
- Headless browser automation (Playwright)
- Real website navigation and interaction
- Dynamic content handling (JavaScript, SPAs)
- Screenshot capture for visual reasoning
- Multi-step web workflows
- No API rate limits or restrictions

Based on modern web agent research patterns like:
- WebVoyager: visual web navigation
- LaVague: browser automation with reasoning
- WebArena: interactive web environments
"""

import asyncio
import json
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from .base_tool import BaseTool

# Playwright imports
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class BrowserWebSearchTool(BaseTool):
    """
    Modern browser-based web search and interaction tool.
    
    Features:
    - Real browser automation (Playwright)  
    - JavaScript-enabled websites
    - Visual screenshots for reasoning
    - Multi-step navigation workflows
    - Form interactions and clicking
    - No API limitations or rate limits
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.screenshots_dir = Path("leonardo_screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
        
    async def _setup(self) -> None:
        """Setup browser automation."""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not available - install with: pip install playwright")
        
        try:
            # Initialize Playwright browser
            self.playwright = await async_playwright().start()
            
            # Launch headless Chromium with anti-detection measures
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage', 
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-background-networking',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ]
            )
            
            # Create browser context with realistic settings and stealth measures
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 720},
                device_scale_factor=1,
                # Add realistic browser headers
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            # Create a new page
            self.page = await self.context.new_page()
            
            # Hide automation signatures with JavaScript
            await self.page.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Remove automation signals
                Object.defineProperty(window, 'chrome', {
                    get: () => ({
                        runtime: {},
                        app: {
                            isInstalled: false,
                        },
                        webstore: {
                            onInstallStageChanged: {},
                            onDownloadProgress: {},
                        },
                        csi: function() {},
                        loadTimes: function() {},
                    })
                });
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)
            
            self.logger.info("✅ Browser automation ready (Playwright + Chromium + Stealth)")
            
        except Exception as e:
            self.logger.error(f"❌ Browser setup failed: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Clean shutdown of browser resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            self.logger.error(f"Browser shutdown error: {e}")
        
        await super().shutdown()
    
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute browser-based web tool."""
        
        if tool_name == "search_web":
            return await self._browser_web_search(args)
        elif tool_name == "navigate_to":
            return await self._navigate_to_url(args)
        elif tool_name == "interact_with_page":
            return await self._interact_with_page(args)
        elif tool_name == "extract_content":
            return await self._extract_page_content(args)
        else:
            raise ValueError(f"Unknown browser tool: {tool_name}")
    
    async def _browser_web_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform web search using real browser automation.
        This navigates to search engines like a human would.
        """
        query = args.get("query", "").strip()
        search_engine = args.get("engine", "duckduckgo")  # duckduckgo, google, bing
        max_results = min(args.get("max_results", 5), 10)
        take_screenshot = args.get("screenshot", True)
        
        if not query:
            raise ValueError("Search query cannot be empty")
        
        try:
            search_url = self._get_search_engine_url(search_engine, query)
            
            self.logger.info(f"🌐 Browser search: '{query}' on {search_engine}")
            
            # Navigate to search engine with human-like behavior
            await self.page.goto(search_url, wait_until="networkidle", timeout=30000)
            
            # Human-like delay
            await self.page.wait_for_timeout(1000 + (hash(query) % 1000))  # Random delay 1-2 seconds
            
            # Take screenshot for visual reasoning
            screenshot_path = None
            if take_screenshot:
                screenshot_path = await self._take_screenshot(f"search_{search_engine}_{query[:30]}")
            
            # Wait for search results to load with longer timeout
            await self.page.wait_for_timeout(3000)
            
            # Extract search results using browser automation
            results = await self._extract_search_results(search_engine, max_results)
            
            # Get page text content for reasoning
            page_text = await self.page.inner_text("body")
            
            return {
                "query": query,
                "search_engine": search_engine,
                "results": results,
                "count": len(results),
                "screenshot": screenshot_path,
                "page_url": self.page.url,
                "summary": self._create_search_summary(query, results),
                "page_text_preview": page_text[:500] + "..." if len(page_text) > 500 else page_text
            }
            
        except Exception as e:
            self.logger.error(f"Browser search failed: {e}")
            raise ValueError(f"Browser search failed: {e}")
    
    async def _navigate_to_url(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Navigate to a specific URL and capture information."""
        url = args.get("url", "").strip()
        take_screenshot = args.get("screenshot", True)
        extract_text = args.get("extract_text", True)
        
        if not url:
            raise ValueError("URL cannot be empty")
        
        # Add protocol if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        try:
            self.logger.info(f"🌐 Navigating to: {url}")
            
            # Navigate to URL
            await self.page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Take screenshot
            screenshot_path = None
            if take_screenshot:
                screenshot_path = await self._take_screenshot(f"navigate_{url.replace('/', '_')}")
            
            # Extract page information
            title = await self.page.title()
            current_url = self.page.url
            
            page_text = ""
            if extract_text:
                page_text = await self.page.inner_text("body")
                if len(page_text) > 2000:
                    page_text = page_text[:2000] + "..."
            
            return {
                "url": url,
                "final_url": current_url,
                "title": title,
                "screenshot": screenshot_path,
                "content": page_text,
                "summary": f"Successfully navigated to {title} at {current_url}"
            }
            
        except Exception as e:
            self.logger.error(f"Navigation failed: {e}")
            raise ValueError(f"Navigation failed: {e}")
    
    async def _interact_with_page(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Interact with page elements (click, type, scroll)."""
        action = args.get("action", "").lower()
        selector = args.get("selector", "")
        text = args.get("text", "")
        take_screenshot = args.get("screenshot", True)
        
        try:
            if action == "click":
                await self.page.click(selector, timeout=10000)
                result_msg = f"Clicked element: {selector}"
                
            elif action == "type":
                await self.page.fill(selector, text)
                result_msg = f"Typed '{text}' into {selector}"
                
            elif action == "scroll":
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                result_msg = "Scrolled to bottom of page"
                
            elif action == "wait":
                await self.page.wait_for_selector(selector, timeout=10000)
                result_msg = f"Waited for element: {selector}"
                
            else:
                raise ValueError(f"Unknown action: {action}")
            
            # Take screenshot after interaction
            screenshot_path = None
            if take_screenshot:
                screenshot_path = await self._take_screenshot(f"interaction_{action}")
            
            return {
                "action": action,
                "selector": selector,
                "success": True,
                "screenshot": screenshot_path,
                "current_url": self.page.url,
                "summary": result_msg
            }
            
        except Exception as e:
            self.logger.error(f"Page interaction failed: {e}")
            raise ValueError(f"Page interaction failed: {e}")
    
    async def _extract_page_content(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Extract specific content from the current page."""
        content_type = args.get("type", "text")  # text, links, forms, tables
        selector = args.get("selector", "body")
        
        try:
            if content_type == "text":
                content = await self.page.inner_text(selector)
                
            elif content_type == "html":
                content = await self.page.inner_html(selector)
                
            elif content_type == "links":
                links = await self.page.evaluate("""
                    () => {
                        const links = Array.from(document.querySelectorAll('a[href]'));
                        return links.map(link => ({
                            text: link.innerText.trim(),
                            href: link.href,
                            title: link.title
                        })).filter(link => link.text);
                    }
                """)
                content = links[:20]  # Limit to first 20 links
                
            elif content_type == "forms":
                forms = await self.page.evaluate("""
                    () => {
                        const forms = Array.from(document.querySelectorAll('form'));
                        return forms.map(form => ({
                            action: form.action,
                            method: form.method,
                            inputs: Array.from(form.querySelectorAll('input')).map(input => ({
                                name: input.name,
                                type: input.type,
                                placeholder: input.placeholder
                            }))
                        }));
                    }
                """)
                content = forms
                
            else:
                raise ValueError(f"Unknown content type: {content_type}")
            
            return {
                "content_type": content_type,
                "selector": selector,
                "content": content,
                "url": self.page.url,
                "summary": f"Extracted {content_type} content from {selector}"
            }
            
        except Exception as e:
            self.logger.error(f"Content extraction failed: {e}")
            raise ValueError(f"Content extraction failed: {e}")
    
    def _get_search_engine_url(self, engine: str, query: str) -> str:
        """Get search URL for different engines."""
        encoded_query = query.replace(" ", "+")
        
        if engine.lower() == "google":
            return f"https://www.google.com/search?q={encoded_query}"
        elif engine.lower() == "bing":
            return f"https://www.bing.com/search?q={encoded_query}"
        else:  # duckduckgo default
            return f"https://duckduckgo.com/?q={encoded_query}"
    
    async def _extract_search_results(self, engine: str, max_results: int) -> List[Dict[str, Any]]:
        """Extract search results from the current page using browser automation."""
        try:
            if engine.lower() == "google":
                # Google search result selectors
                results = await self.page.evaluate(f"""
                    () => {{
                        const results = [];
                        const items = document.querySelectorAll('div[data-ved] h3');
                        for (let i = 0; i < Math.min(items.length, {max_results}); i++) {{
                            const item = items[i];
                            const link = item.closest('a');
                            if (link) {{
                                const snippet = item.closest('[data-ved]').querySelector('[data-sncf]');
                                results.push({{
                                    title: item.innerText,
                                    url: link.href,
                                    snippet: snippet ? snippet.innerText : ''
                                }});
                            }}
                        }}
                        return results;
                    }}
                """)
                
            elif engine.lower() == "bing":
                # Bing search result selectors
                results = await self.page.evaluate(f"""
                    () => {{
                        const results = [];
                        const items = document.querySelectorAll('.b_algo h2 a');
                        for (let i = 0; i < Math.min(items.length, {max_results}); i++) {{
                            const item = items[i];
                            const snippet = item.closest('.b_algo').querySelector('.b_caption p');
                            results.push({{
                                title: item.innerText,
                                url: item.href,
                                snippet: snippet ? snippet.innerText : ''
                            }});
                        }}
                        return results;
                    }}
                """)
                
            else:  # duckduckgo
                # DuckDuckGo search result selectors - Updated for current DuckDuckGo structure
                results = await self.page.evaluate(f"""
                    () => {{
                        const results = [];
                        
                        // Try multiple selector patterns for DuckDuckGo results
                        let items = [];
                        
                        // Pattern 1: Current DuckDuckGo structure
                        items = document.querySelectorAll('[data-testid="result-title-a"]');
                        
                        // Pattern 2: Alternative structure with h2 links
                        if (items.length === 0) {{
                            items = document.querySelectorAll('h2 a[href]:not([href*="duckduckgo.com"])');
                        }}
                        
                        // Pattern 3: General result links (fallback)
                        if (items.length === 0) {{
                            items = document.querySelectorAll('a[href*="http"]:not([href*="duckduckgo.com"])');
                            // Filter to only those that look like search results
                            items = Array.from(items).filter(link => {{
                                const text = link.innerText.trim();
                                const parent = link.closest('[data-testid], .result, .web-result, article');
                                return text.length > 10 && parent !== null;
                            }});
                        }}
                        
                        console.log(`Found ${{items.length}} potential results`);
                        
                        for (let i = 0; i < Math.min(items.length, {max_results}); i++) {{
                            const item = items[i];
                            let snippet = '';
                            
                            // Try different methods to find snippet
                            const parent = item.closest('[data-testid], .result, .web-result, article, div');
                            if (parent) {{
                                // Try data-testid first
                                let snippetEl = parent.querySelector('[data-testid="result-snippet"]');
                                if (!snippetEl) {{
                                    // Try finding any nearby text content
                                    snippetEl = parent.querySelector('.snippet, .description, .excerpt, span:not(:empty)');
                                }}
                                if (snippetEl) {{
                                    snippet = snippetEl.innerText.trim();
                                }}
                            }}
                            
                            const title = item.innerText.trim();
                            const url = item.href;
                            
                            if (title && url && title.length > 2) {{
                                results.push({{
                                    title: title,
                                    url: url,
                                    snippet: snippet
                                }});
                            }}
                        }}
                        
                        console.log(`Extracted ${{results.length}} valid results`);
                        return results;
                    }}
                """)
            
            return results or []
            
        except Exception as e:
            self.logger.error(f"Failed to extract search results: {e}")
            return []
    
    async def _take_screenshot(self, filename_prefix: str) -> str:
        """Take screenshot and return path."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Clean filename
            clean_prefix = "".join(c for c in filename_prefix if c.isalnum() or c in (' ', '-', '_')).rstrip()
            screenshot_path = self.screenshots_dir / f"{clean_prefix}_{timestamp}.png"
            
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            
            self.logger.debug(f"Screenshot saved: {screenshot_path}")
            return str(screenshot_path)
            
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return ""
    
    def _create_search_summary(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Create search summary from browser results."""
        if not results:
            return f"No search results found for '{query}'"
        
        summary_parts = [f"Found {len(results)} results for '{query}':"]
        
        for i, result in enumerate(results[:3], 1):
            title = result.get("title", "No title")[:80]
            if len(result.get("title", "")) > 80:
                title += "..."
            summary_parts.append(f"{i}. {title}")
        
        if len(results) > 3:
            summary_parts.append(f"... and {len(results) - 3} more results.")
        
        return " ".join(summary_parts)
    
    async def _validate_args(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Validate browser tool arguments."""
        
        if tool_name == "search_web":
            query = args.get("query", "")
            if not query or not isinstance(query, str) or not query.strip():
                return "Search query must be a non-empty string"
        
        elif tool_name == "navigate_to":
            url = args.get("url", "")
            if not url or not isinstance(url, str):
                return "URL must be a non-empty string"
        
        elif tool_name == "interact_with_page":
            action = args.get("action", "")
            if action not in ["click", "type", "scroll", "wait"]:
                return "Action must be one of: click, type, scroll, wait"
            
            if action in ["click", "wait"] and not args.get("selector"):
                return f"Action '{action}' requires a selector"
            
            if action == "type" and (not args.get("selector") or not args.get("text")):
                return "Action 'type' requires both selector and text"
        
        return None  # Valid
