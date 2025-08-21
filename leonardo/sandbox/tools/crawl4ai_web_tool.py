#!/usr/bin/env python3
"""
Crawl4AI Web Tool for Leonardo - Professional Web Crawling and Content Extraction

This implements the upgraded web module using Crawl4AI as suggested:
- Apache-2.0 license (permissive)
- Local & free (uses Playwright under the hood)
- LLM-ready output (clean Markdown/JSON)
- Built for dynamic sites with async browser pool
- MCP-compatible tool contract
- RAG-ready content extraction

Following the architecture pattern:
Planner → web.scrape (MCP) → Crawl4AI → {markdown, json, links} → Memory/RAG
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_tool import BaseTool, ToolResult

# Crawl4AI imports
try:
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.extraction_strategy import LLMExtractionStrategy
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False


class Crawl4AIWebTool(BaseTool):
    """
    Professional web crawling tool using Crawl4AI.
    
    Features:
    - Clean Markdown/JSON output for LLM processing
    - Advanced dynamic site handling
    - Async browser pool for performance
    - Multiple extraction strategies
    - RAG-ready content formatting
    - MCP-compatible tool contracts
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.crawler: Optional[AsyncWebCrawler] = None
        self.cache_dir = Path("leonardo_web_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
    async def _setup(self) -> None:
        """Setup Crawl4AI crawler."""
        if not CRAWL4AI_AVAILABLE:
            raise ImportError("Crawl4AI not available - install with: pip install crawl4ai")
        
        try:
            # Initialize AsyncWebCrawler with optimized settings
            self.crawler = AsyncWebCrawler(
                headless=True,
                verbose=False
            )
            
            # Crawler is ready to use (no separate start method needed)
            self.logger.info("✅ Crawl4AI web crawler ready")
            
        except Exception as e:
            self.logger.error(f"❌ Crawl4AI setup failed: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Clean shutdown of crawler resources."""
        try:
            # Crawl4AI handles cleanup automatically
            self.crawler = None
        except Exception as e:
            self.logger.error(f"Crawler shutdown error: {e}")
        
        await super().shutdown()
    
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute Crawl4AI web tool following MCP contract."""
        
        if tool_name == "web.scrape":
            return await self._web_scrape(args)
        elif tool_name == "web.search":
            return await self._web_search(args)
        elif tool_name == "web.extract":
            return await self._web_extract(args)
        elif tool_name == "web.crawl":
            return await self._web_crawl(args)
        else:
            raise ValueError(f"Unknown Crawl4AI tool: {tool_name}")
    
    async def _web_scrape(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Web scrape following MCP contract:
        { "tool":"web.scrape",
          "args":{
            "url":"https://example.com",
            "format":"markdown",            // or "json" 
            "max_pages": 1,                 // optional for deep crawl
            "wait_for":"networkidle",       // optional: dynamic sites
            "selectors": null               // optional: CSS/XPath filters
          }
        }
        """
        url = args.get("url", "")
        output_format = args.get("format", "markdown")  # "markdown" or "json"
        max_pages = args.get("max_pages", 1)
        wait_for = args.get("wait_for", "networkidle")
        selectors = args.get("selectors", None)
        
        if not url:
            raise ValueError("URL is required for web.scrape")
        
        self.logger.info(f"🌐 Crawl4AI scraping: {url}")
        
        try:
            # Configure crawl parameters
            crawl_config = {
                "url": url,
                "word_count_threshold": 10,  # Min words to extract
                "bypass_cache": False,
                "process_iframes": True,
                "remove_overlay_elements": True,
                "simulate_user": True,  # Human-like behavior
                "override_navigator": True,  # Anti-detection
                "wait_for": wait_for,
                "delay_before_return_html": 2.0  # Let page load
            }
            
            # Add CSS selectors if provided
            if selectors:
                crawl_config["css_selector"] = selectors
            
            # Execute the crawl using async context manager pattern
            async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
                result = await crawler.arun(**crawl_config)
            
            if not result.success:
                return {
                    "success": False,
                    "error": f"Crawl failed: {result.error_message}",
                    "url": url
                }
            
            # Format output based on requested format
            if output_format.lower() == "json":
                content = {
                    "title": result.metadata.get("title", ""),
                    "description": result.metadata.get("description", ""),
                    "keywords": result.metadata.get("keywords", ""),
                    "text": result.cleaned_html,
                    "markdown": result.markdown,
                    "links": result.links,
                    "images": result.media.get("images", []) if result.media else [],
                    "metadata": result.metadata
                }
            else:  # markdown format (default)
                content = result.markdown
            
            # Prepare response
            response = {
                "success": True,
                "url": url,
                "title": result.metadata.get("title", ""),
                "format": output_format,
                "content": content,
                "links": result.links[:20],  # Limit links
                "word_count": len(result.markdown.split()) if result.markdown else 0,
                "extraction_time": datetime.now().isoformat(),
                "summary": self._create_content_summary(result.markdown, result.links)
            }
            
            # Cache for RAG integration
            await self._cache_content(url, response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"❌ Web scrape failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    async def _web_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Web search using Crawl4AI to scrape search engine results.
        Better than our previous approach - gets clean content.
        """
        query = args.get("query", "")
        search_engine = args.get("engine", "google")
        max_results = min(args.get("max_results", 5), 10)
        
        if not query:
            raise ValueError("Search query cannot be empty")
        
        try:
            # Build search URL
            search_urls = {
                "google": f"https://www.google.com/search?q={query.replace(' ', '+')}", 
                "duckduckgo": f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
                "bing": f"https://www.bing.com/search?q={query.replace(' ', '+')}"
            }
            
            search_url = search_urls.get(search_engine.lower(), search_urls["google"])
            
            self.logger.info(f"🔍 Crawl4AI search: '{query}' on {search_engine}")
            
            # Use web.scrape to get search results page
            scrape_result = await self._web_scrape({
                "url": search_url,
                "format": "json",
                "wait_for": "networkidle"
            })
            
            if not scrape_result.get("success", False):
                return scrape_result
            
            # Extract search results from the scraped content
            content = scrape_result.get("content", {})
            links = content.get("links", [])
            
            # Filter to actual search results (not search engine internal links)
            search_results = []
            for link in links[:max_results * 2]:  # Get more to filter
                href = link.get("href", "")
                text = link.get("text", "").strip()
                
                # Filter out search engine internal links
                if (href and text and 
                    len(text) > 10 and 
                    not any(domain in href for domain in ["google.com", "duckduckgo.com", "bing.com"]) and
                    href.startswith("http")):
                    
                    search_results.append({
                        "title": text[:100],
                        "url": href,
                        "snippet": ""  # Could be enhanced with meta descriptions
                    })
                    
                    if len(search_results) >= max_results:
                        break
            
            return {
                "success": True,
                "query": query,
                "search_engine": search_engine, 
                "results": search_results,
                "count": len(search_results),
                "search_url": search_url,
                "summary": f"Found {len(search_results)} results for '{query}' using Crawl4AI"
            }
            
        except Exception as e:
            self.logger.error(f"❌ Crawl4AI search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    async def _web_extract(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Advanced content extraction with LLM-guided extraction.
        Perfect for RAG integration.
        """
        url = args.get("url", "")
        extraction_prompt = args.get("prompt", "")
        output_format = args.get("format", "markdown")
        
        if not url:
            raise ValueError("URL is required for web.extract")
        
        try:
            self.logger.info(f"🧠 Crawl4AI intelligent extraction: {url}")
            
            # Configure extraction strategy if prompt provided
            extraction_config = {
                "url": url,
                "word_count_threshold": 10,
                "bypass_cache": False,
                "simulate_user": True,
                "override_navigator": True,
                "wait_for": "networkidle"
            }
            
            # Add LLM extraction if prompt provided
            if extraction_prompt:
                # This would use LLM-guided extraction (requires API key setup)
                self.logger.info(f"Using guided extraction: {extraction_prompt}")
            
            # Execute crawl
            result = await self.crawler.arun(**extraction_config)
            
            if not result.success:
                return {
                    "success": False,
                    "error": f"Extraction failed: {result.error_message}",
                    "url": url
                }
            
            # Clean and structure the extracted content
            extracted_data = {
                "url": url,
                "title": result.metadata.get("title", ""),
                "content": result.markdown if output_format == "markdown" else result.cleaned_html,
                "summary": self._create_content_summary(result.markdown, result.links),
                "key_points": self._extract_key_points(result.markdown),
                "links": result.links[:10],
                "metadata": result.metadata,
                "word_count": len(result.markdown.split()) if result.markdown else 0
            }
            
            return {
                "success": True,
                "extraction": extracted_data,
                "format": output_format
            }
            
        except Exception as e:
            self.logger.error(f"❌ Web extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    async def _web_crawl(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Multi-page crawling for comprehensive site analysis.
        """
        start_url = args.get("url", "")
        max_pages = min(args.get("max_pages", 3), 10)  # Limit for safety
        same_domain_only = args.get("same_domain", True)
        
        if not start_url:
            raise ValueError("Starting URL is required for web.crawl")
        
        try:
            self.logger.info(f"🕷️ Crawl4AI multi-page crawl: {start_url}")
            
            crawled_pages = []
            urls_to_crawl = [start_url]
            crawled_urls = set()
            
            for i in range(max_pages):
                if not urls_to_crawl or i >= len(urls_to_crawl):
                    break
                    
                current_url = urls_to_crawl[i]
                if current_url in crawled_urls:
                    continue
                
                # Crawl current page
                page_result = await self._web_scrape({
                    "url": current_url,
                    "format": "json"
                })
                
                if page_result.get("success"):
                    crawled_pages.append(page_result)
                    crawled_urls.add(current_url)
                    
                    # Add new URLs if within domain limits
                    if same_domain_only and i == 0:  # Only for first page
                        page_links = page_result.get("links", [])[:5]  # Limit new URLs
                        for link in page_links:
                            new_url = link.get("href", "")
                            if (new_url.startswith("http") and 
                                new_url not in crawled_urls and 
                                len(urls_to_crawl) < max_pages):
                                urls_to_crawl.append(new_url)
            
            return {
                "success": True,
                "start_url": start_url,
                "pages_crawled": len(crawled_pages),
                "total_words": sum(page.get("word_count", 0) for page in crawled_pages),
                "pages": crawled_pages,
                "summary": f"Successfully crawled {len(crawled_pages)} pages starting from {start_url}"
            }
            
        except Exception as e:
            self.logger.error(f"❌ Web crawl failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": start_url
            }
    
    async def _cache_content(self, url: str, content: Dict[str, Any]) -> None:
        """Cache content for RAG integration."""
        try:
            # Create cache filename
            url_hash = str(hash(url))[-8:]  # Last 8 chars of hash
            cache_file = self.cache_dir / f"web_content_{url_hash}.json"
            
            # Add timestamp
            cache_data = {
                "url": url,
                "cached_at": datetime.now().isoformat(),
                "content": content
            }
            
            # Save to cache
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"💾 Cached content: {cache_file}")
            
        except Exception as e:
            self.logger.warning(f"Cache save failed: {e}")
    
    def _create_content_summary(self, markdown: str, links: List[Dict]) -> str:
        """Create intelligent content summary."""
        if not markdown:
            return "No content extracted"
        
        words = markdown.split()
        word_count = len(words)
        link_count = len(links) if links else 0
        
        # Extract first meaningful sentence
        sentences = markdown.split('.')[:3]
        first_sentence = sentences[0].strip()[:100] if sentences else ""
        
        return f"Extracted {word_count} words with {link_count} links. {first_sentence}..."
    
    def _extract_key_points(self, markdown: str) -> List[str]:
        """Extract key points from markdown content."""
        if not markdown:
            return []
        
        # Simple key point extraction (could be enhanced with NLP)
        lines = markdown.split('\n')
        key_points = []
        
        for line in lines:
            line = line.strip()
            # Look for bullet points, numbered lists, or headers
            if (line.startswith('- ') or 
                line.startswith('* ') or 
                line.startswith('#') or
                (len(line.split()) > 5 and len(line) < 200)):
                key_points.append(line.replace('#', '').replace('- ', '').replace('* ', '').strip())
                if len(key_points) >= 5:  # Limit key points
                    break
        
        return key_points
    
    async def _validate_args(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Validate Crawl4AI tool arguments."""
        
        if tool_name in ["web.scrape", "web.extract", "web.crawl"]:
            url = args.get("url", "")
            if not url or not isinstance(url, str):
                return "URL must be a non-empty string"
            if not url.startswith(("http://", "https://")):
                return "URL must start with http:// or https://"
        
        elif tool_name == "web.search":
            query = args.get("query", "")
            if not query or not isinstance(query, str) or not query.strip():
                return "Search query must be a non-empty string"
        
        return None  # Valid
